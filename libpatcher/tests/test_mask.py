from libpatcher.mask import *
from nose.tools import *

ma = Mask(['hello',3,'world'])
da1 = 'hello!!!world'
da2 = 'hello_world'
def test_maskA_match():
    eq_(ma.match(da1), 0)
@raises(MaskNotFoundError)
def test_maskA_not_match():
    ma.match(da2)
