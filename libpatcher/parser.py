# This is a parser for assembler listings (?)
__all__ = ['parseFile', 'ParseError', 'FilePos']

import asm
from itertools import chain
from mask import Mask
from block import Block
from patch import Patch

class FilePos:
    " This holds current line info (filename, line text, line number) "
    def __init__(self, filename, lnum=-1, line=''):
        self.filename = filename
        self.lnum = lnum
        self.line = line
    def setLine(self, lnum, line):
        self.lnum = lnum
        self.line = line
    def getLine(self):
        return self.line
    def getLnum(self):
        return self.lnum
    def clone(self):
        " Useful for instructions to hold exact position "
        return FilePos(self.filename, self.lnum, self.line)
    #def __repr__(self):
    #    return "\"%s\"\n%s, line %s" % (self.line, self.filename, self.lnum+1)
    def __str__(self):
        return "%s, line %s" % (self.filename, self.lnum+1)

class ParseError(Exception):
    def __init__(self, msg, pos):
        self.msg = msg
        self.pos = pos
    def __str__(self):
        return "%s: %s\n%s" % (str(self.pos), self.msg, self.pos.getLine())

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
    rl = False # whether we are in {register list} block
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
            c = c.replace('r','\r')
            c = c.replace('n','\n')
            s += c
            t=t[0]
        elif t in ['n','ns']: # number, maybe 0xHEX or 0bBINARY or 0octal, or numshift
            if c.isdigit() or c in 'aAbBcCdDeEfFxX':
                s += c
            else:
                domore = True # need to process current character further
                # for consistency with old version's behaviour,
                # treat all numeric 'db' arguments as hexadecimal
                if opcode == "db":
                    s = "0x"+s
                try:
                    if t == 'ns': # numshift for label
                        # args[-1] must exist and be label, or else t would not be 'ns'
                        args[-1].shift = int(s, 0)
                    else: # regular number
                        args.append(asm.Num(s))
                except ValueError:
                    raise ParseError("Invalid number: %s" % s, pos)
                s = ''
                t = None
        elif t == 'l': # label or reg
            if c.isalnum() or c == '_' or (rl and c == '-'):
                s += c
            else:
                domore = True
                if rl: # in list of registers
                    reglist.append(s, pos) # it will handle all validation itself
                else:
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
            if c.isdigit() or c == '-' or (opcode == "db" and c in "AaBbCcDdEeFf"):
                s += c
                t = 'n'
            elif c.isalpha() or c == '_':
                s += c
                t = 'l' # label
            elif c == '+': # shift-value for label
                if args and type(args[-1]) is asm.Label:
                    t = 'ns' # number,shift
                else:
                    raise ParseError("Unexpected +", pos)
            elif c in "'\"": # quoted str
                t = c
            elif c.isspace(): # including last \n
                continue # skip
            elif c == ',':
                continue # skip - is it a good approach? allows both "MOV R0,R1" and "MOV R1 R1"
            elif c == '[':
                if br:
                    raise ParseError("Nested [] are not supported", pos)
                br = True
                gargs = args
                args = asm.List()
            elif c == ']':
                if not br:
                    raise ParseError("Unmatched ]", pos)
                gargs.append(args)
                args = gargs
                br = False
            elif c == '{':
                if rl:
                    raise ParseError("Already in register list", pos)
                rl = True
                reglist = asm.RegList()
            elif c == '}':
                if not rl:
                    raise ParseError("Unmatched }", pos)
                args.append(reglist)
                reglist = None
                rl = False
            else:
                raise ParseError("Bad character: %c" % c, pos)
    # now let's check that everything went clean
    if t:
        raise ParseError("Unterminated string? %c" % t, pos)
    if br:
        raise ParseError("Unmatched '['", pos)

    try:
        return asm.findInstruction(opcode, args, pos)
    except IndexError:
        raise ParseError("Unknown instruction: %s %s" % (opcode, ','.join([repr(x) for x in args])), pos)

