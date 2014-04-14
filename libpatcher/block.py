# This module holds Block class
class Block(object):
    def __init__(self, mask, instructions):
        self.mask = mask
        self.instructions = instructions
        self.context = {}
    def __repr__(self):
        return "<<<Block at\n%s:\n%s\n>>>" % (repr(self.mask), '\n'.join([repr(x) for x in self.instructions]))
    def getContext(self):
        " Returns block-local context dictionary "
        return self.context
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
        return sum([i.getCode() for i in self.instructions])
