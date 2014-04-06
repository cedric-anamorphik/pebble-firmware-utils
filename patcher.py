#!/usr/bin/env python
# This scripts applies patches to firmware

import sys
from struct import pack,unpack

# Helper functions for syntax checking
def parseArgs(tokens):
    """ Convert tokens from form ['Arg1,', 'Arg2', ',', 'Arg3'] to ['Arg1','Arg2','Arg3'] """
    return [x.strip() for x in ' '.join(tokens).split(',')]
# register names and their numerical values
_regs = {
    'R0': 0, 'R1': 1, 'R2': 2, 'R3': 3,
    'R4': 4, 'R5': 5, 'R6': 6, 'R7': 7, 'WR': 7,
    'R8': 8, 'R9': 9, 'SB': 9,
    'R10': 10, 'SL': 10, 'R11': 11, 'FP': 11,
    'R12': 12, 'IP': 12, 'R13': 13, 'SP': 13,
    'R14': 14, 'LR': 14, 'R15': 15, 'PC': 15,
    'A1':0,'A2':1,'A3':2,'A4':3,
    'V1':4,'V2':5,'V3':6,'V4':7,
    'V5':8,'V6':9,'V7':10,'V8':11,
}
def isReg(token, low = False):
    """ low: only lower registers are valid """
    try:
        parseReg(token, low)
        return True
    except:
        return False
def parseReg(token, low = False):
    """ Convert 'Rn' to n """
    token = token.upper()
    if not token in _regs:
        raise ValueError("Not a valid register name: %s" % token)
    r = _regs[token]
    if low and r >= 8:
        raise ValueError("Bad register for this context: %s" % token)
    return r
def isNumber(token, bits):
    try:
        parseNumber(token, bits)
        return True
    except:
        return False
def parseNumber(token, bits):
    r = int(token, 0)
    if r >= (1<<bits):
        raise ValueError("Number too large: %s" % token)
    return r
def isLabel(token):
    return len(token) > 0 and (token[0].isalpha() or token[0] == '_')

# Classes for instructions
class Instruction:
    """ Abstract, don't instantiate! """
    def match(tokens):
        """
        Tests if this instruction matches given set of tokens.
        If yes, returns new instance of that instruction [and removes used tokens??]
        """
        raise NotImplementedError
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
    def _getOffset(self, label):
        """ Returns correct offset to getAddr """
        return self._getAddr(label) - ((self.pos + 4) & 0xFFFFFFFC) # cut last 4 bits
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
        return pack("<H", self._getCodeN())
    def _getCodeN(self):
        """ Override this to return numeric code """
        raise NotImplementedError("Don't instantiate this class!")
    def getSize(self):
        """ returns size of this instruction in bytes """
        return 2
    def setSrcLine(self, srcline):
        """ Set source code line info for debugging later """
        self.srcline = srcline
    def __str__(self):
        ret = str(self.srcline)
        if self.pos:
            ret += "\t@ 0x%X" % self.pos
        return ret
class DCB(Instruction):
    """ DCB with any number of bytes """
    def __init__(self, code):
        """
        code is a ready instruction code, like '\\x00\\xBF'
        """
        self.code = code
    def getSize(self):
        return len(self.code)
    def getCode(self):
        return self.code
