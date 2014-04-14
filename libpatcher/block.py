# This module holds Block class
class Block(object):
    def __init__(self, patch, mask, instructions):
        self.patch = patch
        self.mask = mask
        self.instructions = instructions
        self._context = {}
        self.position = None # to cache mask.match() result
    def __repr__(self):
        return "<<<Block at\n%s:\n%s\n>>>" % (repr(self.mask), '\n'.join([repr(x) for x in self.instructions]))
    @property
    def context(self):
        " Block-local context dictionary "
        return self._context
    def getMask(self):
        return self.mask
    def getPosition(self, binary=None):
        """
        Returns position of this block's mask in given binary file.
        Will cache its result.
        """
        if self.position == None \
                or (binary and self._binary != binary):
            # if position was not calculated yet
            # or if bin/codebase provided and not same as were saved
            if binary is None:
                raise ValueError("No saved position and binary not provided")
            self.position = self.mask.match(binary)
            self._binary = binary
        return self.position
    def bind(self, addr):
        """
        This method is called once after construction.
        It binds block to specific memory address (which is determined with mask.match)
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
        return ''.join([i.getCode() for i in self.instructions])
