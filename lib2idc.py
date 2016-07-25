#!/usr/bin/env python3

import sys
from struct import unpack

if len(sys.argv) < 3:
    print("Usage:")
    print("lib2idc.py libpebble.a (pbl_table-offset-in-fw)")
    sys.exit(1)

szLibfile, pbl_table = sys.argv[1:]

f = open(szLibfile, "rb")

# validate file type
header = f.read(8)
if header != b'!<arch>\n':
    print("This doesn\'t look like a proper .a file")
    sys.exit(1)

# find names start - in pbl libraries it starts with accel_,
# unless they make a breaking change again (like 2 to 3)
f.seek(0x48)  # skip header stuff
while True:
    val = f.read(4)
    if not val:
        print("Could not find names section, but reached EOF")
        sys.exit(1)
    if val != b'\x00\x00F\x98' and b'a' in val:
        right_apos = len(val) - val.index(b'a')
        f.seek(f.tell() - right_apos)
        break

bNames = f.read()
names = []
first = ""
alphabet = b'_' + bytes(range(ord('a'), ord('z')+1))
for s in bNames.split(b'\0'):
    if s == first or len(s) == 0 or not (s[0] in alphabet):
        # if repeating or empty or doesn't look like function name
        break
    s = s.decode()
    names.append(s)
    if first == "":
        first = s

# now let's find funcs
f.seek(0)
while True:
    val = f.read(4)
    if not val:
        print("Could not find funcs section, but reached EOF")
        sys.exit(1)
    if val == b'\xA8\xA8\xA8\xA8':
        # found
        break

funcs = []
addrs = []
for i in range(len(names)):
    proc = f.read(12)
    if len(proc) < 12:  # end of file reached
        break
    addr = unpack("<LLL", proc)[2]
    funcs.append((addr, names[i]))
    addrs.append(addr)

print("#include <idc.idc>")
print()
print("static main(void) {")
print("\tauto pbl_table = %s;" % pbl_table)
for f in funcs:
    print('\tMakeUnkn(Dword(pbl_table+0x%08X)-1, DOUNK_DELNAMES);' % f[0])
    print('\tMakeName(Dword(pbl_table+0x%08X)-1, "%s");' % f)
    print('\tMakeFunction(Dword(pbl_table+0x%08X)-1, BADADDR);' % f[0])
print("\t// Now mark these offsets (including blanks)")
for i in range(0, addrs[-1]+4, 4):
    print("\tOpOff(pbl_table+0x%08X, 0, 0);" % i)
print("}")
