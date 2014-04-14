from libpatcher.asm import *
from libpatcher.parser import *
from libpatcher.parser import parseBlock, parseInstruction
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
    i.setAddr(addr)
    block = [i]
    #FIXME: block.context = context
    i.setBlock(block)
    return i.getCode()

def test_ADD_R1_1():
    assert op(('ADD', [Reg('R1'), Num(1)])) == '\x01\x31'
@nottest
def test_ADD_R3_R0_R2():
    assert op('ADD R3,R0,R2') == '\x83\x18'
@nottest
def test_MOV_R0_2C():
    assert op('MOV R0,0x2C') == '\x2c\x20'
@nottest
def test_BL_self():
    code = "label: BL label"
    assert False, "Not implemented yet"
def test_DCH_0x1234():
    assert op('DCH 0x1234') == '\x34\x12'
@raises(ParseError)
def test_DCH_too_large():
    op('DCH 0x12345')
