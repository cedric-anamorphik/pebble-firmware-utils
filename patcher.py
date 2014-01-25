#!/usr/bin/env python
# This scripts applies patches to firmware

import sys
from struct import pack #,unpack

data = ""
datar = ""

class Instruction:
    """ Abstract, don't instantiate! """
    def setLabel(self, label):
        """ Sets name for this instruction to be discovered later """
        self.label = label
    def getLabel(self):
        try:
            return self.label
        except AttributeError:
            return None # if we have not this property set
    def setContext(self, context):
        """
        Sets context (dictionary label->address)
        which is good for procedure containing this instruction
        Also it must contain all external funcs used in this function
        """
        self.context = context
    def _getAddr(self, label):
        """
        Queries address from Context
        """
        try:
            return self.context[label]
        except KeyError:
            raise Exception("No such address: %s (for %s)" % (label, self))
    def setPosition(self, pos):
        """
        Sets address where this instruction will be placed
        """
        self.pos = pos
    def getPosition(self):
        return self.pos
    def getCode(self):
        """
        Returns binary code for this instruction
        sitting on given position
        """
        raise NotImplementedError("Don't instantiate this class!")
    def getSize(self):
        """ returns size of this instruction in bytes """
        return 2
class I(Instruction):
    """ Just an ordinary two-byte instruction """
    def __init__(self, code):
        """
        code is a ready instruction code, like '\\x00\\xBF'
        """
        self.code = code
    def getCode(self):
        return self.code
class DCx(Instruction):
    """ DCW or DCD. For DCB see class I (command db) """
    def __init__(self, size, val):
        """ val is either number (dec/0xhex/0oct/0bbin) or label/address """
        if size not in [2,4]:
            raise ValueError("Unsupported size %d, it must be either 2 or 4" % size)
        self.size = size
        if type(val) is not str or len(val) < 1:
            raise ValueError("Bad value: %s" % repr(val))
        if size != 4 and not val[0].isdigit(): # address must be 4bytes!
            raise ValueError("addrs are only valid for DCD, not DCW")
        self.val = val
    def getSize(self):
        return self.size
    def getCode(self):
        if self.val[0].isdigit():
            val = int(self.val, 0)
        else:
            val = self._getAddr(val)
        fmt = '<H' if self.size==2 else '<I'
        return pack(fmt, val)
class Jump(Instruction):
    """ Any of two-byte B** or CB* """
    def __init__(self, dest, cond, reg=None):
        """
        label: jump destination
        cond: condition (number, max 4 bits)
        reg: number of register to use (if CB*) or None (if B**)
        """
        self.dest = dest
        if cond < 0 or cond > 0b1111:
            raise ValueError("Bad condition value %x!" % cond)
        self.cond = cond
        if reg and (reg < 0 or reg > 0b111):
            raise ValueError("Bad register value %x!" % reg)
        self.reg = reg
    def getCode(self):
        offset = self._getAddr(self.dest) - (self.pos+4)
        offset = offset >> 1
        usereg = self.reg != None
        if abs(offset) >= 1<<(5 if usereg else 8):
            raise ValueError("Offset %X exceeds maximum of %X!" %
                             (offset, 1<<11))
        if usereg:
            code = (0b1011 << 12) +\
                   (self.cond << 8) +\
                   (offset << 3) +\
                   (self.reg)
        else:
            code = (0b1101 << 12) +\
                   (self.cond << 8) +\
                   (offset)
        return pack('<H', code)
class LongJump(Instruction):
    """ B.W or BL instruction (4-bytes) """
    def __init__(self, dest, bl):
        """
        dest is a destination label
        bl is a boolean value - if this is BL or B.W
        """
        self.dest = dest
        self.bl = bl
    def getCode(self):
        offset = self._getAddr(self.dest) - (self.pos+4)
        offset = offset >> 1
        if abs(offset) >= 1<<22:
            raise ValueError("Offset %X exceeds maximum of %X!" %
                             (offset, 1<<22))
        hi_o = (offset >> 11) & 0b11111111111
        lo_o = (offset >> 0)  & 0b11111111111
        hi_c = 0b11110
        lo_c = 0b11111 if self.bl else 0b10111
        hi = (hi_c << 11) + hi_o
        lo = (lo_c << 11) + lo_o
        code = pack('<HH', hi, lo)
        return code
    def getSize(self):
        return 4
