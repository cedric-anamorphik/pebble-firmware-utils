from libpatcher.asm import *
from libpatcher.parser import *
from libpatcher.parser import parseBlock, parseInstruction
from libpatcher.block import *
from libpatcher.patch import Patch
from nose.tools import *

mock_patch = Patch('test_patch', binary="test_bin")
def op_gen(instr, addr=0, context={}):
    pos = FilePos('test_asm.pbp',0)
    if isinstance(instr, str):
        i = parseInstruction(instr, pos)
    else:
        i = findInstruction(instr[0], instr[1], pos)
    assert i
    if addr < 0x8010000:
        addr += 0x8010000
    block = Block(mock_patch, None, [i])
    block.bind(addr)
    context['self'] = addr # add fake "self" label for our instruction
    context['next'] = addr+4
    block.context.update(context) # append our "fake" labels
    return i
def op(instr, addr=0, context={}):
    return op_gen(instr, addr, context).getCode()

def eq_(a,b):
    def unhex(s):
        return ' '.join(["%02X"%ord(c) for c in s])
    if isinstance(a, str):
        a = unhex(a)
    if isinstance(b, str):
        b = unhex(b)
    assert a==b, "%s != %s" % (a,b)
def test_BL_self():
    eq_(op('BL self'), '\xFF\xF7\xFE\xFF')
def test_BW_self():
    eq_(op('B.W self'), '\xFF\xF7\xFE\xBF')
def test_BW_next():
    eq_(op('B.W next'), '\x00\xF0\x00\xB8')
def test_DCW_0x1234():
    assert op('DCW 0x1234') == '\x34\x12'
@raises(ParseError)
def test_DCW_too_large():
    op('DCW 0x12345')
def test_DCD_0xDEADBEEF():
    assert op('DCD 0xDEADBEEF') == '\xEF\xBE\xAD\xDE'
def test_NOP():
    assert op('NOP') == '\x00\xBF'
def test_BCC_self():
    eq_(op('BCC self'), '\xFE\xD3')
def test_BEQ_self():
    eq_(op('BEQ self'), '\xFE\xD0')
def test_BNE_W_self():
    eq_(op('BNE.W self'), '\x7F\xF4\xFE\xAF')
def test_CBZ_R3_next():
    eq_(op('CBZ R3, next'), '\x03\xB1')
def test_CBNZ_R7_next():
    eq_(op('CBNZ R7, next'), '\x07\xB9')
def test_B_self():
    eq_(op('B self'), '\xFE\xE7')
def test_global_label():
    instr = op_gen('global globlabel')
def test_val():
    eq_(op('val name'), '')
    eq_(mock_patch.context['name'], 0x74736574) # integer representation of 'test'
def test_DCD_name():
    eq_(op('DCD name'), 'test')
def test_DCD_name_p_1():
    eq_(op('DCD name+1'), 'uest')
def test_ADD_R1_1():
    assert op(('ADD', [Reg('R1'), Num(1)])) == '\x01\x31'
#def test_ADD_R3_R0_R2():
#    eq_(op('ADD R3,R0,R2'), '\x83\x18')
def test_ADD_R7_SP_12():
    eq_(op('ADD R7,SP,12'), '\x03\xAF')
def test_ADR_R2_next():
    eq_(op('ADR R2,next'), '\x00\xA2')
def test_BLX_R8():
    eq_(op('BLX R8'), '\xC0\x47')
def test_BX_LR():
    eq_(op('BX LR'), '\x70\x47')
def test_CMP_R3_0xF():
    eq_(op('CMP R3,0xF'), '\x0F\x2B')
def test_CMP_R2_R12():
    eq_(op('CMP R2,R12'), '\x62\x45')
def test_CMP_R0_R1():
    eq_(op('CMP R0,R1'), '\x88\x42')
def test_MOV_R0_2C():
    eq_(op('MOV R0,0x2C'), '\x2c\x20')
def test_MOV_R0_3x4():
    eq_(op('MOV R0,3*4'), '\x0c\x20')
def test_MOV_R0_10m4():
    eq_(op('MOV R0,10-4'), '\x06\x20')
def test_MOV_R0_10p4():
    eq_(op('MOV R0,10+4'), '\x0e\x20')
def test_MOVS_R0_R5():
    eq_(op('MOVS R0,R5'), '\x28\x00')
def test_MOV_R0_R5():
    eq_(op('MOV R0,R5'), '\x28\x46')
def test_MOVW_R1_0xFF000():
    eq_(op('MOV.W R1,0xFF000'),'\x4F\xF4\x7F\x21')
def test_MOV_R2_50000():
    eq_(op('MOV R2,50000'),'\x4C\xF2\x50\x32')
@raises(ParseError)
def test_MOV_R2_m50000_fails():
    eq_(op('MOV R2,-50000'),'\x4F\xF4\x7F\x21')
@raises(ParseError)
def test_MOVW_R1_m1_fails():
    print op('MOVW R1,-1')
def test_LDR_R3_next():
    eq_(op('LDR R3, next'), '\x00\x4B')
def test_LDR_R5_R3():
    eq_(op('LDR R5,[R3]'), '\x1D\x68')
def test_LDR_R12_SP_0x24():
    eq_(op('LDR R12,[SP,0x24]'), '\xDD\xF8\x24\xC0')
def test_LDRB_R3_R3():
    eq_(op('LDRB R3,[R3]'), '\x1B\x78')
def test_MUL_R3_R7():
    eq_(op('MUL R3,R7'), '\x7b\x43')
def test_PUSH_R3_LR():
    eq_(op('PUSH {R3,LR}'), '\x08\xb5')
def test_PUSH_R4_R8_LR():
    eq_(op('PUSH {R4-R8,LR}'), '\x2d\xe9\xf0\x41')
def test_POP_R4_R8_PC():
    eq_(op('POP {R4-R8,PC}'), '\xbd\xe8\xf0\x81')
def test_POP_R3_R7_PC():
    eq_(op('POP {R3-R7,PC}'), '\xF8\xBD')
def test_STR_R3_SP():
    eq_(op('STR R3,[SP]'), '\x00\x93')
def test_STR_R3_SP_4():
    eq_(op('STR R3,[SP,4]'), '\x01\x93')
def test_STR_R5_R2():
    eq_(op('STR R5,[R2]'), '\x15\x60')
def test_STR_R8_SP_0x34():
    eq_(op('STR R8,[SP,0x34]'), '\xCD\xF8\x34\x80')
def test_STRB_R6_R4_6():
    eq_(op('STRB R6,[R4,6]'), '\xA6\x71')
def test_STRB_R3_SP_3():
    eq_(op('STRB R3,[SP,3]'), '\x8D\xF8\x03\x30')
def test_SUB_R2_0x12():
    eq_(op('SUB R2,0x12'), '\x12\x3A')
def test_SUB_R4_R6_R4():
    eq_(op('SUB R4,R6,R4'), '\x34\x1B')
def test_SUB_R2_R0_8(): # with T4 encoding - f2; T3 -> f1
    eq_(op('SUB R2,R0,8'), b'\xa0\xf2\x08\x02')
def test_SUB_R1_R4_1():
    eq_(op('SUB R1,R4,1'), b'\x61\x1E')
def test_UXTB_R5_R4():
    eq_(op('UXTB R5,R4'), '\xE5\xB2')
