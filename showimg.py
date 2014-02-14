#!/usr/bin/env python

import sys
from struct import unpack

def imgSize(rowsize, height):
    return rowsize * height

def showImage(data, rowsize, width, height, inverse=False):
    ptr = 0
    PX = ('#', ' ') if inverse else (' ', '#')
    for row in range(height):
        for byte in range(rowsize):
            p = ord(data[ptr])
            for i in range(8):
                if (byte-1)*8 + i >= width:
                    break
                sys.stdout.write( PX[(p >> i) & 1] )
            ptr+=1
        print "."
    print

def calcHeightBySize(rowsize, datasize):
    return datasize/rowsize

if __name__ == "__main__":
    f = sys.stdin
    if len(sys.argv) >= 1 and sys.argv[0] in ['-h', '--help']:
        print "Usage: cat image | showimg.py [-r] [offset]"
        print "Possible example: dd if=tintin_fw.bin bs=1 count=64 skip=`wcalc 0x48af4 | tr -d '= '` | ../../showimg.py 4 16"
        exit(1)
    rev = len(sys.argv) >= 2 and sys.argv[1] == '-r'
    shift = 0
    if len(sys.argv) >= (3 if rev else 2):
        shift = int(sys.argv[4 if rev else 3])
    if shift:
        f.read(shift)
    rowsize = unpack('H', f.read(2))[0]
    f.read(6) # two unknown fields
    width = unpack('H', f.read(2))[0]
    f.read(2) # height
    data = sys.stdin.read()
    showImage(data, rowsize, width, calcHeightBySize(rowsize, len(data)), rev)