def parseBlock(f, pos, definitions, if_state, patch):
    """
    Parses one mask from patch file.
    Returns results (mask and block contents) as tuple
    """

    # mask's starting position
    mpos = None
    # mask's tokens
    mask = []
    # mask offset (for @)
    mofs = 0
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
                    raise ParseError("%s requires at least one argument" % cmd, pos)
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
                    raise ParseError("Unexpected #else", pos)
                if_state[-1] = not if_state[-1]
                continue
            elif cmd == "#endif":
                if_state.pop() # remove latest state
                if not if_state:
                    raise ParseError("Unmatched #endif", pos)
                continue
            # ...now check if_state...
            if not if_state[-1]:
                continue # #define must only work if this is met
            # ...and following will depend on it
            if cmd in ["#define", "#default"]: # default is like define but will not override already set value
                if not args:
                    raise ParseError("At least one argument required for #define", pos)
                name = args[0]
                val = True
                if args[1:]:
                    val = line.split(None, 2)[2] # remaining args as string
                # always set for #define, and only if unset / just True if #default
                if cmd == "#define" \
                        or name not in definitions \
                        or definitions[name] == True:
                    definitions[name] = val
            elif cmd == "#include":
                if not args:
                    raise ParseError("#include requires an argument", pos)
                arg = line.split(None, 1)[1] # all args as a string
                import os.path
                if not os.path.isabs(arg):
                    arg = os.path.join(os.path.dirname(f.name), arg)
                f = open(arg, 'r')
                # parse this file into this patch's library patch.
                # If this is already library patch,
                # its library property will return itself.
                parseFile(f, definitions, patch=patch.library)
            else:
                raise ParseError("Unknown command: %s" % cmd, pos)
            continue # to next line

        # and now for non-# lines
        if not if_state[-1]:
            continue # skip any code if current condition is not met

        # process ${definitions} everywhere
        for d, v in definitions.items():
            if type(v) is str and '${'+d+'}' in line:
                line = line.replace('${'+d+'}', v)

        if instructions == None: # not in block, reading mask
            # read mask: it consists of 00 f7 items, ? ?4 items, and "strings"
            tokens = line.split('"')
            if len(tokens) % 2 == 0:
                raise ParseError("Unterminated string", pos)
            if not mpos:
                mpos = pos.clone() # save starting position of mask
            is_str = False
            for tokennum, token in enumerate(tokens):
                if is_str:
                    if bskip:
                        mask.append(bskip)
                        bskip = 0
                    bstr += token
                else:
                    # process $definitions only outside of "strings" and
                    # outside of {blocks}
                    # FIXME: $definitions inside of {blocks} [and in "strings"?]
                    for d, v in definitions.items():
                        if type(v) is str and '$'+d in token: # FIXME: $var and $variable
                            token = token.replace('$'+d, v)

                    ts = token.split()
                    for t in ts:
                        if len(t) == 2 and t.isalnum():
                            if bskip:
                                mask.append(bskip)
                                bskip = 0
                            try:
                                c = chr(int(t, 16))
                            except ValueError:
                                raise ParseError("Bad token: %s" % t, pos)
                            bstr += c
                        elif t[0] == '?':
                            if len(t) == 1:
                                count = 1
                            else:
                                try:
                                    count = int(t[1:])
                                except ValueError:
                                    raise ParseError("Bad token: %s" % t, pos)
                            if bstr:
                                mask.append(bstr)
                                bstr = ''
                            bskip += count
                        elif t == '@':
                            if mofs:
                                raise ParseError("Duplicate '@'", pos)
                            mofs = sum([len(x) if type(x) is str else x for x in mask]) + len(bstr) + bskip
                        elif t == '{':
                            if bstr:
                                mask.append(bstr)
                                bstr = ''
                                if bskip:
                                    print mask,bstr,bskip
                                    raise ParseError("Internal error: both bstr and bskip used", pos)
                            if bskip:
                                mask.append(bskip)
                                bskip = 0
                            line = '"'.join(tokens[tokennum+1:]) # prepare remainder for next if
                            instructions = [] # this will also break for's
                        else:
                            raise ParseError("Bad token: %s" % t, pos)
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
                return Block(patch, Mask(mask, mofs, mpos), instructions)

            # plain labels:
            label = line.split(None, 1)[0]
            if label.endswith(':'): # really label
                line = line.replace(label, '', 1).strip() # remove it
                instructions.append(asm.LabelInstruction(label[:-1], pos))
            if not line: # had only the label
                continue

            instr = parseInstruction(line, pos)
            instructions.append(instr)
    if mask or bstr or bskip:
        raise ParseError("Unexpected end of file", pos)
    return None

def parseFile(f, definitions=None, patch=None, libpatch=None):
    """
    Parses patch file.
    Definitions dictionary is used for #define and its companions.
    If patch was not provided, it will be created,
    in which case libpatch (patch for includes) must be provided.
    """
    if definitions == None:
        definitions = {}
    if not patch:
        if not libpatch:
            raise ValueError("Neither patch nor libpatch were provided")
        patch = Patch(f.name, libpatch)

    # for #commands:
    if_state = [True] # this True should always remain there

    pos = FilePos(f.name)
    while True:
        block = parseBlock(f, pos, definitions, if_state, patch)
        if not block:
            break
        patch.blocks.append(block)

    return patch
