# This module holds Block class
from asm import LabelInstruction
from patch import PatchingError

class Block(object):
    def __init__(self, patch, mask, instructions):
        self.patch = patch
        self._mask = mask
        self.instructions = instructions
        self._context = {}
        self.position = None # to cache mask.match() result
    def __repr__(self):
        name=""
        if len(self.instructions) > 0:
            instr = self.instructions[0]
            if isinstance(instr, LabelInstruction) and instr.glob:
                name = " "+instr.name
        content = '\n'.join([repr(x) for x in self.instructions])
        if self.mask:
            return "<<<Block%s at\n%s:\n%s\n>>>" % (name, repr(self.mask), content)
        else:
            return "<<<Floating block%s:\n%s\n>>>" % (name, content)
    @property
    def context(self):
        " Block-local context dictionary "
        return self._context
    @property
    def mask(self):
        return self._mask
    def getSize(self):
        " Returns overall size of block's instructions "
        # FIXME: will this work before binding?
        # Replace with maxsize?
        return sum([i.getSize() for i in self.instructions])
    def getPosition(self, binary=None, ranges=None):
        """
        Returns position of this block's mask in given binary file.
        Will cache its result.
        """
        if self.position == None:
            # if position was not calculated yet
            if self.mask.floating:
                if ranges == None:
                    raise ValueError("No ranges provided for floating block")
                r = ranges.find(self.getSize())
                self.position = r[0]
                self.mask.size = r[1]-r[0]
            else:
                if binary is None:
                    raise ValueError("No saved position and binary not provided")
                self.position = self.mask.match(binary)
        return self.position
    def bind(self, addr):
        """
        This method is called once after construction.
        It binds block to specific memory address
        (which is determined with mask.match or is obtained from ranges)
        """
        self.addr = addr
        for i in self.instructions:
            i.setAddr(addr)
            addr += i.getSize()
            i.setBlock(self) # it may in return update our context, so call after setAddr
    def getCode(self):
        """
        Calculstes and returns binary code of this whole block.
        """
        code = b""
        for i in self.instructions:
            try:
                icode = i.getCode()
            except Exception as e:
                raise PatchingError("Block %s, instruction %s" % (self.mask, i), e)
            if len(icode) != i.getSize():
                raise AssertionError("Internal check failed: instruction length mismatch for %s" % repr(i))
            code += icode
        return code
