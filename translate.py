#!/usr/bin/env python
# This script updates strings in tintin_fw.bin file

import sys
from struct import pack, unpack

# data is a loaded tintin_fw file contents
data = ""
# datar is data to return
datar = ""

# strings is dictionary of strings to replace
#strings = {}

def is_valid_pointer(n):
    """ Checks if a number looks like a valid pointer """
    return n >= 0x08010000 and n < (0x08010000+len(data))

def is_string_pointer(ptr):
    """
    Checks if a number points to somthing similar to string;
    returns string (maybe empty) if it is a valid string or False otherwise
    """
    def is_string_char(c):
        return c in "\t\r\n" or (c >= ' ' and c <= '~') # tab, endline or printable latin

    if not is_valid_pointer(ptr):
        return False

    for i in range(ptr-0x08010000, len(data)):
        if data[i] == '\0':
            #return i - (ptr-0x08010000) # line ended without non-string chars, return strlen
            return data[ptr-0x08010000:i] # line ended without non-string chars, return it
        if not is_string_char(data[i]):
            return False # encountered non-string char, return False
    return False # reched end of file, return False

def find_all_strings():
    """
    Scans input file for all referenced strings.
    Returns array of tuples: (offset, value, string)
    """
    pointers = [] # tuples: offset to pointer, offset to its string, the string itself
    for i in range(0, len(data)-3, 4): # each 4-aligned int; -3 to avoid last (partial) value
        n = unpack("I", data[i:i+4])[0]
        s = is_string_pointer(n)
        if s:
            #print i,n,s
            pointers.append((i, n, s))
    return pointers

def find_pointers_to_offset(offset):
    """
    Finds all pointers to given offset; returns offsets to them
    """
    ret = []
    ptr = offset + 0x08010000
    for i in range(0, len(data)-3, 4):
        n = unpack("I", data[i:i+4])[0]
        if n == ptr:
            ret.append(i)
    return ret

def find_string_offsets(s):
    """ Returns list of offsets to given string """
    ret = []
    s = s + '\0' # string in file must end with \0 !
    i = data.find(s)
    while i != -1:
        ret.append(i)
        i = data.find(s, i+1)
    return ret

def parse_args():
    import argparse
    parser = argparse.ArgumentParser(
        description="Translation helper for Pebble firmware",
        epilog="Strings format:\nOriginal String:=Translated String\n"+
        "Any newlines in strings must be replaced with '\\n', any backslashes with '\\\\'.\n"+
        "Lines starting with # are comments, so if you need # at start replace it with \\#")
    parser.add_argument("tintin", nargs='?', default="tintin_fw.bin", type=argparse.FileType("rb"),
                        help="Input tintin_fw file, defaults to tintin_fw.bin")
    parser.add_argument("output", nargs='?', default=sys.stdout, # bad idea: type=argparse.FileType("wb"),
                        help="Output file, defaults to stdout")
    parser.add_argument("-s", "--strings", default=sys.stdin, type=argparse.FileType("r"),
                        help="File with strings to translate, by default will read from stdin")
    parser.add_argument("-p", "--print-only", action="store_true",
                        help="Don't translate anything, just print out all referenced strings from input file")
    return parser.parse_args()

def read_strings(f):
    strings = {}
    for line in f:
        line = line[:-1] # remove trailing \n
        if len(line) == 0 or line.startswith('#'): # comment or empty
            continue
        line = line.replace('\\n', '\n').replace('\\#', '#').replace('\\\\', '\\') # unescape
        if not ':=' in line:
            print "Warning: bad line in strings:", line
            continue
        left, right = line.split(':=', 1)
        if not right: # empty
            print "Warning: translation is empty; ignoring:", line
            continue
        if ':=' in right:
            print "Warning: unambigous line in strings:", line
            continue
        if left in strings:
            print "Warning: duplicate string, ignoring:", line
            print "Original: "+strings[left]
            continue
        strings[left] = right
    return strings

if __name__ == "__main__":
    args = parse_args()
    if args.output == sys.stdout:
        sys.stdout = sys.stderr # if writing new tintin to sdout, print all messages to stderr to avoid cluttering

    # load source fw:
    data = args.tintin.read()
    datar = data

    if args.print_only:
        print "Scanning tintin_fw..."
        ptrs = find_all_strings()
        print "Found %d referenced strings" % len(ptrs)
        for p in ptrs:
            args.output.write(p[2]+'\n')
        args.output.close()
        sys.exit(0)

    strings = read_strings(args.strings)

    for key in strings:
        val = strings[key]
        print "Processing", key
        os = find_string_offsets(key)
        if not os: # no such string
            print " -- not found, ignoring"
            continue
        if len(val) <= len(key): # can just replace
            print " -- found %d occurance(s), replacing" % len(os)
            for o in os:
                print " -- 0x%X" % o
                oldlen = len(datar)
                datar = datar[0:o] + val + '\0' + datar[o+len(val)+1:]
                if len(datar) != oldlen:
                    raise AssertionError("Length mismatch")
        else: # new string is longer than old, so will add it to end of tintin file
            print " -- found %d occurance(s), looking for pointers" % len(os)
            ps = []
            for o in os:
                newps = find_pointers_to_offset(o)
                ps.extend(newps)
                if not newps:
                    print " !? String at 0x%X is unreferenced, will ignore!" % o
            if not ps:
                print " !! No pointers to that string, cannot translate!"
                continue
            print " == found %d ptrs; appending string and updating them" % len(ps)
            newp = len(datar) + 0x08010000
            newps = pack('I', newp)
            datar = datar + val + '\0'
            for p in ps:
                oldlen = len(datar)
                datar = datar[0:p] + newps + datar[p+4:]
                if len(datar) != oldlen:
                    raise AssertionError("Length mismatch")
    print "Saving..."
    args.output.write(datar)
    args.output.close()
    print "Done."
