class AmbiguousMaskError(Exception):
    "Thrown if mask was found more than 1 time"

class Mask(object):
    "This class represents mask"
    def __init__(self, parts, offset=0):
        """
        parts: list of alternating strings and integers.
            strings mean parts which will be matched,
            integers means "skip N bytes".
        offset: how many bytes from matched beginning to skip
        """
        self.parts = parts
        self.offset = offset
        # TODO: validate
    def __repr__(self):
        return ','.join([repr(x) for x in self.parts])+" @"+str(self.offset)
    def match(self, data):
        """
        Tries to match this mask to given data.
        Returns matched position on success,
        False if not found
        or (exception?) if found more than one occurance.
        """
        # if mask starts with skip, append it to offset
        if type(self.parts[0]) is int:
            self.offset += self.parts[0]
            del self.parts[0]
        pos = data.find(self.parts[0])
        found = False
        while pos != -1:
            pos2 = pos
            for p in parts[1:]:
                if type(p) is int:
                    pos2 += p
                else:
                    if p == data[pos2:pos2+len(p)]:
                        pos2 += len(p)
                    else:
                        break
            else: # not breaked -> matched
                if found: # was already found? -> duplicate match
                    raise AmbiguousMaskError(self)
                found = True
        # all occurances checked
        if found:
            return pos
        return False
