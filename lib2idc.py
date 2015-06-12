#!/usr/bin/env python2

import sys
from struct import unpack

if len(sys.argv) < 5:
    print "Usage:"
    print "lib2idc.py libpebble.a (names-offset) (funcs-offset) (pbl_table-offset)"
    print "for sdk 2.0b3 offsets are: 0x9D8, 0x40AE"
    sys.exit(1)

szLibfile, szNames, szFuncs, pbl_table = sys.argv[1:]
ofsNames = int(szNames, 16)
ofsFuncs = int(szFuncs, 16)

f = open(szLibfile, "rb")
f.seek(ofsNames)
bNames = f.read()
names = []
first = ""
for s in bNames.split('\0'):
    if s == first or len(s) == 0 or not (s[0].isalpha() or s[0] in '_'):
        # if repeating or empty or doesn't look like function name
        break
    names.append(s)
    if first == "":
        first = s

f.seek(ofsFuncs)
funcs = []
addrs = []
for i in range(len(names)):
    proc = f.read(12)
    if len(proc) < 12: # end of file reached
        break
    addr = unpack("<LLL", proc)[2]
    funcs.append((addr, names[i]))
    addrs.append(addr)

print "#include <idc.idc>"
print
print "static main(void) {"
print "\tauto pbl_table = %s;" % pbl_table
for f in funcs:
    print '\tMakeUnkn(Dword(pbl_table+0x%08X)-1, DOUNK_DELNAMES);' % f[0]
    print '\tMakeName(Dword(pbl_table+0x%08X)-1, "%s");' % f
    print '\tMakeFunction(Dword(pbl_table+0x%08X)-1, BADADDR);' % f[0]
print "\t// Now mark these offsets (somewhat buggy approach though)"
for i in range(0, len(funcs)*4, 4):
    print "\tOpOff(pbl_table+0x%08X, 0, 0);" % i
print "}"
