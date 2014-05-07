from mask import MaskNotFoundError

class RangeError(MaskNotFoundError):
    """
    This is raised when no available range found
    """

class Ranges(object):
    """
    This class represents collection of Ranges to use
    """
    def __init__(self):
        self._ranges = []

    def add(self, f, t):
        """
        Adds a range to the collection
        """
        if f > t:
            raise ValueError("Illegal range, from>to: %d,%d" % (f,t))

        if f == t:
            return # empty range - ignore

        for r in list(self._ranges): # copy list to prevent remove() influence iterator
            if r[0] == r[1]: # collapsed range
                self._ranges.remove(r)
                continue
            if r[0] == f and r[1] == t: # duplicate range
                raise AssertionError("Duplicate range %d-%d" % (f,t))
            if ((f <= r[0] and t > r[0]) or
                (f < r[1] and t >= r[1])):
                raise AssertionError("Range clash: %d-%d clashes with %d-%d" %
                                     (f,t, r[0],r[1]))
        for r in self._ranges: # now when we definitely have no clashes
            if r[1] == f: # append
                r[1] = t
                return
            if t == r[0]: # append
                r[0] = f
                return

        # this is completely new range
        self._ranges.append([f,t])

    def find(self, size):
        """
        Returns the best matching range for block of given size,
        and excludes returned range from collection.
        @returns [from, to]
        """
        for r in sorted(self._ranges, key=lambda r: r[1]-r[0]): # sort by size, ascending
            if r[1]-r[0] >= size:
                ret = [r[0],r[1]] # copy range
                r[0] += size # and reduce it
                return ret
        raise RangeError("No suitable range for %d bytes" % size)