class DCx(Instruction):
    """ DCW or DCD. For DCB (command db) see class DCB """
    def __init__(self, size, val):
        """ val is either number (dec/0xhex/0oct/0bbin) or label/address, or label+n """
        if size not in [2,4]:
            raise ValueError("Unsupported size %d, it must be either 2 or 4" % size)
        self.size = size
        if type(val) is not str or len(val) < 1:
            raise ValueError("Bad value: %s" % repr(val))
        add = 0
        if '+' in val:
            val, add = val.split('+')
            add = int(add, 0)
        if size != 4 and not val[0].isdigit(): # address must be 4bytes!
            raise ValueError("addrs are only valid for DCD, not DCW")
        self.val = val
        self.add = add
    def getSize(self):
        return self.size
    def getCode(self):
        if self.val[0].isdigit():
            val = int(self.val, 0)
        else:
            val = self._getAddr(self.val)
        val += self.add
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
        # don't use getOffset here as we don't need to clip last 2 bits
        offset = self._getAddr(self.dest) - (self.pos+4)
        offset = offset >> 1
        usereg = self.reg != None
        if abs(offset) >= 1<<(6 if usereg else 8):
            raise ValueError("Offset %X exceeds maximum of %X!" %
                             (offset, 1<<11))
        if usereg:
            code = ((0b1011 << 12)
                    + (self.cond << 11)
                    + (0 << 8)
                    + ((offset >> 5) << 9)
                    + (1 << 8)
                    + ((offset & 0b11111) << 3)
                    + (self.reg))
        else:
            code = ((0b1101 << 12)
                    + (self.cond << 8)
                    + (offset))
        return pack('<H', code)
class Bxx(Jump):
    _conds = {
        'CC': 0x3, 'CS': 0x2, 'EQ': 0x0, 'GE': 0xA,
        'GT': 0xC, 'HI': 0x8, 'LE': 0xD, 'LS': 0x9,
        'LT': 0xB, 'MI': 0x4, 'NE': 0x1, 'PL': 0x5,
        'VC': 0x7, 'VS': 0x6,
    }
    codes = ['B'+x for x in _conds]
    def __init__(self, dest, cond):
        cond = cond.upper()
        if not cond in self._conds:
            raise ValueError("Bxx: incorrect condition %s" % cond)
        Jump.__init__(self, dest, self._conds[cond])
class CBx(Jump):
    def __init__(self, is_equal, args):
        args = parseArgs(args)
        if not (len(args) == 2
               and isReg(args[0], True)
               and isLabel(args[1])):
            raise ValueError("CBx: incorrect arguments")
        Jump.__init__(self, args[1], 0 if is_equal else 1, parseReg(args[0]))
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
class SimpleInstruction(Instruction):
    """ CMP, MOV, ADD... either Rx,Rx or Rx,N """
    def __init__(self, args, mcasi, hireg):
        """
        args is list of tokens (to be parsed);
        mcasi is opcode for Rx,N;
        hireg is opcode for Rx,Rx.
        """
        args = parseArgs(args)
        if not (len(args) == 2 and
                ((isReg(args[0], True) and isNumber(args[1], 8)) or
                 (isReg(args[0]) and isReg(args[1])))):
            raise ValueError("Invalid args: %s" % repr(args))
        self.args = args
        if (mcasi and mcasi >= 0b100) or (hireg and hireg >= 0b100):
            raise ValueError("Invalid mode: %d, %d" % (mcasi, hireg))
        self.mcasi = mcasi
        self.hireg = hireg
    def _getCodeN(self):
        a0 = parseReg(self.args[0])
        imm = not isReg(self.args[1])
        if imm:
            a1 = parseNumber(self.args[1], 8)
        else:
            a1 = parseReg(self.args[1])

        if imm and a0 < 8:
            return (0x1 << 13) + (self.mcasi << 11) + (a0 << 8) + (a1 << 0)
        else:
            h0 = a0 >> 3
            h1 = a1 >> 3
            return (0x11 << 10) + (self.hireg << 8) + (h0 << 7) + (h1 << 6) + (a1 << 3) + (a0 << 0)
class AluSimple(Instruction):
    """ This represents ADC, AND, ASR, etc """
    _ops = {
        "ADC": 0x5, "AND": 0x0, "ASR": 0x4, "BIC": 0xE,
        "CMN": 0xB, #"CMP": 0xA, # this CMP will not be used - see above
        "EOR": 0x1, "XOR": 0x1, # just an alias
        "LSL": 0x2, "LSR": 0x3, "MUL": 0xD,
        "MVN": 0xF, "NEG": 0x9, "ORR": 0xC, "OR": 0xC,
        "ROR": 0x7, "SBC": 0x6, "TST": 0x8,
    }
    codes = _ops
    def __init__(self, op, args):
        args = parseArgs(args)
        if not (op in self._ops
                and len(args) == 2
                and isReg(args[0], True)
                and isReg(args[1], True)):
            raise ValueError("Invalid args: %s" % repr(args))
        self.rd = parseReg(args[0], True)
        self.rs = parseReg(args[1], True)
        self.op = self._ops[op]
    def _getCodeN(self):
        return (0x10 << 10) + (self.op << 6) + (self.rs << 3) + (self.rd)
