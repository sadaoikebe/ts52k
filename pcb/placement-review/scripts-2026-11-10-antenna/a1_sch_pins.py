"""Reassign the 18 matrix/encoder GPIOs on the MDBT50Q child sheet.
Each signal is a wire from the U5 pin end to a hierarchical label; unused pins carry a no_connect."""
import re,sys,uuid
P='/home/hatch/workspace/ts52k-fable/pcb/mdbt50q.kicad_sch'
s=open(P).read()
# U5 at (106.68,101.6): left pin ends x=86.36 (label x=63.5), right pin ends x=127.0 (label x=139.7); y=101.6-local_y
PIN={3:('L',129.54),4:('L',132.08),5:('L',134.62),6:('L',137.16),7:('L',139.7),8:('L',142.24),9:('L',71.12),10:('L',81.28),
     11:('L',68.58),12:('L',86.36),13:('L',78.74),14:('L',83.82),16:('R',121.92),20:('L',73.66),22:('R',73.66),24:('R',76.2),
     26:('R',134.62),37:('R',81.28),41:('R',91.44),42:('R',101.6),43:('R',106.68),44:('R',104.14),46:('R',109.22),48:('R',114.3),49:('R',116.84)}
NEW={'rpg1':4,'rpg2':6,'row1':8,'row6':10,'row2':12,'row7':14,'col6':16,'col5':20,'col4':22,'col3':24,'col2':26,
     'row3':37,'row8':41,'row4':43,'row9':44,'row5':46,'row10':48,'col1':49}
def f(v): return ('%.4f'%v).rstrip('0').rstrip('.')
def blocks(kind):
    # top-level blocks (either tab-indented or unindented)
    out=[]
    for m in re.finditer(r'\n(\t?)\(%s\b'%kind,s):
        i=m.start()+1; d=0; j=i
        while True:
            c=s[j]
            if c=='(': d+=1
            elif c==')':
                d-=1
                if d==0: break
            j+=1
        out.append((i,j+1))
    return out
rm=[]
names=set(NEW)
for a,b in blocks('hierarchical_label'):
    n=re.match(r'\t?\(hierarchical_label "([^"]+)"',s[a:b]).group(1)
    if n in names:
        m=re.search(r'\(at ([-\d.]+) ([-\d.]+)',s[a:b]); rm.append((a,b,float(m.group(1)),float(m.group(2))))
lab=[(x,y) for _,_,x,y in rm]
assert len(rm)==18,len(rm)
for a,b in blocks('wire'):
    pts=re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)',s[a:b]); pts=[(float(x),float(y)) for x,y in pts]
    if any(p in lab for p in pts) and {p[0] for p in pts}<= {63.5,86.36,127.0,139.7} and pts[0][1]==pts[1][1]:
        rm.append((a,b,0,0))
assert len(rm)==36,len(rm)
newpins={NEW[n] for n in NEW}
ncpos={ (86.36 if PIN[p][0]=='L' else 127.0, PIN[p][1]) for p in newpins}
nrm=0
for a,b in blocks('no_connect'):
    m=re.search(r'\(at ([-\d.]+) ([-\d.]+)\)',s[a:b]); q=(float(m.group(1)),float(m.group(2)))
    if q in ncpos: rm.append((a,b,0,0)); nrm+=1
for a,b,_,_ in sorted(rm,reverse=True):
    e=b
    if s[e]=='\n': e+=1
    s=s[:a]+s[e:]
add=''
for n,p in NEW.items():
    side,y=PIN[p]; x0=86.36 if side=='L' else 127.0; x1=63.5 if side=='L' else 139.7
    add+=f'''\t(wire
\t\t(pts
\t\t\t(xy {f(x0)} {f(y)}) (xy {f(x1)} {f(y)})
\t\t)
\t\t(stroke
\t\t\t(width 0)
\t\t\t(type default)
\t\t)
\t\t(uuid "{uuid.uuid4()}")
\t)
\t(hierarchical_label "{n}"
\t\t(shape bidirectional)
\t\t(at {f(x1)} {f(y)} {180 if side=='L' else 0})
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1 1)
\t\t\t)
\t\t\t(justify {'right' if side=='L' else 'left'})
\t\t)
\t\t(uuid "{uuid.uuid4()}")
\t)
'''
old_used={3,4,5,6,7,8,9,10,11,12,13,14,41,42,44,46,48,49}
for p in sorted(old_used-newpins):
    side,y=PIN[p]; x0=86.36 if side=='L' else 127.0
    add+=f'''\t(no_connect
\t\t(at {f(x0)} {f(y)})
\t\t(uuid "{uuid.uuid4()}")
\t)
'''
k=s.rfind('\n\t(sheet_instances')
if k<0: k=s.rfind('\n)')
s=s[:k+1]+add+s[k+1:]
open(P,'w').write(s)
print('removed NC',nrm,'added NC',len(old_used-newpins))
