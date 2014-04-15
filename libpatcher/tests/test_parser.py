from libpatcher.parser import *
from libpatcher.patch import Patch
from nose.tools import *
from pprint import pprint

def test_file():
    f = open('tests/test.pbp')
    patch = parseFile(f, libpatch=Patch('library', binary='bin'))
    print patch
    pprint(patch.blocks)
