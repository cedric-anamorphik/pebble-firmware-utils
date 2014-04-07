# This is a library of ARM/THUMB assembler instruction definitions

from struct import pack

def isInstruction(str):
    """
    Returns True if str is a valid assembler instruction name
    """
    pass # TODO

def makeInstruction(op, args):
    """
    Returns an Instruction subclass for given opcode and arguments.
    May raise ValueError if opcodej
    """
    pass

###
# Instruction argument types:
# integer, list of arguments, register, label

class Argument:
    def match(self, other):
        """ Matches this instance with given obj """
        raise NotImplementedError

class Num(int, Argument):
    """ Just remember initially specified value format """
    def __init__(self, val=None, bits=None, positive=False):
        if val is None:
            self.bits = bits
            if bits:
                self.maximum = 1 << bits
            self.positive = positive
            return int.__init__(self, 0)
        self.initial = val
        # and for consistency with Reg:
        self.val = self
        if type(val) == 'str':
            return int.__init__(self, val, 0) # auto determine base
        else:
            return int.__init__(self, val)
    def __str__(self):
        if 'bits' in self:
            if self.bits:
                return "%d-bits integer%s" % (self.bits,
                    ", positive" if self.positive else "")
            return "%sinteger" % ("positive " if self.positive else "")
        return self.initial
    def match(self, other):
        if type(other) is not Num:
            return False
        if 'bits' in self:
            if self.positive and other < 0:
                return False
            if self.bits and abs(other) >= self.maximum:
                return False
            return True
        return other == self

class List(list, Argument):
    def match(self, other):
        if type(other) is not List:
            return False
        if len(self) != len(other):
            return False
        for i,j in zip(self, other):
            if not i.match(j):
                return False
        return True

class Reg(int, Argument):
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
    @staticmethod
    def lookup(name):
        """
        Tries to convert given register name to its integer value.
        Will raise IndexError if name is invalid.
        """
        return _regs[name.upper()]
    @staticmethod
    def is_reg(name):
        """ Checks whether string is valid register name """
        return name.upper() in _regs
    def __init__(self, name=None, hi=None):
        """
        Usage: either Reg('name') or Reg(hi=True/False) or Reg()
        First is a plain register, others are masks
        """
        if not name or name in ['HI','LO']: # pure mask
            if name == 'HI':
                hi = True
            elif name == 'LO':
                hi = False
            self.mask = hi
            name = "%s register" % (
                "High" if hi else
                "Low" if hi == False else
                "Any")
            val = -1
        else:
            val = lookup(name)
        self.name = name
        return int.__init__(self)
    def __str__(self):
        return self.name
    def match(self, other):
        if not type(other) is Reg:
            return False
        if 'mask' in self:
            if self.mask == True: # hireg
                return other >= 8
            elif self.mask == False: # loreg
                return other < 8
            else: # any
                return True
        return self == other

class LabelError(Exception):
    """
    This exception is raised when label requested is not found in given context.
    """
    pass
class Label(Argument):
    def __init__(self, name=None):
        self.name = name
    def __str__(self):
        return self.name
    def match(self, other):
        return type(other) is Label
    def getAddress(self, context):
        if not self.name:
            raise LabelError("This is a mask, not label!")
        try:
            return context[self.name]
        except IndexError:
            raise LabelError
class Str(str, Argument):
    """ This represents _quoted_ string """
    def __init__(self, val=None):
        if val == None:
            val = "String"
            self.mask = True
        else:
            self.mask = False
        return str.__init__(self, val)
    def match(self, other):
        if type(other) is not Str:
            return False
        if self.mask:
            return True
        return self == other

###
# Instructions

class Instruction:
    """
    This class may represent either instruction definition (with masks instead of args)
    or real instruction (with concrete args and context).
    """
    def __init__(self, opcode, args, proc, mask=True):
        self.opcode = opcode
        self.args = args
        self.proc = proc
        self.mask = mask
        self.ctx = None
    def match(self, opcode, args):
        """ Match this definition to given instruction """
        if not self.mask:
            raise ValueError("This is not mask, cannot match")
        # check mnemonic...
        if type(self.opcode) is str:
            if self.opcode != opcode:
                return False
        else: # multiple opcodes possible
            if opcode not in self.opcode:
                return False
        # ... and args
        if len(self.args) != len(args):
            return False
        for a,b in zip(self.args, args):
            if not a.match(b):
                return False
        return True
    def instantiate(self, opcode, args):
        if not self.mask:
            raise ValueError("This is not mask, cannot instantiate")
        return Instruction(opcode, args, self.proc, mask=False)
    def setContext(self, ctx):
        self.ctx = ctx
    def getCode(self):
        if not self.ctx:
            raise ValueError("No context, cannot calculate code")
        code = self.proc(self.ctx, *self.args)
        if type(code) is str:
            return code
        elif type(code) is int:
            return pack('<H', code)
        elif type(code) is tuple:
            return pack('<HH', code[0], code[1])
        raise ValueError("Bad code: %s" % repr(code))
    def getSize(self):
        """ default implementation; may be overriden by decorator """
        return self.size
# list of instruction definitions
_instructions = []
def instruction(opcode, args, size=2, proc=None):
    """
    This is a function decorator for instruction definitions.
    It may also be used as a plain function, then you should pass it a function as proc arg.
    """
    def gethandler(proc):
        instr = Instruction(opcode, args, proc)
        if callable(size):
            instr.getSize = size
        else:
            instr.size = size
        _instructions.append(instr)
        return proc
    if proc: # not used as decorator
        gethandler(proc)
    else:
        return gethandler
def instruct_class(c):
    """ decorator for custom instruction classes """
    _instructions.append(c())
    return c

instruction('ADD', [Reg(hi=False), Num()])(lambda(c,rd,imm):
            (1 << 13) + (2 << 11) + (rd.val << 8) + imm)
def _longJump(ctx, dest, bl):
    offset = dest.offset(ctx, 4)
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
    return (hi,lo)
instruction('BL', [Label()], 4, lambda(ctx,dest): _longJump(ctx,dest,True))
instruction('B.W', [Label()], 4, lambda(ctx,dest): _longJump(ctx,dest,False))
@instruction('BL', [Label()], 4)
def BL(ctx, label):
    pass
@instruct_class
class DCB(Instruction):
    def __init__(self, args=None):
        super(None, args, None)
        if args:
            code = ''
            for a in args:
                if type(a) is Str:
                    code += a
                elif type(a) is Num:
                    code += pack('<C', a)
                else:
                    raise ValueError("Bad argument: %s" % repr(a))
            self.code = code
            self.size = len(code)
    def match(self, opcode, args):
        return opcode in ['DCB', 'db']
    def instantiate(self, opcode, args):
        return DCB(args)
    def getCode(self):
        return self.code
instruction('DCH', [Num(bits=16)], 2, lambda(ctx,num): num)
instruction('DCD', [Num(bits=32)], 4, lambda(ctx,num): pack('<I', num))
