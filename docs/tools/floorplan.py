import json,math,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Wedge,Rectangle,FancyBboxPatch
from matplotlib import font_manager
keys=json.load(open('ref/out/ts52k_keys.json'))
K={k[0]:(k[1],k[2]) for k in keys}
cols=[['MX2','MX3','MX4','MX5'],['MX7','MX8','MX13','MX9'],['MX11','MX12','MX18','MX14'],['MX16','MX17','MX22','MX23'],
['MX20','MX21','MX27'],['MX25','MX26','MX31'],['MX29','MX30','MX35','MX60'],['MX33','MX34','MX39'],
['MX37','MX38','MX44','MX81'],['MX42','MX43','MX48','MX82'],['MX46','MX47','MX52','MX58'],['MX51','MX56','MX75','MX61'],
['MX55','MX65','MX66','MX67'],['MX64','MX74','MX71']]
assert sorted(sum(cols,[]))==sorted(K), set(K)-set(sum(cols,[]))
json.dump(cols,open('ref/out/ts52k_ec_columns.json','w'))
fig,ax=plt.subplots(figsize=(22,7.2),dpi=110)
X0,X1,Y0,Y1=-3.57,303.61,45.24,121.44
ax.add_patch(Rectangle((X0,Y0),X1-X0,Y1-Y0,fc='#f7f7f2',ec='k',lw=1.5))
ax.add_patch(Rectangle((16.68,41.09),14.28,4.2,fc='#f7f7f2',ec='k',lw=1.5))
# lanes
ax.add_patch(Rectangle((X0+0.5,113.2),X1-X0-1,7.7,fc='#ffe9a8',ec='none',alpha=.8))
ax.text(150,122.9,'bottom lane (L4, y=113.2-120.9): column tails + SENSE trunk, pitch >=1.5 mm, GND between, L3 solid GND',ha='center',va='top',fontsize=9,color='#8a6d00')
ax.add_patch(Rectangle((46,45.8),236,6.5,fc='#d9e8ff',ec='none',alpha=.8))
ax.text(160,44.6,'top lane (L4): encoder A/B/SW and other non-matrix slow nets only',ha='center',va='bottom',fontsize=9,color='#1f4e9c')
for name,(x,y) in K.items():
    ax.add_patch(Wedge((x,y),8.5,0,360,width=1.5,fc='#bdbdbd',ec='none'))
    ax.add_patch(Wedge((x,y),6,90,270,width=3.75,fc='#e07b39',ec='none'))
    ax.add_patch(Wedge((x,y),6,-90,90,width=3.75,fc='#3b7dd8',ec='none'))
colA='#b3005e';colB='#00796b'
for i,c in enumerate(cols):
    pts=[K[k] for k in c]; col=colA if i<6 else colB
    ax.plot([p[0] for p in pts],[p[1] for p in pts],'-',color=col,lw=2.2,zorder=5)
    ax.text(pts[0][0],pts[0][1]-9.6,f'c{i+1}',color=col,ha='center',va='bottom',fontsize=9,fontweight='bold')
# blocks
def box(x,y,w,h,label,fc,ec='k'):
    ax.add_patch(FancyBboxPatch((x-w/2,y-h/2),w,h,boxstyle='round,pad=0.3',fc=fc,ec=ec,lw=1.2,zorder=8,alpha=.92))
    ax.text(x,y,label,ha='center',va='center',fontsize=8,zorder=9)
ax.add_patch(Rectangle((15.5,41.5),30.5,41.5,fc='none',ec='#d32f2f',lw=2,ls='--',zorder=7))
ax.text(46.5,60,'async digital island\n(USB, RP2040, QSPI flash,\n12 MHz osc, LDO) = rev 0.2 position',color='#d32f2f',fontsize=8,va='center',zorder=9,bbox=dict(fc='white',ec='none',alpha=.8,pad=1))
box(24.7,64,7,7,'RP2040','#ffcdd2')
box(32.2,88.7,9,7,'AFE\nC2,AD8601','#c8e6c9')
box(75,107.5,11,7,'MUX A\nc1-c6','#f8bbd0')
box(222.6,103.2,7,9,'MUX B\nc7-c14','#b2dfdb')
box(297.8,47.3,11,7,'encoder','#eeeeee')
# SENSE trunk
sx=[27,30,32.2,26,22,22,75,75]; sy=[69,78,85,95,108,116.5,116.5,111.5]
ax.plot(sx,sy,'-',color='#2e7d32',lw=2.6,zorder=6)
ax.plot([75,222.6,222.6],[118.3,118.3,108],'-',color='#2e7d32',lw=2.6,zorder=6)
ax.plot([75,75],[116.5,118.3],'-',color='#2e7d32',lw=2.6,zorder=6)
ax.text(120,119.3,'SENSE trunk (hi-Z, >=2 mm from non-matrix nets)',color='#2e7d32',fontsize=8,va='center',zorder=9)
# tails (schematic)
for i,c in enumerate(cols):
    x,y=K[c[-1]]; tx=75 if i<6 else 222.6; col=colA if i<6 else colB
    yl=114+ (abs(i-(2.5 if i<6 else 9.5)))*0.9
    ax.plot([x,x,tx],[y,yl,yl],'-',color=col,lw=1.0,zorder=4,alpha=.9)
ax.set_xlim(-8,308);ax.set_ylim(126,39);ax.set_aspect('equal');ax.axis('off')
ax.set_title('TS52K-EC floor plan proposal (bottom-side parts shown through the board; existing 307.2 x 76.2 mm outline, unchanged)  orange=drive half (row), blue=sense half (column), grey=GND guard ring',fontsize=10)
plt.tight_layout();plt.savefig('floorplan-ts52k-ec.png');print('ok')
