from libpatcher.mask import Mask, MaskNotFoundError
from nose.tools import eq_, raises

ma = Mask([b'hello', 3, b'world'])
da1 = b'hello!!!world'
da2 = b'hello_world'

def test_maskA_match():
    eq_(ma.match(da1), 0)

@raises(MaskNotFoundError)
def test_maskA_not_match():
    ma.match(da2)
