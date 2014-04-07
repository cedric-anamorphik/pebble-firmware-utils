# This is a parser for assembler listings (?)

import asm

def parseLine(f):
    for line in f:
        line = line.strip()
        # comments, empty lines..
        opcode, arg = line.split(None,1)

        # now parse args
        args = []
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
                    s.append(c)
                else:
                    domore = True # need to process current character further
                    args.append(asm.Num(int(s, 0)))
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
                    continue # skip - is it correct?
                elif c == '[':
                    if br:
                        raise SyntaxError("Nested [] are not supported")
                    br = True
                    gargs = args
                    args = asm.List()
                elif c == ']':
                    if not br:
                        raise SyntaxError("Unmatched ]")
                    gargs.append(args)
                    args = gargs
                    br = False
                else:
                    raise SyntaxError("Bad character: %c" % c)
        if t:
            raise SyntaxError("Unterminated string?")
        if br:
            raise SyntaxError("Unmatched '['")
