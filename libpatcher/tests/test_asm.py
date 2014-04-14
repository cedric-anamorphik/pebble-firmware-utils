from libpatcher.asm import *
from libpatcher.parser import *
from libpatcher.parser import parseBlock, parseInstruction
from libpatcher.block import *
from nose.tools import *

def op(instr, addr=0, context={}):
    pos = FilePos('test_asm.pbp',0)
    if type(instr) is str:
        i = parseInstruction(instr, pos)
    else:
        i = findInstruction(instr[0], instr[1], pos)
    assert i
    if addr < 0x8010000:
        addr += 0x8010000
    block = Block(None, [i])
    block.bind(addr)
    context['self'] = addr # add fake "self" label for our instruction
    block.context.update(context) # append our "fake" labels
    return i.getCode()

def test_ADD_R1_1():
    assert op(('ADD', [Reg('R1'), Num(1)])) == '\x01\x31'
#def test_ADD_R3_R0_R2():
#    assert op('ADD R3,R0,R2') == '\x83\x18'
#def test_MOV_R0_2C():
#    assert op('MOV R0,0x2C') == '\x2c\x20'
def test_BL_self():
    eq_(op('BL self'), '\xFF\xF7\xFE\xFF')
def test_BW_self():
    eq_(op('B.W self'), '\xFF\xF7\xFE\xBF')
def test_DCH_0x1234():
    assert op('DCH 0x1234') == '\x34\x12'
@raises(ParseError)
def test_DCH_too_large():
    op('DCH 0x12345')
def test_DCD_0xDEADBEEF():
    assert op('DCD 0xDEADBEEF') == '\xEF\xBE\xAD\xDE'
def test_NOP():
    assert op('NOP') == '\x00\xBF'
def test_BCC_self():
    eq_(op('BCC self'), '\xFE\xD2')
def test_BEQ_self():
    eq_(op('BEQ self'), '\xFE\xCF')
def test_B_self():
    eq_(op('B self'), '\xFE\xE7')
