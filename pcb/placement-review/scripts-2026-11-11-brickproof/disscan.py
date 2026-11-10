import sys,struct
sys.path.insert(0,'/tmp/brick/tools')
from capstone import *
from capstone.arm import *
exec(open('/tmp/brick/tools/hexinfo.py').read().split("mem=load")[0])
mem=load(sys.argv[1])
lo,hi=int(sys.argv[2],16),int(sys.argv[3],16)
code=bytes(mem.get(a,0xff) for a in range(lo,hi))
md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS);md.detail=True;md.skipdata=True
def w(a): return struct.unpack('<I',bytes(mem.get(a+i,0xff) for i in range(4)))[0]
reg={}
names={0x10001200:'UICR.PSELRESET0',0x10001204:'UICR.PSELRESET1',0x10001208:'UICR.APPROTECT',0x1000120C:'UICR.NFCPINS',0x10001304:'UICR.REGOUT0',0x10001014:'UICR.BOOTADDR',0x10001018:'UICR.MBRPARAM',0x40000558:'APPROTECT.DISABLE',0x40000550:'APPROTECT.FORCEPROTECT',0x40000578:'POWER.DCDCEN',0x40000580:'POWER.DCDCEN0',0x4000051C:'POWER.GPREGRET',0x40000400:'POWER.RESETREAS',0x4001E504:'NVMC.CONFIG',0x4001E50C:'NVMC.ERASEALL',0x4001E514:'NVMC.ERASEUICR',0x4001E508:'NVMC.ERASEPAGE',0x40000518:'CLOCK.LFCLKSRC',0x40000500:'POWER.SYSTEMOFF',0x40010504:'WDT?'}
hits=[]
for i in md.disasm(code,lo):
    m=i.mnemonic;ops=i.operands if i.id else []
    try:
        if m.startswith(('ldr')) and len(ops)==2 and ops[1].type==ARM_OP_MEM and ops[1].mem.base==ARM_REG_PC:
            la=((i.address+4)&~3)+ops[1].mem.disp; reg[ops[0].reg]=w(la); continue
        if m.startswith(('movw','mov.w','movs','mov')) and len(ops)==2 and ops[1].type==ARM_OP_IMM:
            reg[ops[0].reg]=ops[1].imm&0xffffffff; continue
        if m.startswith('movt') and ops[0].reg in reg:
            reg[ops[0].reg]=(reg[ops[0].reg]&0xffff)|((ops[1].imm&0xffff)<<16); continue
        if m.startswith(('add','sub')) and ops[-1].type==ARM_OP_IMM:
            src=ops[-2].reg if len(ops)==3 else ops[0].reg
            if src in reg:
                v=reg[src]+(ops[-1].imm if m.startswith('add') else -ops[-1].imm); reg[ops[0].reg]=v&0xffffffff
            else: reg.pop(ops[0].reg,None)
            continue
        if m.startswith(('str','ldr')) and len(ops)>=2 and ops[1].type==ARM_OP_MEM and ops[1].mem.base in reg and ops[1].mem.index==0:
            a=(reg[ops[1].mem.base]+ops[1].mem.disp)&0xffffffff
            if 0x10001000<=a<0x10002000 or 0x40000400<=a<0x40000600 or 0x4001E500<=a<0x4001E520:
                hits.append((i.address,m,a,names.get(a,'')))
            if m.startswith('ldr'): reg.pop(ops[0].reg,None)
            continue
        if m.startswith(('b','cb','pop','bl','bx')): 
            if m in('bl','blx'): [reg.pop(r,None) for r in (ARM_REG_R0,ARM_REG_R1,ARM_REG_R2,ARM_REG_R3,ARM_REG_R12)]
            elif m.startswith(('bx','pop','b.w')) or m=='b': reg.clear()
            continue
        # any other write to a reg invalidates
        if ops and ops[0].type==ARM_OP_REG: reg.pop(ops[0].reg,None)
    except Exception as e: pass
from collections import Counter
for h in hits: print(f"0x{h[0]:06X} {h[1]:6s} 0x{h[2]:08X} {h[3]}")
