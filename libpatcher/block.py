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
        if self.addr:
            raise ValueError("Mask was already bound to %s" + self.addr)
        self.addr = addr
        for i in self.instructions:
            i.setAddr(addr)
            addr += i.getSize()
            i.setBlock(self) # it may in return update our context, so call after setAddr
    def apply(self, binary):
        """
        Applies this block to given binary
        and returns resulting binary.
        Can raise MaskNotFound / AmbiguousMask
        """
        pos = self.mask.match(binary)
        self.bind(pos + 0x8010000) # convert pos to mem addr
