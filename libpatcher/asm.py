# This is a library of ARM/THUMB assembler instruction definitions
__all__ = ['Num', 'List', 'Reg', 'Label', 'Str',
           #'Argument', 'LabelError', 'Instruction',
           'findInstruction']

from struct import pack

###
# Instruction argument types:
# integer, list of arguments, register, label
class Argument(object):
    def match(self, other):
        """ Matches this instance with given obj """
        raise NotImplementedError

class Num(int, Argument):
    """ Just remember initially specified value format """
    def __new__(cls, val=None, bits='any', positive=False):
        if type(val) is str:
            ret = int.__new__(cls, val, 0) # auto determine base
        elif val is None:
            ret = int.__new__(cls, 0)
            ret.bits = bits
            if bits != 'any':
                ret.maximum = 1 << bits
            ret.positive = positive
            return ret
        else:
            ret = int.__new__(cls, val)
        ret.initial = str(val)
        # and for consistency with Reg:
        ret.val = ret
        ret.bits = None
        return ret
    def __repr__(self):
        if self.bits != None:
            if self.bits != 'any': # numeric
                return "%d-bits integer%s" % (self.bits,
                    ", positive" if self.positive else "")
            return "Integer%s" % (", positive" if self.positive else "")
        return str(self.initial)
    def match(self, other):
        if type(other) is not Num:
            return False
        if self.bits != None:
            if self.positive and other < 0:
                return False
            if self.bits != 'any' and abs(other) >= self.maximum:
                return False
            return True
        return other == self

class List(list, Argument):
    def match(self, other):
        if type(other) not in (List, list): # it may be either our specific List obj or plain list
            return False
        if len(self) != len(other):
            return False
        for i,j in zip(self, other):
            if type(i) is not tuple:
                i = (i,) # to be iterable
            for ii in i:
                if ii.match(j):
                    break
            else: # none matched
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
        return Reg._regs[name.upper()]
    @staticmethod
    def is_reg(name):
        """ Checks whether string is valid register name """
        return name.upper() in Reg._regs
    def __new__(cls, name=None, hi='any'):
        """
        Usage: either Reg('name') or Reg(hi=True/False) or Reg()
        First is a plain register, others are masks
        """
        if not name or name in ['HI','LO']: # pure mask
            if name == 'HI':
                hi = True
            elif name == 'LO':
                hi = False
            mask = hi
            name = "%s register" % (
                "High" if hi else
                "Low" if hi == False else
                "Any")
            val = -1
        else:
            val = Reg.lookup(name)
            mask = None
        ret = int.__new__(cls, val)
        ret.name = name
        ret.mask = mask
        return ret
    def __repr__(self):
        return self.name
    def match(self, other):
        if not type(other) is Reg:
            return False
        if self.mask != None:
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
    def __repr__(self):
        return (":%s"%self.name) if self.name else "Label"
    def match(self, other):
        return type(other) is Label
    def getAddress(self, instr):
        if not self.name:
            raise LabelError("This is a mask, not label!")
        try:
            return instr.findLabel(self)
        except IndexError:
            raise LabelError
    def offset(self, instr, bits=None):
        ofs = self.getAddress(instr) - (instr.getAddr()+4)
        if bits and abs(ofs) >= (1<<bits):
            raise LabelError("Offset is too far: %X" % ofs)
        if ofs < 0:
            if not bits:
                print "Warning: negative offset and no bitlength provided!"
                bits = ofs.bit_length()
            ofs = (1<<bits) + ofs
        print hex(ofs),bits
        return ofs
class Str(str, Argument):
    """ This represents _quoted_ string """
    def __new__(cls, val=None):
        if val == None:
            val = "String"
            mask = True
        else:
            mask = False
        ret = str.__new__(cls, val)
        ret.mask = mask
        return ret
    def match(self, other):
        if type(other) is not Str:
            return False
        if self.mask:
            return True
        return self == other

###
# Instructions description
class Instruction(object):
    """
    This class may represent either instruction definition (with masks instead of args)
    or real instruction (with concrete args and context).
    Instruction handler may access its current opcode via self.opcode field.
    """
    def __init__(self, opcode, args, proc, mask=True, pos=None):
        self.opcode = opcode
        self.args = args
        self.proc = proc
        self.mask = mask
        self.pos = pos
        self.size = None
        self.addr = None
        self.original = None
    def __repr__(self):
        ret = "<%s %s>" % (self.opcode, ','.join([repr(x) for x in self.args]))
        if self.original:
            ret += "(mask:%s)" % self.original
        return ret
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
        # __func__ to avoid type checking, as match() will excellently work
        # on plain list.
        if not List.match.__func__(self.args, args):
            return False
        return True
    def instantiate(self, opcode, args, pos):
        if not self.mask:
            raise ValueError("This is not mask, cannot instantiate")
        # this magic is to correctly call constructor of subclass
        ret = self.__class__(opcode, args, self.proc, mask=False, pos=pos)
        if self.size != None:
            ret.size = self.size
        else:
            # this magic is to correctly "replant" custom method to another
            # instance
            import types
            ret.getSize = types.MethodType(self.getSize.__func__, ret)
        ret.original = self
        return ret
    def setAddr(self, addr):
        """
        Sets memory address at which this particular instruction instance resides.
        This is called somewhere after instantiate.
        """
        self.addr = addr
    def getAddr(self):
        " Returns memory address for this instruction "
        return self.addr
    def setBlock(self, block):
        self.block = block
    def findLabel(self, label):
        if label.name in self.block.getContext():
            return self.block.getContext()[label.name]
        # TODO: global context
        raise LabelError("Label not found: %s" % repr(label))
    def getCode(self):
        if not self.addr:
            raise ValueError("No address, cannot calculate code")
        if callable(self.proc):
            code = self.proc(self, *self.args)
        else:
            code = self.proc
        if type(code) is str:
            return code
        elif type(code) is int:
            return pack('<H', code)
        elif type(code) is tuple:
            return pack('<HH', code[0], code[1])
        else:
            raise ValueError("Bad code: %s" % repr(code))
    def getSize(self):
        """ default implementation; may be overriden by decorator """
        return self.size
    def getPos(self):
        " pos is instruction's position in patch file "
        return self.pos

