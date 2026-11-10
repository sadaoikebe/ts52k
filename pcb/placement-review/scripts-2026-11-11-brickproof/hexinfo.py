import sys,struct
def load(p):
    mem={};base=0
    for l in open(p):
        l=l.strip()
        if not l.startswith(':'):continue
        b=bytes.fromhex(l[1:]);n,a,t=b[0],(b[1]<<8)|b[2],b[3];d=b[4:4+n]
        assert sum(b)&0xff==0
        if t==0:
            for i,x in enumerate(d): mem[base+a+i]=x
        elif t==4: base=((d[0]<<8)|d[1])<<16
        elif t==2: base=((d[0]<<8)|d[1])<<4
    return mem
mem=load(sys.argv[1])
ad=sorted(mem);segs=[];s=ad[0];p=s
for a in ad[1:]:
    if a!=p+1: segs.append((s,p));s=a
    p=a
segs.append((s,p))
for s,e in segs: print(f"segment 0x{s:08X}-0x{e:08X} ({e-s+1} bytes)")
def w(a): return struct.unpack('<I',bytes(mem.get(a+i,0xff) for i in range(4)))[0]
for a in sorted(x for x in mem if x>=0x10000000 and x%4==0): print(f"UICR-range 0x{a:08X} = 0x{w(a):08X}")
# search literals in bootloader region
import itertools
bl=[a for a in ad if 0xF4000<=a<0x100000]
blob=bytes(mem[a] for a in range(bl[0],bl[-1]+1) if a in mem) if bl else b''
print("bootloader span",hex(bl[0]),hex(bl[-1]))
for name,val in [("APPROTECT.DISABLE 0x40000558",0x40000558),("UICR.APPROTECT 0x10001208",0x10001208),("UICR base 0x10001000",0x10001000),("UICR.PSELRESET0 0x10001200",0x10001200),("UICR.REGOUT0 0x10001304",0x10001304),("NRF_POWER 0x40000000",0x40000000),("DBL_RESET_MEM 0x20007F7C",0x20007F7C),("UF2 app family 0xADA52840",0xADA52840),("UF2 boot family 0xD663823C",0xd663823c),("DCDCEN0 0x40000580",0x40000580),("DCDCEN 0x40000578",0x40000578)]:
    pat=struct.pack('<I',val);c=[];i=blob.find(pat)
    while i>=0: c.append(hex(bl[0]+i)); i=blob.find(pat,i+1)
    print(name,len(c),c[:6])
print("MBR vec",hex(w(0)),hex(w(4)),"app@0x26000 present:",0x26000 in mem, "0xFF000 settings present:",0xFF000 in mem, "0xFE000:",0xFE000 in mem)