class ADDSUB(Instruction):
    def __init__(self, is_sub, args):
        args = parseArgs(args)
        self.is_sub = 1 if is_sub else 0
        if len(args) == 2:
            if isReg(args[1], True): # ADD Rx,Ry is alias to ADD Rx,Rx,Ry
                self.isImm = False
                self.rd = parseReg(args[0], True)
                self.rs = parseReg(args[0], True)
                self.ro = parseReg(args[1], True)
            else:
                self.isImm = True
                self.rd = parseReg(args[0])
                self.rs = None
                if self.rd >= 8:
                    if self.rd != _regs['SP']:
                        raise ValueError("Invalid hireg: %s" % repr(args))
                    self.imm = parseNumber(args[1], 7)
                else:
                    self.imm = parseNumber(args[1], 8)
        elif len(args) == 3:
            self.rd = parseReg(args[0],True)
            if isReg(args[2]):
                self.rs = parseReg(args[1],True)
                self.isImm = False
                self.ro = parseReg(args[2],True)
            else:
                self.rs = parseReg(args[1])
                self.isImm = True
                if self.rs >= 8:
                    if self.rs != _regs['SP']:
                        raise ValueError("Invalid hireg: %s" % repr(args))
                    if is_sub:
                        raise ValueError("Cannot SUB from SP to loreg: %s" % repr(args))
                    # ADD Rd, SP,imm -> shifted imm must fit 8bits
                    self.imm = parseNumber(args[2], 10) >> 2
                else:
                    self.imm = parseNumber(args[2], 3)
        else:
            raise ValueError("Invalid args: %s" % repr(args))
    def _getCodeN(self):
        if self.isImm:
            if self.rs == None: # 8bit imm
                if self.rd == _regs['SP']:
                    return (0xb0 << 8) + (self.is_sub << 7) + self.imm
                # duplicate SimpleInstruction
                return (1 << 13) + ((3 if self.is_sub else 2) << 11) + (self.rd << 8) + self.imm
            elif self.rs == _regs['SP']: # ADD Rd, SP,imm
                return (0b10101 << 11) + (self.rd << 8) + self.imm
            else: # 3-bit offset
                return (3 << 11) + (1 << 10) + (self.is_sub << 9) + (self.imm << 6) + (self.rs << 3) + (self.rd)
        else:
            return (3 << 11) + (0 << 10) + (self.is_sub << 9) + (self.ro << 6) + (self.rs << 3) + (self.rd)
