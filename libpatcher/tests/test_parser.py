from libpatcher.parser import *
from nose.tools import *
from pprint import pprint

def test_file():
    f = open('tests/test.pbp')
    pprint(parseFile(f))
