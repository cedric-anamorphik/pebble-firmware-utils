# This is a parser for assembler listings (?)

import asm
from itertools import chain

class FilePos:
    " This holds current line info (filename, line text, line number) "
    def __init__(self, filename, lnum=-1, line=''):
        self.filename = filename
        self.lnum = lnum
        self.line = line
    def setLine(self, lnum, line):
        self.lnum = lnum
        self.line = line
    def getLnum(self):
        return self.lnum
    def clone(self):
        " Useful for instructions to hold exact position "
        return FilePos(self.filename, self.lnum, self.line)
    def __str__(self):
        return "\t\"%s\"\n%s, line %s" % (self.line, self.filename, self.lnum+1)

class SyntaxError(Exception):
    def __init__(self, msg, pos):
        self.msg = msg
        self.pos = pos
    def __str__(self):
        return "%s: %s" % (str(self.pos), self.msg)

def uncomment(line):
    """ Removes comment, if any, from line. Also strips line """
    linewoc = '' # line without comment
    in_str = ''
    for c in line:
        if in_str:
            if c == in_str:
                in_str = ''
        else:
            if c in ';': # our comment character
                break
            elif c in '"\'':
                in_str = c
        linewoc += c
    return linewoc.strip() # remove leading and trailing spaces

def parseInstruction(line, pos):
    """
    This methods converts line from source file to Instruction (opcode and args?).
    """
    try:
        opcode, arg = line.split(None,1)
    except ValueError: # only one token
        opcode = line
        arg = ''

    # now parse args
    args = asm.List()
    s = '' # string repr of current arg
    t = None # type of current arg: None (no current), n(numeric), ',"(quoted str), l(reg or label)
    br = False # whether we are in [] block
    for c in arg+'\n': # \n will be processed as last character
        domore = False # if current character needs to be processed further
        if t == None: # state: no current arg
            domore = True
        elif t in "'\"": # quoted string
            if c == t: # end of string
                args.append(asm.Str(s))
                s = ''
                t = None
            elif c == '\\': # backslash in string
                t += '\\'
            else:
                s += c
        elif t in ['"\\', "'\\"]: # state: backslash in quoted string
            s += c
            t=t[0]
        elif t == 'n': # number, maybe hex
            if c.isdigit() or c in 'xXbB':
                s += c
            else:
                domore = True # need to process current character further
                try:
                    args.append(asm.Num(s))
                except ValueError:
                    raise SyntaxError("Invalid number: %s" % s, pos)
                s = ''
                t = None
        elif t == 'l': # label or reg
            if c.isalnum() or c == '_':
                s += c
            else:
                domore = True
                if asm.Reg.is_reg(s):
                    a = asm.Reg(s)
                else:
                    a = asm.Label(s)
                args.append(a)
                s = ''
                t = None
        else:
            raise ValueError("Internal error: illegal type state %s" % t)

        if domore: # current character was not processed yet
            if c.isdigit():
                s += c
                t = 'n'
            elif c.isalpha() or c == '_':
                s += c
                t = 'l' # label
            elif c in "'\"": # quoted str
                t = c
            elif c.isspace(): # including last \n
                continue # skip
            elif c == ',':
                continue # skip - is it a good approach? allows both "MOV R0,R1" and "MOV R1 R1"
            elif c == '[':
                if br:
                    raise SyntaxError("Nested [] are not supported", pos)
                br = True
                gargs = args
                args = asm.List()
            elif c == ']':
                if not br:
                    raise SyntaxError("Unmatched ]", f, line)
                gargs.append(args)
                args = gargs
                br = False
            else:
                raise SyntaxError("Bad character: %c" % c, pos)
    # now let's check that everything went clean
    if t:
        raise SyntaxError("Unterminated string? %c" % t, pos)
    if br:
        raise SyntaxError("Unmatched '['", pos)

    try:
        return asm.findInstruction(opcode, args, pos)
    except IndexError:
        raise SyntaxError("Unknown instruction: %s %s" % (opcode, ','.join([repr(x) for x in args])), pos)

