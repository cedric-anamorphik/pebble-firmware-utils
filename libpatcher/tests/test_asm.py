from libpatcher.asm import *
from libpatcher.parser import FilePos, parseInstruction
from nose.tools import *

def op(instr, addr=0):
    pos = FilePos('test_asm.pbp',0)
    if type(instr) is str:
        i = parseInstruction(instr, pos)
    else:
        i = findInstruction(instr[0], instr[1], pos)
    assert i
    if addr < 0x8010000:
        addr += 0x8010000
    i.setAddr(addr)
    return i.getCode()

@istest
def ADD_R1_1():
    assert op(('ADD', [Reg('R1'), Num(1)])) == '\x01\x31'
#@istest
def ADD_R3_R0_R2():
    assert op('ADD R3,R0,R2') == '\x83\x18'
#@istest
def MOV_R0_2C():
    assert op('MOV R0,0x2C') == '\x2c\x20'
