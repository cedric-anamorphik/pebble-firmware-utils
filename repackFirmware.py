#!/usr/bin/env python2

import zipfile
import os, os.path
import json
from libpebble.stm32_crc import crc32
from struct import pack, unpack
import tempfile
import shutil

def getCrc(pbpack):
    """read CRC from a pbpack file"""
    pbpack.seek(4)
    return unpack('I', pbpack.read(4))[0]

def updateCrc(tintin, nNew, nOld = 0, byOffset = None, replace_all = False):
    """update CRC sum in tintin binary
       Passing byOffset means nOld will not be used.
    """
    new = pack('I', nNew)
    offsets = []
    if byOffset:
        offsets.append(byOffset)
        print "Checksum must be at 0x%08X." % offset
    else:
        old = pack('I', nOld)
        fw = tintin.read()
        i = fw.find(old)
        if i < 0:
            print "Oops... Couldn't find checksum 0x%08X in tintin_fw.bin! Maybe you specified incorrect data?.."
            exit(1)
        if replace_all:
            while i >= 0:
                offsets.append(i)
                i = fw.find(old, i+1)
        else:
            j = fw.find(old, i+1)
            if not j < 0: # if it was not the only occurance
                print "Oops... There are several occurances of possible checksum 0x%08X, at least at 0x%08X and 0x%08X." % (nOld, i, j)
                print "Bailing out!"
                exit(1)
            offsets.append(i)
            print "Found the only occurance of old checksum 0x%08X at 0x%08X" % (nOld, i)
    for offset in offsets:
        print "Replacing checksum at 0x%08X with the new value 0x%08X..." % (offset, nNew)
        tintin.seek(offset)
        tintin.write(new)
    tintin.flush()
    print "OK."

def parse_args():
    def readable(f):
        open(f, 'rb').close()
        return f
    import argparse
    parser = argparse.ArgumentParser(description="Update checksums and pack firmware package "
                                  "with modified resource pack or tintin_fw binary")
    parser.add_argument("outfile",
            help="Output file, e.g. Pebble-1.10-ev2_4.pbz")
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("-o", "--original", default="system_resources.pbpack", type=argparse.FileType('rb'),
            help="Original resource pack from the original firmware, defaults to system_resources.pbpack",
            metavar="ORIGINAL_RESPACK")
    group.add_argument("-c", "--orig-crc", type=lambda x: int(x,16),
            help="CRC sum from the original resource pack (hexadecimal), e.g. 0xDEADBE05")
    group.add_argument("-s", "--offset", type=lambda x: int(x,16),
            help="Offset from beginning of tintin_fw.bin to checksum value (hexadecimal), e.g. 0xFA57BA70; "+
            "you may acquire it from previous run of this utility.")
    parser.add_argument("-m", "--manifest", default="manifest.json", type=readable,
            help="Manifest file from the original firmware, defaults to manifest.json")
    parser.add_argument("-t", "--tintin-fw", "--tintin", default="tintin_fw.bin", type=readable,
            help="Tintin_fw file from the original firmware, defaults to tintin_fw.bin")
    parser.add_argument("-r", "--respack", default="system_resources.pbpack", type=readable,
            help="Updated resource pack filename, defaults to system_resources.pbpack")
    parser.add_argument("-R", "--no-resources", action="store_true",
            help="Don't store resources in the bundle at all. "
                        "This is experimental, and intended to eliminate unneeded delays "
                        "during patch debugging. "
                        "Requires patched SDK to avoid exceptions during flashing.")
    group = parser.add_argument_group("Optional parameters")
    group.add_argument("-k", "--keep-dir", action="store_true",
            help="Don't remove temporary directory after work")
    group.add_argument("-a", "--replace-all", action="store_true",
            help="If crc found more than 1 time, don't bail out but replace 'em all "
            "(may be required for v3.0 firmware)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    do_crc = not args.original or args.respack != args.original.name

    if do_crc and args.original:
        args.orig_crc = getCrc(args.original)
        args.original.close()

    print "Will create firmware at %s," % args.outfile
    print "using %s for manifest, %s for tintin binary" % (args.manifest, args.tintin_fw)
    print "and %s for resource pack." % args.respack

    if do_crc:
        if args.orig_crc:
            print "Will replace 0x%08X with new CRC." % args.orig_crc
        else:
            print "Will write new CRC at 0x%08X." % args.offset
    print

    try:
        workdir = tempfile.mkdtemp()+'/'

        print " # Copying new resource pack..."
        shutil.copy(args.respack, workdir+'system_resources.pbpack')
        with open(workdir+'system_resources.pbpack', 'rb') as newres:
            newCrc = getCrc(newres)

        print " # Copying tintin_fw.bin..."
        shutil.copy(args.tintin_fw, workdir+'tintin_fw.bin')
        if do_crc:
            print " # Updating CRC value in tintin_fw.bin from 0x%08X to 0x%08X:" % (args.orig_crc or 0, newCrc)
            with open(workdir+'tintin_fw.bin', 'r+b') as tintin:
                updateCrc(tintin, newCrc, args.orig_crc, args.offset, args.replace_all)

        print " # Reading manifest..."
        with open(args.manifest, 'r') as f:
            manifest = json.load(f)

        print " # Updating manifest..."
        if do_crc:
            rp_size = os.path.getsize(args.respack)
            print "   res pack size = %d" % rp_size
            with open(args.respack) as f:
                rp_crc = crc32(f.read())
            print "   res pack crc = %d" % rp_crc
        tintin_size = os.path.getsize(workdir+"tintin_fw.bin")
        print "   tintin size = %d" % tintin_size
        with open(workdir+"tintin_fw.bin") as f:
            tintin_crc = crc32(f.read())
        print "   tintin crc = %d" % tintin_crc

        print " # Changing values:"
        if do_crc:
            print "  resources.size: %d => %d" % (manifest['resources']['size'], rp_size)
            manifest['resources']['size'] = rp_size
            print "  resources.crc: %d => %d" % (manifest['resources']['crc'], rp_crc)
            manifest['resources']['crc'] = rp_crc
        print "  firmware.size: %d => %d" % (manifest['firmware']['size'], tintin_size)
        manifest['firmware']['size'] = tintin_size
        print "  firmware.crc: %d => %d" % (manifest['firmware']['crc'], tintin_crc)
        manifest['firmware']['crc'] = tintin_crc

        print " # Storing manifest..."
        with open(workdir+"manifest.json", "wb") as f:
            json.dump(manifest, f)

        print " # Creating output zip..."
        z = zipfile.ZipFile(args.outfile, "w", zipfile.ZIP_STORED)
        try:
            for f in ("tintin_fw.bin",
                      "system_resources.pbpack",
                      "manifest.json"):
                if f == "system_resources.pbpack" and args.no_resources:
                    print "   SKIPPING resource pack!"
                    continue
                print "   Storing %s..." % f
                z.write(workdir+f, f)
            for f in ("LICENSE.txt",
                      "layouts.json.auto"):
                z.write(f, f) # form current dir - FIXME
        finally:
            z.close()

        print " # Done. Firmware is packed to %s" % args.outfile

    finally:
        if args.keep_dir:
            print "Kept temporary files in %s" % workdir
        else:
            print "Removing temporary files..."
            shutil.rmtree(workdir)