def parseBlock(f, pos, definitions):
    " Parses one mask from patch file. Returns results (mask and block contents) as tuple "

    # for #commands:
    if_state = [True] # this True should always be there

    # current mask
    mask = []
    # current mask item (bytestring)
    bstr = ''
    # current mask item (integer, number of bytes to skip)
    bskip = 0

    # and to be used when in block:
    instructions = None

    for lnum, line in enumerate(f, pos.getLnum()+1):
        pos.setLine(lnum,line.strip())
        line = uncomment(line)
        if not line: # skip empty lines
            continue

        if line[0] == '#':
            tokens = line.split()
            cmd,args = tokens[0],tokens[1:]
            # these will not depend on if_state...
            if cmd in ["#ifdef", "#ifndef", "#ifval", "#ifnval"]:
                if not args:
                    raise SyntaxError("%s requires at least one argument" % cmd, pos)
                newstate = 'n' in cmd # False for 'ifdef', etc.
                if "val" in cmd:
                    vals = definitions.values()
                # "OR" logic, as one can implement "AND" with nested #ifdef's
                # so any matched arg stops checking
                for a in args:
                    if (("def" in cmd and a in definitions) or
                        ("val" in cmd and a in vals)):
                        newstate = not newstate
                        break
                if_state.append(newstate)
                continue
            elif cmd == "#else":
                if len(if_state) <= 1:
                    raise SyntaxError("Unexpected #else", pos)
                if_state[-1] = not if_state[-1]
                continue
            elif cmd == "#endif":
                if_state.pop() # remove latest state
                if not if_state:
                    raise SyntaxError("Unmatched #endif", pos)
                continue
            # ...now check if_state...
            if not if_state[-1]:
                continue # #define must only work if this is met
            # ...and following will depend on it
            if cmd == "#define":
                if not args:
                    raise SyntaxError("At least one argument required for #define", pos)
                name = args[0]
                val = True
                if args[1:]:
                    val = line.split(None, 2)[2] # remaining args as string
                definitions[name] = val
            else:
                raise SyntaxError("Unknown command: %s" % cmd, pos)
            continue # to next line

        # and now for non-# lines
        if not if_state[-1]:
            continue # skip any code if current condition is not met

        if instructions == None: # not in block, reading mask
            # read mask: it consists of 00 f7 items, ? ?4 items, and "strings"
            tokens = line.split('"')
            if len(tokens) % 2 == 0:
                raise SyntaxError("Unterminated string", pos)
            is_str = False
            for tnum, token in enumerate(tokens):
                if is_str:
                    if bskip:
                        mask.append(bskip)
                        bskip = 0
                    bstr += token
                else:
                    ts = token.split()
                    for t in ts:
                        if len(t) == 2 and t.isalnum():
                            if bskip:
                                mask.append(bskip)
                                bskip = 0
                            try:
                                c = chr(int(t, 16))
                            except ValueError:
                                raise SyntaxError("Bad token: %s" % t, pos)
                            bstr += c
                        elif t[0] == '?':
                            if len(t) == 1:
                                count = 1
                            else:
                                try:
                                    count = int(t[1:])
                                except ValueError:
                                    raise SyntaxError("Bad token: %s" % t, pos)
                            if bstr:
                                mask.append(bstr)
                                bstr = ''
                            bskip += count
                        elif t == '{':
                            if bstr:
                                mask.append(bstr)
                                bstr = ''
                                if bskip:
                                    print mask,bstr,bskip
                                    raise SyntaxError("Internal error: both bstr and bskip used", pos)
                            if bskip:
                                mask.append(bskip)
                                bskip = 0
                            line = '"'.join(tokens[tnum+1:]) # prepare remainder for next if
                            instructions = [] # this will also break for's
                        else:
                            raise SyntaxError("Bad token: %s" % t, pos)
                        if instructions != None: # if entered block
                            break
                is_str = not is_str
                if instructions != None: # if entered block
                    break
        # mask read finished. Now read block content, if in block
        if instructions != None and line: # if still have something in current line
            if line.startswith('}'):
                # FIXME: what to do with remainder?
                remainder = line[1:]
                if remainder:
                    print "Warning: spare characters after '}', will ignore: %s" % remainder
                return (mask, instructions)

            instr = parseInstruction(line, pos)
            instructions.append(instr)
    if mask or bstr or bskip:
        raise SyntaxError("Unexpected end of file", pos)
    return None, None

def parsePatch(f, definitions=None):
    """
    Parses patch file.
    Definitions dictionary is used for #define and its companions.
    """
    if definitions == None:
        definitions = {}
    # list of masks and corresponding instruction listings
    blocks = []

    pos = FilePos(f.name)
    while True:
        mask, content = parseBlock(f, pos, definitions)
        if not mask:
            break
        blocks.append((mask, content))
    return blocks

if __name__ == "__main__":
    import sys
    from pprint import pprint
    pprint(parsePatch(open(sys.argv[1])))
