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

def parse_args():
    import argparse
    parser = argparse.ArgumentParser(
        description = "This script displays images found in Pebble firmware or resource files")
    parser.add_argument("input", nargs='?', default="tintin_fw.bin", type=argparse.FileType("rb"),
                        help="Input file, defaults to tintin_fw.bin")
    parser.add_argument("-o", "--offset", type=lambda(n): int(n, 0),
                        help="Offset to beginning of image. If omitted, image will be treated as resource-type file")
    parser.add_argument("-i", "--invert", action="store_true",
                        help="Inverse display (white/black)")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    f = args.input
    if args.offset:
        print args.offset
        if args.offset > 0x08010000:
            args.offset -= 0x08010000 # convert from memory address to file offset
        f.read(args.offset)
    s = f.read(4)
    ofs = unpack('I', s)[0]
    if 0x8010000 < ofs and ofs < 0x80fffff: # memory offset
        rowsize = unpack('H', f.read(2))[0]
        f.read(2) # unknown field = 0x1000
    else: # resource file
        ofs = None
        rowsize = unpack('H', s[:2])[0]
    f.read(4) # unknown field
    width, height = unpack('HH', f.read(4))
    if ofs:
        f.seek(ofs-0x8010000)
    data = f.read()
    showImage(data, rowsize, width, height, args.invert) # or: calcHeightBySize(rowsize, len(data))
