from libpatcher.parser import parseFile
from libpatcher.patch import Patch
from pprint import pprint

def test_file():
    try:
        f = open('tests/test.pbp')
    except:
        f = open('libpatcher/tests/test.pbp')
    patch = parseFile(f, libpatch=Patch('library', binary=b'bin'))
    print(patch)
    pprint(patch.blocks)