class MOVW(Instruction):
    """ This represents MOV.W insruction """
    def __init__(self, args, setflags):
        args = parseArgs(args)
        if len(args) != 2:
            raise ValueError("Invalid arguments for MOV.W")
        self.rd = parseReg(args[0])
        self.val = parseNumber(args[1], 32)
        self.s = 1 if setflags else 0
    def getCode(self):
        # 11110 i 0 0010 S 1111   0 imm3 rd4 imm8
        if self.val <= 0xFF: # 1 byte
            val = self.val
        else:
            b1 = self.val >> 24
            b2 = (self.val >> 16) & 0xFF
            b3 = (self.val >> 8) & 0xFF
            b4 = self.val & 0xFF
            if b1 == b2 == b3 == b4:
                val = (0b11 << 8) + b1
            elif b1 == 0 and b3 == 0:
                val = (0b01 << 8) + b2
            elif b2 == 0 and b4 == 0:
                val = (0b10 << 8) + b1
            else:
                # rotating scheme
                def rol(n, ofs):
                    return ((n << ofs) & 0xFFFFFFFF) | (n >> (32-ofs))
                    # maybe buggy for x >= 1<<32,
                    # but we will not have such values -
                    # see parseNumber above for explanation
                ok = False
                for i in range(0b1000, 32): # lower values will cause autodetermining to fail
                    val = rol(self.val, i)
                    if (val & 0xFFFFFF00) == 0 and (val & 0xFF) == 0x80 + (val & 0x7F): # correct
                        ok = True
                        val = ((i << 7) & 0xFFF) + (val & 0x7F)
                        break
                if not ok: # try T3 encoding
                    if val <= 0x7FFF and not self.s:
                        val = val << 1 # don't know why, but will have val/2 without this
                        imm4 = val >> 12
                        i = (val >> 11) & 1
                        imm3 = (val >> 8) & 0b111
                        imm8 = val & 0xFF
                        code1 = (0b11110 << 11) + (i << 10) + (0b100100 << 4) + imm4
                        code2 = (imm3 << 12) + (self.rd << 8) + imm8
                        return pack("<HH", code1, code2)
                    else:
                        raise ValueError("Cannot use MOV.W for value 0x%X!" % self.val)
        # now we have correctly encoded value
        i = val >> 11
        imm3 = (val >> 8) & 0b111
        imm8 = val & 0xFF
        code1 = (0b11110 << 11) + (i << 10) + (0b00010 << 5) + (self.s << 4) + 0b1111
        code2 = (imm3 << 12) + (self.rd << 8) + imm8
        return pack("<HH", code1, code2)
    def getSize(self):
        return 4
class ADR(Instruction):
    """
    ADR Rx, label
    """
    def __init__(self, args):
        args = parseArgs(args)
        if not (len(args) == 2 and
                (isReg(args[0], True) and isLabel(args[1]))):
            raise ValueError("Invalid args: %s" % repr(args))
        self.rd = args[0]
        self.dest = args[1]
    def _getCodeN(self):
        rd = parseReg(self.rd, True)
        ofs = self._getOffset(self.dest) # offset to that label
        if ofs < 0:
            raise ValueError("Negative offset for ADR is not supported: %X" % ofs)
        if abs(ofs) >= (1 << 10):
            raise ValueError("Offset is too far")
        if ofs & 0b11: # not 4-divisible
            raise ValueError("offset 0x%X is not divisible by 4" % ofs)
        ofs = ofs >> 2
        return (0x14 << 11) + (rd << 8) + ofs
class UXTx(Instruction):
    def __init__(self, is_halfword, args):
        args = parseArgs(args)
        if not (len(args) == 2 and
                isReg(args[0], True) and isReg(args[1], True)):
            raise ValueError("Invalid args: %s" % repr(args))
        self.rd = args[0]
        self.rs = args[1]
        self.b = 0 if is_halfword else 1
    def _getCodeN(self):
        rd = parseReg(self.rd, True)
        rs = parseReg(self.rs, True)
        return (0b101100101 << 7) + (self.b << 6) + (rs << 3) + (rd)
