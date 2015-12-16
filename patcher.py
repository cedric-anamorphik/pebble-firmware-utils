#!/usr/bin/env python2

from libpatcher import *

def parse_args():
    import argparse
    parser = argparse.ArgumentParser(
        description="Pebble firmware patcher")
    parser.add_argument("patch", nargs='+', type=argparse.FileType("r"),
                        help="File with a patch to apply")
    parser.add_argument("-o", "--output", required=True, type=argparse.FileType("wb"),
                        help="Output file name")
    parser.add_argument("-t", "--tintin", nargs='?', default="tintin_fw.bin", type=argparse.FileType("rb"),
                        help="Input tintin_fw file, defaults to tintin_fw.bin")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Print debug information while patching")
    parser.add_argument("-D", "--define", action="append", default=[],
                        help="Add some #define'd constant. Usage: either -D constant or -D name=val")
    parser.add_argument("-i", "--ignore-length", action="store_true",
                        help="Don't check for mask length when overwriting block (dangerous!")
    parser.add_argument("-a", "--append", action="store_true",
                        help="Use space in the end of firmware to store floating blocks")
    parser.add_argument("-A", "--always-append", action="store_true",
                        help="Same as --append, but doesn't check for maximum file size. "
                        "Useful for PebbleTime firmware which seems to have other size limits")
    parser.add_argument("-c", "--codebase", type=lambda x: int(x, base=0),
                        default=0x8004000,
                        help="Codebase of the binary. "
                        "Defaults to 0x8004000 (which is for 3.x fw); "
                        "for 1.x-2.x set it to 0x8010000")
    return parser.parse_args()

def patch_fw(args):
    data = args.tintin.read()

    # this is a library patch,
    # which will hold all #included blocks
    library = Patch("#library", binary=data)

    # this holds list of ranges
    ranges = Ranges()

    if args.append or args.always_append:
        ranges.add_eof(data, 0x70000 if args.append else 0x1000000,
                       0x48)

    # this is for #defined and pre#defined values
    definitions = {}
    for d in args.define:
        if '=' in d:
            name,val = d.split('=', 1)
            definitions[name] = val
        else:
            definitions[d] = True

    # Read all requested patch files
    patches = [library]
    print("Loading files:")
    for f in args.patch:
        print(f.name)
        patches.append(parseFile(f, definitions, libpatch=library))
    # Bind them all to real binary (i.e. scan masks)...
    print("Binding patches:")
    for p in patches: # including library
        print(p)
        p.bindall(data, ranges, args.codebase)
    # ...and apply
    print("Applying patches:")
    for p in patches:
        print(p)
        data = p.apply(data, args.codebase, ignore=args.ignore_length)
    print("Saving...")
    # restore eof bytes, if file-end range was used
    data = ranges.restore_tail(data)
    args.output.write(data)
    args.output.close()
    print("Done.")

if __name__ == "__main__":
    args = parse_args()
    patch_fw(args)
