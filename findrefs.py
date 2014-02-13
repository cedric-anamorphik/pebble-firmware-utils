#!/usr/bin/env python2
#
# Finds all references to given address
# Either plain or procedure calls

import sys
from struct import pack

def genCode(pos, to, is_bl):
    """
    Returns assembler code for B.W or BL instruction
    placed at [pos], which refers to [to].
    """
    offset = to - (pos+4)
    offset = offset >> 1
    if abs(offset) >= 1<<22:
        print ("Offset %X exceeds maximum of %X!" %
                            (offset, 1<<22))
        return '' # we don't need exception here,
                  # just return empty string which will not match anything
        raise ValueError("Offset %X exceeds maximum of %X!" %
                            (offset, 1<<22))
    hi_o = (offset >> 11) & 0b11111111111
    lo_o = (offset >> 0)  & 0b11111111111
    hi_c = 0b11110
    lo_c = 0b11111 if is_bl else 0b10111
    hi = (hi_c << 11) + hi_o
    lo = (lo_c << 11) + lo_o
    code = pack('<HH', hi, lo)
    return code

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usage: findrefs.py [tintin_fw.bin] 0xVALUE"
        print "Examples:"
        print "  findrefs.py 0x080412f9"
        print "  findrefs.py tintin_fw.patched.bin 0x0801FEDC"
        exit(1)

    if len(sys.argv) == 2:
        tintin = "tintin_fw.bin"
        val = sys.argv[1]
    else:
        tintin = sys.argv[1]
        val = sys.argv[2]

    val = int(val, 0)
    sval = pack('I', val)
    data = open(tintin, "rb").read()

    for i in range(0, len(data)-3, 4):
        d = data[i:i+4]
        iadr = i + 0x08010000
        if d == sval:
            print "Offset 0x%X (0x%X): DCD 0x%X" % (i, iadr, val)
        if d == genCode(iadr, val, False):
            print "Offset 0x%X (0x%X): B.W 0x%X" % (i, iadr, val)
        if d == genCode(iadr, val, True):
            print "Offset 0x%X (0x%X): BL 0x%X" % (i, iadr, val)
    print "Done."