class LDRSTR(Instruction):
    """ LDR and STR """
    def __init__(self, is_load, datatype, args):
        """
        is_load determines LDR from STR
        datatype is eithore None or 'B' (byte)
        args is list of tokens to be parsed
        """
        argsj = ' '.join(args)
        if '[' in argsj:
            reg, args = argsj.split('[')
            reg = reg.strip().strip(',')
            if args[-1] != ']':
                raise ValueError("Unclosed '['?")
            args = parseArgs([args[:-1]])
            if len(args) == 1:
                rb = args[0]
                ro = '0'
            elif len(args) == 2:
                rb, ro = args
            else:
                raise ValueError("Illegal args count for LDR/STR, %s" % repr(args))
        else:
            args = parseArgs(args)
            reg = args.pop(0)
            if len(args) == 1:
                rb = 'PC'
                ro = args[0]
            elif len(args) == 2:
                rb, ro = args
            else:
                raise ValueError("Illegal args count for LDR/STR, %s" % repr(args))
        if datatype:
            if not datatype in ['B']:
                raise ValueError("Unsupported datatype for LDR/STR, %s" % datatype)
            if rb in ['PC','SP']:
                raise ValueError("Unsupported register for LDR/STR with datatype %s" % datatype)
        self.b = 1 if datatype == 'B' else 0
        self.shift = {'':2,'H':1,'B':0}[datatype]
        self.rd = reg
        self.rb = rb
        self.ro = ro
        self.l = 1 if is_load else 0
    def _getCodeN(self):
        rd = parseReg(self.rd, True)
        rb = parseReg(self.rb)
        if isReg(self.ro, True):
            rb = parseReg(self.rb, True) # must be low register too
            ro = parseReg(self.ro, True)
            return (0x5 << 12) + (self.l << 11) + (self.b << 10) + (0b0 << 9) + (ro << 6) + (rb << 3) + rd
        # imm
        if isLabel(self.ro):
            imm = self._getOffset(self.ro)
        elif rb in (_regs['PC'], _regs['SP']):
            imm = parseNumber(self.ro, 8)
        else:
            imm = parseNumber(self.ro, 7) # limited size

        if imm & ((1<<self.shift)-1): # not 2^numbytes-divisible
            raise ValueError("imm 0x%X is not divisible by 4" % imm)
        if imm < 0:
            raise ValueError("Negative offset 0x%X" % imm)
        imm = imm >> self.shift
        if abs(imm) >= (1 << (8 if rb in (_regs['PC'],_regs['SP']) else 3)):
            raise ValueError("Offset is too far: 0x%X" % imm)
        if rb == _regs['PC']: # pc-relative
            if not self.l:
                raise ValueError("PC-relative STR is impossible")
            return (0x9 << 11) + (rd << 8) + imm
        if rb == _regs['SP']: # sp-relative
            return (0x9 << 12) + (self.l << 11) + (rd << 8) + imm
        return (0x3 << 13) + (self.b << 12) + (self.l << 11) + (imm << 6) + (rb << 3) + rd
class EmptyInstruction(Instruction):
    """ Pseudo-instruction with zero size, for labels """
    def __init__(self):
        self.srcline = None
    def getSize(self):
        return 0
    def getCode(self):
        return '' # empty code
class ALIGN(Instruction):
    """ Adds meaningless instructions (NOP) to align following code/data """
    def __init__(self, bound):
        if bound != '4':
            raise ValueError("Bad alignment, currently only 4 supported: %s" % bound)
        self.bound = bound
    def getSize(self):
        rest = self.pos % 4
        return rest
    def getCode(self):
        return '\x00\xBF\x00\xBF'[:self.getSize()]

def parse_args():
    """ Not to be confused with parseArgs :) """
    import argparse
    parser = argparse.ArgumentParser(
        description="Pebble firmware patcher")
    parser.add_argument("patch", nargs='+', type=argparse.FileType("r"),
                        help="File with a patch to apply")
    parser.add_argument("-o", "--output", required=True, type=argparse.FileType("wb"),
                        help="Output file name")
    parser.add_argument("-t", "--tintin", nargs='?', default="tintin_fw.bin", type=argparse.FileType("rb"),
                        help="Input tintin_fw file, defaults to tintin_fw.bin")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Print debug information while patching")
    parser.add_argument("-D", "--define", action="append", default=[],
                        help="Add some #define'd constant. Usage: either -D constant or -D name=val")
    return parser.parse_args()

