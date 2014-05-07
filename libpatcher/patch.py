# This module holds Patch class
class PatchingError(Exception):
    def __init__(self, message = None, cause = None):
        self.cause = cause
        if cause:
            message += ": " + repr(cause)
        super(PatchingError, self).__init__(message)

class Patch(object):
    """
    This class represents one patch file,
    with all its blocks and its global context.
    It may also represent aggregation of #included ("library") patchfiles.
    """
    def __init__(self, name, library=None, binary=None):
        """
        library: if not provided, will link to self
        binary: reference to original binary data;
            must be provided if there is no library
        """
        self.name = name
        if not binary and not library:
            raise ValueError("Neither binary nor library provided")
        self.binary = binary or library.binary
        self._blocks = []
        self._library = library or self
        self._is_bound = False
        self._context = {}
    def __repr__(self):
        return "<patch:%s, %s blocks>" % (self.name, len(self.blocks))
    @property
    def blocks(self):
        """
        Collection of blocks for this patch
        """
        return self._blocks
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
    def bindall(self, binary, ranges, codebase = 0x8010000):
        """
        Tries to bind all blocks of this patch
        to addresses in given binary.
        May raise MaskNotFoundError.
        """
        if self._is_bound:
            raise ValueError("Already bound")
        for block in self.blocks:
            block.bind(block.getPosition(binary, ranges) + codebase)
    def apply(self, binary, codebase = 0x8010000, ignore=False):
        """
        Applies all blocks from this patch to given binary,
        and returns resulting patched binary.
        Will bind itself firstly if neccessary.
        """
        if not self._is_bound:
            self.bindall(binary, codebase)
        for block in self.blocks:
            bpos = block.getPosition()
            code = block.getCode()
            if len(code) > block.mask.size and not ignore:
                raise PatchingError("Code length %d exceeds mask length %d! Mask at %s" %
                                    (len(code), block.mask.size, block.mask.pos))
            binary = binary[0:bpos] + code + binary[bpos+len(code):]
        return binary