class LabelInstruction(Instruction):
    """
    This class represents an abstract label instruction. It has zero size.
    It should be instantiated directly.
    """
    def __init__(self, name, pos, glob=False):
        Instruction.__init__(self, None, [name], None, False, pos)
        self.name = name
        self.glob = glob
    def __repr__(self):
        return "<label:%s>" % self.name
    def setBlock(self, block):
        self.block = block
        if self.glob:
            # TODO
            raise ValueError("Not implemented yet")
        else:
            block.getContext()[self.name] = self.getAddr()
    def getSize(self):
        return 0
    def getCode(self):
        return ''
_instructions = []
def instruction(opcode, args, size=2, proc=None):
    """
    This is a function decorator for instruction definitions.
    It may also be used as a plain function, then you should pass it a function as proc arg.
    Note that proc may also be in fact plain value, e.g. for "NOP" instruction.
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

def findInstruction(opcode, args, pos):
    """
    This method tries to find matching instruction
    for given opcode and args.
    On success, it will instantiate that instruction with given pos (cloning that pos).
    On failure, it will throw IndexError.
    """
    for i in _instructions:
        if i.match(opcode, args):
            return i.instantiate(opcode, args, pos.clone())
    raise IndexError("Unsupported instruction: %s" % opcode)

###
# All the instruction definitions
instruction('ADD', [Reg("LO"), Num()], 2, lambda self,rd,imm:
            (1 << 13) + (2 << 11) + (rd << 8) + imm)
def _longJump(self, dest, bl):
    offset = dest.offset(self, 22)
    offset = offset >> 1
    hi_o = (offset >> 11) & (2**10-1)
    lo_o = (offset >> 0)  & (2**11-1)
    hi_c = 0b11110
    lo_c = 0b11111 if bl else 0b10111
    hi = (hi_c << 11) + hi_o
    lo = (lo_c << 11) + lo_o
    return (hi,lo)
instruction('BL', [Label()], 4, lambda self,dest: _longJump(self,dest,True))
instruction('B.W', [Label()], 4, lambda self,dest: _longJump(self,dest,False))
@instruct_class
class DCB(Instruction):
    def __init__(self, opcode=None, args=None, pos=None):
        Instruction.__init__(self, opcode, args, None, pos=pos)
        if args:
            code = ''
            for a in args:
                if type(a) is Str:
                    code += a
                elif type(a) is Num:
                    code += pack('<B', a)
                else:
                    raise ValueError("Bad argument: %s" % repr(a))
            self.code = code
            self.size = len(code)
    def match(self, opcode, args):
        return opcode in ['DCB', 'db']
    def instantiate(self, opcode, args, pos):
        return DCB(opcode, args, pos)
    def getCode(self):
        return self.code
    def getSize(self):
        return len(self.code)
@instruct_class
class ALIGN(Instruction):
    # FIXME handle size properly
    def __init__(self, opcode='ALIGN', args=[(Num(4),Num(2))], proc=None, mask=True, pos=None):
        Instruction.__init__(self, opcode, args, proc, mask, pos)
        if pos: # not mask
            self.size = args[0]
    def getCode(self):
        return '\x00\xBF'*(self.size/2)
    def getSize(self):
        return self.size
instruction('DCH', [Num(bits=16)], 2, lambda self,num: pack('<H', num))
instruction('DCD', [Num(bits=32)], 4, lambda self,num: pack('<I', num))
instruction('NOP', [], 2, 0xBF00)
for cond, val in {
    'CC': 0x3, 'CS': 0x2, 'EQ': 0x0, 'GE': 0xA,
    'GT': 0xC, 'HI': 0x8, 'LE': 0xD, 'LS': 0x9,
    'LT': 0xB, 'MI': 0x4, 'NE': 0x1, 'PL': 0x5,
    'VC': 0x7, 'VS': 0x6,
}.items():
    instruction('B'+cond, [Label()], 2, lambda self,lbl:
                (0b1101 << 12) + (val << 8) + (lbl.offset(self,9)>>1))
    instruction('B'+cond+'.W', [Label()], 4, lambda self,lbl:
                ((0b11110 << 11) + (val << 6) + (lbl.offset(self,18) >> 12),
                 (0b10000 << 11) + ((lbl.offset(self,18) & (2**11-1)) >> 1)))
@instruction(['CBZ','CBNZ'], [Reg('LO'), Label()])
def CBx(self, reg, lbl):
    offset = lbl.offset(self, 7)
    op = 1 if 'N' in self.opcode else 0
    return ((0b1011 << 12) +
            (op << 11) +
            ((offset >> 5) << 9) +
            (1 << 8) +
            ((offset & 0b11111) << 3) +
            reg)
instruction('B', [Label()], 2, lambda self,lbl:
            (0b11100 << 11) + (lbl.offset(self, 12)>>1))