def patch_fw(args):
    data = ""
    datar = ""

    # for compatibility with older callers (as previous versions expected this
    # to be a single open file)
    if type(args.patch) is not list:
        args.patch = [args.patch]

    data = args.tintin.read()
    datar = data

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
        """
        Convert list of hexadecimal bytes to string (byte array)
        Also supports "strings\r" as elements
        """
        ret = ''
        for v in vals:
            if v.startswith('"') and v.endswith('"'):
                ret += parse_str(v)
            else:
                myassert(len(v) == 2, "Malformed hex string at %s" % v)
                ret += pack('B', tryc(lambda: int(v, 16), "Malformed hex string at %s" % v))
        return ret
    def parse_str(s):
        """ Unescape \", \r and \n in string; also remove enclosing ""-s """
        if not (s.startswith('"') and s.endswith('"')):
            raise ValueError("Not a valid string")
        s = s[1:-1]
        return s.replace('\\n','\n').replace('\\r','\r').replace('\\"', '"')

    def search_addr(sig):
        """
        This function tries to match signature to data,
        and returns a memory address of found match only if it is the only one.
        sig is list of bytes (in hex), "?[n]" or "@"
        bytes must match, ? means any byte, "?n" means any n bytes,
        @ is required position (default position is at start of mask)
        """
        def is_hex(n):
            return n.isdigit() or n.lower() in 'abcdef'
        def masklen():
            """ Returns length of given mask in bytes """
            b=0
            for m in mask:
                if type(m) is str:
                    b += len(m)
                elif type(m) is int:
                    b += m
                else:
                    raise ValueError(m) # must never happen
            return b
        if not sig:
            raise ValueError("Cannot search for empty mask")
        offset = 0 # for @
        mask = [] # form: str, int(offset), str...
        string = '' # current string
        for s in sig:
            if len(s) == 2 and is_hex(s[0]) and is_hex(s[1]): # byte
                b = int(s, 16) # must work as we checked already
                string += chr(b)
            elif s == '@':
                myassert(offset == 0, "Multiple '@'s (or mask starting with skip) - it is not good! Where am I?")
                offset = masklen() + len(string)
            elif s[0] == '?':
                s = s[1:]
                if len(s) == 0:
                    val = 1
                else:
                    val = tryc(lambda: int(s), "Not a number: %s" % s)
                if string: # this skip is not very first mask item
                    mask.append(string)
                    string = ''
                    mask.append(val)
                elif not mask: # we are at first mask item, which must be string,
                               #so just treat this skip as negative offset
                    offset = -val
                else: # consecutive skips must be merged
                    mask[-1] += val
            elif s[0] == '"' and s[-1] == '"': # string specified
                string += s[1:-1]
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
            return False, -1
        if len(matches) > 1:
            print "Multiple match - ambiguous, so failing"
            return False, -1
        #print "Mask found at %X" % (matches[0] + offset + 0x08010000)
        return matches[0] + offset + 0x08010000, masklen()-offset

    blocks = [] # list of all our blocks
    masklens = [] # list of mask lengths for each block
    blocknames = []
    procs = {} # all known procedure names -> addr
    # and for #if's:
    definitions = {}
    for d in args.define:
        if '=' in d:
            name,val = d.split('=', 1)
            definitions[name] = val
        else:
            definitions[d] = True
    if_state = [True]
    # This is a stack.
    # True: in matched If or unmatched If's Else (processing)
    # False: in unmatched If or matched If's Else
    # (skipping, just counting If/Endif)
    # Initial True must always stay there, or else we have something unmatched

    def load_file(patchfile, recindent=''):
        """
        This function loads a patch file.
        Recindent is used for recursively loaded files (#include)
        """
        print "%sLoading %s..." % (recindent, patchfile.name)
        # scratchpad:
        mask = [] # mask for determining baddr
        mlen = 0 # length of mask in bytes
        baddr = None # block beginning
        addr = None # current instruction starting address, or block beginning
        block = None # current block - list of instructions
        label = None # label saved for further use
        blockname = None # proc

        global lnum, line

        for lnum, line in enumerate(patchfile):
            line = line[:-1].strip() # remove \n and leading/trailing whitespaces
            if line.find(';') >= 0:
                line = line[:line.find(';')].strip()
            if len(line) == 0: # empty line
                continue

            # now process #if's:
            if line[0] == '#':
                tokens = line.split()
                cmd,cargs = tokens[0],tokens[1:]
                if cmd == "#define":
                    myassert(len(cargs)>0, "At least one argument required for #define!")
                    name = cargs[0]
                    if len(cargs) >= 2:
                        val = cargs[1]
                    else:
                        val = True
                    if args.debug:
                        print "%s#defining %s to %s" % (recindent, name, val)
                    definitions[name] = val
                elif cmd in ["#ifdef", "#ifval"]:
                    myassert(len(cargs)>0, "Arguments required!")
                    if cmd == "#ifval":
                        vals = definitions.values()
                    # "OR" logic, as one can implement "AND" with nested #ifdef's
                    matched = False
                    for a in cargs:
                        if cmd == "#ifdef":
                            matched = matched or (a in definitions)
                        else: # ifval
                            matched = matched or (a in vals)
                    if_state.append(matched)
                elif cmd == "#else":
                    myassert(len(if_state)>1, "Unexpected #else")
                    if_state[-1] = not if_state[-1]
                elif cmd == "#endif":
                    myassert(len(if_state)>1, "Unexpected #endif")
                    if_state.pop()
                elif cmd == "#include":
                    myassert(len(cargs) == 1, "One argument required!")
                    import os.path
                    filename = os.path.join(os.path.dirname(patchfile.name), cargs[0])
                    f = open(filename, 'r')
                    load_file(f, recindent+'> ') # recursion
                else:
                    myassert(False, "Unknown #command %s" % cmd)
                continue # we already handled this line
            if not if_state[-1]: # skipping current block
                continue

            tokens = line.split()
            if len(tokens) == 0:
                continue # only comments/whitespaces
            if block == None: # outside of block
                excess = [] # tokens after '{'
                for t in tokens:
                    if t == '{': # end of mask, start of block
                        addr, mlen = search_addr(mask)
                        myassert(addr != False, "Mask not found. Failing.")
                        baddr = addr
                        block = [] # now in block
                    elif block == None: # another part of mask, block not started yet
                        mask.append(t)
                    else:
                        excess.append(t) # pass these to the following code
                tokens = excess # pass any excess tokens to below
            if len(tokens) > 0: # normal line inside block, or remainder from after '{'
                if len(tokens) == 1 and tokens[0] == '}': # end of block
                    if label: # label at the end of block
                        # append pseudo-instruction for it
                        instr = EmptyInstruction()
                        instr.setPosition(addr)
                        instr.setLabel(label)
                        label = None
                        block.append(instr)
                    blocks.append(block)
                    masklens.append(mlen)
                    blocknames.append(blockname)
                    myassert(blockname not in procs, "Duplicate name: %s" % blockname)
                        #-- this was checked when 'proc' was read (probably in block beginning; see below),
                        #   but from that time we could receive new names
                    procs[blockname] = baddr # save this block's address for future use
                    mask = []
                    baddr = None
                    addr = None
                    block = None
                    blockname = None
                    continue
                if tokens[0] == "proc": # this block has name!
                    myassert(len(tokens) == 2, "proc keyword requires one argument")
                    myassert(not blockname, "Duplicate 'proc' statement, this block already has name <%s>" % blockname)
                    myassert(blockname not in procs, "Duplicate name: %s" % blockname)
                    blockname = tokens[1]
                    continue
                elif tokens[0] == 'val': # read value (currently only 4-bytes)
                    myassert(len(tokens) == 2, "val keyword requires one argument (name)")
                    valname = tokens[1]
                    myassert(valname not in procs, "Duplicate name: %s" % valname)
                    val = unpack('<I', data[addr-0x8010000:addr-0x8010000+4])[0]
                    print "%sDetermined: %s = 0x%X" % (recindent, valname, val)
                    procs[valname] = val # save this value to global context
                    continue

                if tokens[0].endswith(':'): # label
                    label = tokens[0][:-1]
                    del tokens[0]
                    if len(tokens) == 0:
                        continue # line contains only label; will use it in next pass
                    # else go below: all following items can have label
                instr = None # this will be current instruction
                try:
                    if tokens[0] in ["db", "DCB"]: # define byte - most common instruction
                        myassert(len(tokens) >= 2, "Error - 'db' without value?")
                        del tokens[0]
                        instr = DCB(parse_hex(tokens))
                    elif tokens[0] in ["DCD", "DCW"]:
                        myassert(len(tokens) == 2, "Bad value count for DCx")
                        instr = DCx(2 if tokens[0]=="DCW" else 4, tokens[1])
                    elif tokens[0] == 'global': # global label
                        myassert(len(tokens) == 2, "Error - illegal 'global' call")
                        label = tokens[1]
                        myassert(label not in procs, "Duplicate name: %s" % label)
                        if label.endswith(':'):
                            label = label[:-1] # remove trailing ':', if any
                        instr = EmptyInstruction()
                        # and store address to globals
                        procs[label] = addr
                    elif tokens[0] in ["ALIGN"]:
                        myassert(len(tokens) == 2, "Error - must specify 1 argument for ALIGN")
                        instr = ALIGN(tokens[1])
                    elif tokens[0] in ["CMP", "MOV"]:
                        codes = {"CMP": (1, 1),
                                "MOV": (0, 2),
                                "ADD": (2, 0), # unused now
                                }
                        code = codes[tokens[0]]
                        del tokens[0]
                        instr = SimpleInstruction(tokens, code[0], code[1])
                    elif tokens[0] in ["ADD", "SUB"]:
                        instr = ADDSUB(tokens[0] == "SUB", tokens[1:])
                    elif tokens[0] in AluSimple.codes:
                        instr = AluSimple(tokens[0], tokens[1:])
                    elif tokens[0] in ["MOV.W", "MOVS.W"]:
                        instr = MOVW(tokens[1:], 'S' in tokens[0])
                    elif tokens[0] in ["ADR"]:
                        instr = ADR(tokens[1:])
                    elif tokens[0] in ["UXTB", "UXTH"]:
                        instr = UXTx('H' in tokens[0], tokens[1:])
                    elif tokens[0] in ["LDR", "STR", "LDRB", "STRB"]:
                        instr = LDRSTR(tokens[0].startswith("LDR"), tokens[0][3:], tokens[1:])
                    elif tokens[0] in ["BX"]:
                        del tokens[0]
                        instr = SimpleInstruction(['R0,', tokens[1]], -1, 3)
                    elif tokens[0] in Bxx.codes:
                        myassert(len(tokens) == 2, "Bad arguments count for Bxx")
                        instr = Bxx(tokens[1], tokens[0][1:])
                    elif tokens[0] in ["CBZ", "CBNZ"]:
                        instr = CBx(tokens[0] == "CBZ", tokens[1:])
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
                except ValueError as e:
                    myassert(False, "Syntax error: " + str(e))
                instr.setSrcLine((patchfile.name, lnum, line))
                if label: # current instruction has a label?
                    instr.setLabel(label)
                    label = None
                instr.setPosition(addr)
                addr += instr.getSize()
                block.append(instr)
        if block: # unterminated?
            print "%sWARNING: unterminated block detected, will ignore it" % recindent
        print "%sFile %s loaded" % (recindent, patchfile.name)

    ###############################
    # load all required patch files
    for p in args.patch:
        load_file(p)

    # now apply patches
    print "Applying patches..."
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
            if args.debug:
                print i
            icode = i.getCode()
            if len(icode) != i.getSize():
                raise ValueError("Instruction length mismatch: expected %d, got %d. %s" %
                                 (len(icode), i.getSize(), str(i)))
            code += icode
        if len(code) > masklens[bnum]:
            print "WARNING: code length exceeds mask length! Strange things may happen..."
        blen = len(datar)
        datar = datar[:start] + code + datar[start+len(code):]
        if len(datar) != blen:
            raise Exception("Length mismatch - was %d, now %d" % (blen, len(datar)))
        print "%d bytes of %d-bytes mask patched at %X" % (len(code), masklens[bnum], start)
    print "Saving..."
    args.output.write(datar)
    args.output.close()
    print "Done."

if __name__ == "__main__":
    args = parse_args()
    patch_fw(args)
