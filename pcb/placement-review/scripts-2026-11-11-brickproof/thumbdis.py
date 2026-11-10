import sys,struct
from capstone import *
exec(open('/tmp/brick/tools/hexinfo.py').read().split("mem=load")[0])
mem=load(sys.argv[1]);lo,hi=int(sys.argv[2],16),int(sys.argv[3],16)
md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS);md.skipdata=True
for i in md.disasm(bytes(mem.get(a,0xff) for a in range(lo,hi)),lo): print(f"{i.address:06X}: {i.mnemonic} {i.op_str}")