class BW(LongJump):
    def __init__(self, dest):
        LongJump.__init__(self, dest, False)
class BL(LongJump):
    def __init__(self, dest):
        LongJump.__init__(self, dest, True)

def parse_args():
    import argparse
    parser = argparse.ArgumentParser(
        description="Pebble firmware patcher")
    parser.add_argument("output", nargs='?', default=sys.stdout, type=argparse.FileType("wb"),
                        help="Output file, defaults to stdout")
    parser.add_argument("-t", "--tintin", nargs='?', default="tintin_fw.bin", type=argparse.FileType("rb"),
                        help="Input tintin_fw file, defaults to tintin_fw.bin")
    parser.add_argument("-p", "--patch", default=sys.stdin, type=argparse.FileType("r"),
                        help="File with patch to apply, by default will read from stdin")
    return parser.parse_args()

def patch_fw(args):
    global data,datap,datar

    def myassert(cond, msg):
        """ Raise descriptive SyntaxError if not cond """
        if not cond:
            raise SyntaxError("%d: %s (%s)" % (lnum+1, msg, line))
    def tryc(action, msg):
        """ Try execute passed lambda function, and raise correct SyntaxError on ValueError """
        try:
            return action()
        except ValueError as e:
            raise SyntaxError("%d: %s - %s (%s)" % (lnum+1, msg, e, line))

    def parse_hex(vals):
        """ Convert list of hexadecimal bytes to string (byte array) """
        ret = ''
        for v in vals:
            myassert(len(v) == 2, "Malformed hex string at %s" % v)
            ret += pack('B', tryc(lambda: int(v, 16), "Malformed hex string at %s" % v))
        return ret

    data = args.tintin.read()

    def search_addr(sig):
        """
        This function tries to match signature to data,
        and returns a memory address of found match only if it is an only one.
        sig is list of bytes (in hex), "?[n]" or "@"
        bytes must match, ? means any byte, "?n" means any n bytes,
        @ is required position (default position is at start of mask)
        """
        def is_hex(n):
            return n.isdigit() or n.lower() in 'abcdef'
        def masklen():
            b=0
            for m in mask:
                if type(m) is str:
                    b += len(m)
                elif type(m) is int:
                    b += m
                else:
                    raise ValueError(m) # must never happen
            return b
        offset = 0 # for @
        mask = [] # form: str, int(offset), str...
        string = '' # current string
        for s in sig:
            if len(s) == 2 and is_hex(s[0]) and is_hex(s[1]): # byte
                b = int(s, 16) # must work as we checked already
                string += chr(b)
            elif s == '@':
                myassert(offset == 0, "Multiple '@'s (or starting with skip) - it is not good! Where am I?")
                offset = masklen() + len(string)
            elif s[0] == '?':
                s = s[1:]
                if len(s) == 0:
                    val = 1
                else:
                    val = tryc(lambda: int(s), "Not a number: %s" % s)
                if string: # this is not very first skip
                    mask.append(string)
                    string = ''
                    mask.append(val)
                else: # first mask item must be string, so just use offset
                    offset = -val
            else:
                myassert(False, "Illegal value: %s" % s)
        if string:
            mask.append(string)
        # now mask is fully parsed
        gpos = None
        matches = []
        while gpos < len(data): # None < n works
            gpos = data.find(mask[0], gpos) # current proposed pos of mask start
            if gpos < 0:
                break # mask start not found
            cpos = gpos + len(mask[0]) # current mask item pos
            mismatch = False
            for m in mask[1:]:
                if type(m) is int:
                    cpos += m
                elif type(m) is str:
                    if not data[cpos:].startswith(m):
                        mismatch = True # mask mismatched
                        break
                    cpos += len(m)
                else: # this must never happen
                    raise ValueError(m)
            if not mismatch: # mask matched
                matches.append(gpos)
            gpos += 1 # to skip this occurance next time
        if len(matches) == 0:
            print "Mask not found"
            return False
        if len(matches) > 1:
            print "Multiple match - ambiguous, so failing"
            return False
        #print "Mask found at %X" % (matches[0] + offset + 0x08010000)
        return matches[0] + offset + 0x08010000

    blocks = [] # list of all our blocks
    blocknames = []
    procs = {} # all known procedure names -> addr

    # scratchpad:
    mask = [] # mask for determining baddr
    baddr = None # block beginning
    addr = None # current instruction starting address, or block beginning
    block = None # current block - list of instructions
    label = None # label saved for further use
    blockname = None # proc

    for lnum, line in enumerate(args.patch):
        line = line[:-1].strip() # remove \n and leading/trailing whitespaces
        if line.find(';') >= 0:
            line = line[:line.find(';')].strip()
        tokens = line.split()
        if len(tokens) == 0:
            continue # empty line, or only comments/whitespaces
        if block == None: # outside of block
            excess = [] # tokens after '{'
            for t in tokens:
                if t == '{': # end of mask, start of block
                    addr = baddr = search_addr(tokens)
                    myassert(addr != False, "Mask not found. Failing.")
                    block = [] # now in block
                elif block == []: # another part of mask, block not started yet
                    mask.append(t)
                else:
                    excess.append(t) # pass these to the following code
            tokens = excess # pass any excess tokens to below
        if len(tokens) > 0: # normal line inside block, or remainder from after '{'
            if len(tokens) == 1 and tokens[0] == '}': # end of block
                blocks.append(block)
                blocknames.append(blockname)
                procs[blockname] = baddr # save this block's address for future use
                mask = []
                baddr = None
                addr = None
                block = None
                blockname = None
                continue
            if tokens[0] == "proc": # this block has name!
                myassert(len(tokens) == 2, "proc keyword requires one argument")
                blockname = tokens[1]
                continue
            if tokens[0].endswith(':'): # label
                label = tokens[0][:-1]
                del tokens[0]
                if len(tokens) == 0:
                    continue # line contains only label; will use it in next pass
                # else go below: all following items can have label
            instr = None # this will be current instruction
            if tokens[0] in ["db", "DCB"]: # define byte - most common instruction
                myassert(len(tokens) >= 2, "Error - 'db' without value?")
                del tokens[0]
                instr = I(parse_hex(tokens))
            elif tokens[0] in ["DCD", "DCW"]:
                myassert(len(tokens) == 2, "Bad value count for DCx")
                instr = DCx(2 if tokens[0]=="DCW" else 4, tokens[1])
            elif tokens[0] == "jump":
                myassert(len(tokens) >= 3, "Too few arguments for Jump")
                myassert(len(tokens) <= 4, "Too many arguments for Jump")
                del tokens[0]
                reg = None
                dest = None
                cond = None
                for t in tokens:
                    if len(t) == 2 and t[0] == 'R': # register
                        reg = int(t[1])
                    elif t[0].isalpha() or t[0] == '_': # identifier (label)
                        dest = t
                    else: # must be number
                        cond = tryc(lambda: int(t), "Malformed argument for Jump: %s" % t)
                myassert(cond != None and dest, "Illegal Jump call")
                instr = Jump(dest, cond, reg)
            elif tokens[0] in ["B.W", "BL"]:
                myassert(len(tokens) == 2, "%s keyword requires one argument" % tokens[0])
                instr = LongJump(tokens[1], tokens[0] == "BL")
            else:
                myassert(False, "Unknown instruction %s" % tokens[0])
            if label: # current instruction has a label?
                instr.setLabel(label)
                label = None
            instr.setPosition(addr)
            addr += instr.getSize()
            block.append(instr)
    if block: # unterminated?
        print "WARNING: unterminated block detected, will ignore it"

    # now apply patches
    print "Applying patches..."
    datar = data
    for bnum, block in enumerate(blocks):
        print "Block %d: %s" % (bnum+1, blocknames[bnum] or "(no name)")
        print " ",
        if len(block) == 0:
            print "skipping (nothing to patch)"
            continue # skip empty blocks as they need not to be patched
        context = procs.copy()
        #print context
        for i in block: # for every instruction check label
            if i.getLabel():
                context[i.getLabel()] = i.getPosition()
        start = block[0].getPosition() - 0x08010000 # convert address to offset
        code = ''
        for i in block:
            i.setContext(context)
            code += i.getCode()
        blen = len(datar)
        datar = datar[:start] + code + datar[start+len(code):]
        if len(datar) != blen:
            raise Exception("Length mismatch - was %d, now %d" % (blen, len(datar)))
        print "%d bytes patched at %X" % (len(code), start)
    print "Saving..."
    args.output.write(datar)
    args.output.close()
    print "Done."

if __name__ == "__main__":
    args = parse_args()
    patch_fw(args)
