#!/usr/bin/env python2
import sys
from struct import pack,unpack

class Image(object):
    def __init__(self):
        pass
    @staticmethod
    def loadFromRes(f):
        img = Image()
        img.header = f.read(12)
        img.magic, img.empt, img.w, img.h = unpack('IIHH', img.header)
        img.pixels = f.read()
        return img
    def toString(self, name):
        """
        Place this to some .h file with #pragma once

        static const uint8_t IMG_Name[] = {
            0xAA, 0xBB...
        }
        """
        def byte2c(b):
            return "0x%02X," % ord(b)
        ret = "/* Size: %dx%s pixels */\n" % (self.w, self.h)
        ret += "static const uint8_t IMG_%s[] = {\n" % name
        ret += "\t" + ' '.join(map(byte2c, self.header)) + "\n"
        rowlen = len(self.pixels) / self.h
        rowlen = max(rowlen, 8)
        rows = [self.pixels[i:i+rowlen] for i in range(0,len(self.pixels),rowlen)]
        for row in rows:
            ret += "\t" + ' '.join(map(byte2c, row)) + "\n"
        ret += "};\n"
        return ret

def parse_args():
    import argparse
    parser = argparse.ArgumentParser(
        description = "This script converts image from resource format to C structure"
    )
    parser.add_argument('name',
                        help="Image name to be used in code")
    parser.add_argument('input', nargs='?', default=sys.stdin, type=argparse.FileType('rb'),
                        help="Input file, defaults to stdin")
    return parser.parse_args()

def main():
    args = parse_args()
    print Image.loadFromRes(args.input).toString(args.name)

if __name__ == '__main__':
    main()
