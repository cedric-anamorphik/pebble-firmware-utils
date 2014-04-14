# This module holds Patch class
class Patch(object):
    """
    This class represents one patch file,
    with all its blocks and its global context.
    It may also represent aggregation of #included ("library") patchfiles.
    """
    def __init__(self, name, library=None, blocks=[]):
        self.name = name
        self.blocks = blocks
        self._library = library
        self._is_bound = False
        self._context = {}
    def __repr__(self):
        return "<patch:%s, %s blocks>" % (self.name, len(self.blocks))
    @property
    def library(self):
        """
        This links to a library patch, which holds
        all "included" patches' data.
        It may link to itself.
        """
        return self._library
    @property
    def context(self):
        """
        This is a patch-level global context.
        """
        return self._context
    def bindall(self, binary, codebase = 0x8010000):
        """
        Tries to bind all blocks of this patch
        to addresses in given binary.
        May raise MaskNotFoundError.
        """
        if self._is_bound:
            raise ValueError("Already bound")
        for block in self.blocks:
            block.bind(block.getPosition(binary) + codebase)
    def apply(self, binary, codebase = 0x8010000):
        """
        Applies all blocks from this patch to given binary,
        and returns resulting patched binary.
        Will bind itself firstly if neccessary.
        """
        if not self._is_bound:
            self.bindall(binary, codebase)
        oldlen = len(binary)
        for block in self.blocks:
            bpos = block.getPosition(binary)
            code = block.getCode()
            binary = binary[0:bpos] + code + binary[bpos+len(code):]
        if len(binary) != oldlen:
            raise AssertionError("Internal check failed: length mismatch, %d != %d" % (len(binary),oldlen))
        return binary
