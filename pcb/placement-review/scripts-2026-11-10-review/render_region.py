import pcbnew,sys,math
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Circle,Rectangle
from matplotlib.collections import LineCollection,PolyCollection
mm=pcbnew.ToMM
def render(path,x0,y0,x1,y1,out,scale=40,zones=True,labels=True,layers='FB',netlabels=True,refs=True,fill=None):
    b=pcbnew.LoadBoard(path) if isinstance(path,str) else path
    W=(x1-x0);H=(y1-y0)
    fig=plt.figure(figsize=(W*scale/100,H*scale/100),dpi=100)
    ax=fig.add_axes([0,0,1,1]);ax.set_xlim(x0,x1);ax.set_ylim(y1,y0);ax.set_aspect('equal');ax.set_facecolor('#101010')
    def inb(x,y,m=3): return x0-m<=x<=x1+m and y0-m<=y<=y1+m
    # zone fills
    if zones:
        for z in b.Zones():
            if z.GetIsRuleArea():
                o=z.Outline()
                pts=[(mm(o.CVertex(i).x),mm(o.CVertex(i).y)) for i in range(o.TotalVertices())]
                ax.add_patch(Polygon(pts,fill=False,ec='yellow',lw=1,ls='--',zorder=9));continue
            for lay,col in ((pcbnew.F_Cu,'#501010'),(pcbnew.B_Cu,'#101850')):
                if not z.IsOnLayer(lay): continue
                if (lay==pcbnew.F_Cu and 'F' not in (fill or layers)) or (lay==pcbnew.B_Cu and 'B' not in (fill or layers)): continue
                ps=z.GetFilledPolysList(lay)
                for i in range(ps.OutlineCount()):
                    ol=ps.Outline(i)
                    pts=[(mm(ol.CPoint(j).x),mm(ol.CPoint(j).y)) for j in range(ol.PointCount())]
                    if not any(inb(*p,m=0) for p in pts[::3]) and not (min(p[0] for p in pts)<x0 and max(p[0] for p in pts)>x1): continue
                    ax.add_patch(Polygon(pts,fc=col,ec='none',alpha=0.55,zorder=1 if lay==pcbnew.F_Cu else 2))
                    for h in range(ps.HoleCount(i)):
                        hl=ps.Hole(i,h)
                        hp=[(mm(hl.CPoint(j).x),mm(hl.CPoint(j).y)) for j in range(hl.PointCount())]
                        if any(inb(*p,m=0) for p in hp[::2]):
                            ax.add_patch(Polygon(hp,fc='#101010',ec='none',alpha=0.75,zorder=1.5 if lay==pcbnew.F_Cu else 2.5))
    # edge cuts
    for d in b.GetDrawings():
        if d.GetLayer()==pcbnew.Edge_Cuts and d.GetClass()=='PCB_SHAPE':
            s=d.GetStart();e=d.GetEnd()
            if d.GetShape()==pcbnew.SHAPE_T_SEGMENT:
                ax.plot([mm(s.x),mm(e.x)],[mm(s.y),mm(e.y)],color='#e0e000',lw=1.5,zorder=10)
            elif d.GetShape()==pcbnew.SHAPE_T_ARC:
                m=d.GetArcMid();ax.plot([mm(s.x),mm(m.x),mm(e.x)],[mm(s.y),mm(m.y),mm(e.y)],color='#e0e000',lw=1.5,zorder=10)
            elif d.GetShape()==pcbnew.SHAPE_T_CIRCLE:
                ax.add_patch(Circle((mm(s.x),mm(s.y)),mm(d.GetRadius()),fill=False,ec='#e0e000',lw=1.5,zorder=10))
    # pads
    for fp in b.GetFootprints():
        p=fp.GetPosition()
        if not inb(mm(p.x),mm(p.y),m=25): continue
        for pad in fp.Pads():
            pp=pad.GetPosition()
            if not inb(mm(pp.x),mm(pp.y)): continue
            for lay,col,zo in ((pcbnew.F_Cu,'#d04040',5),(pcbnew.B_Cu,'#4060e0',6)):
                if pad.IsOnLayer(lay) and (('F' if lay==pcbnew.F_Cu else 'B') in layers):
                    ps=pcbnew.SHAPE_POLY_SET(); pad.TransformShapeToPolygon(ps,lay,0,pcbnew.FromMM(0.01),pcbnew.ERROR_INSIDE)
                    for i in range(ps.OutlineCount()):
                        ol=ps.Outline(i);pts=[(mm(ol.CPoint(j).x),mm(ol.CPoint(j).y)) for j in range(ol.PointCount())]
                        ax.add_patch(Polygon(pts,fc=col,ec='none',alpha=0.8,zorder=zo))
            if pad.GetDrillSize().x>0:
                ds=pad.GetDrillSize()
                ax.add_patch(Circle((mm(pp.x),mm(pp.y)),mm(ds.x)/2,fc='#000',ec='#aaa',lw=0.5,zorder=8))
            if labels and scale>=30:
                ax.text(mm(pp.x),mm(pp.y),pad.GetNumber()+('\n'+pad.GetNetname().split('/')[-1][:10] if netlabels else ''),color='w',fontsize=max(3,scale/9),ha='center',va='center',zorder=20)
        if refs: ax.text(mm(p.x),mm(p.y),fp.GetReference(),color='#ffff80',fontsize=max(5,scale/5),ha='center',va='center',zorder=21,alpha=0.9)
    # tracks
    for t in b.GetTracks():
        if t.GetClass()=='PCB_VIA':
            p=t.GetPosition()
            if not inb(mm(p.x),mm(p.y)): continue
            ax.add_patch(Circle((mm(p.x),mm(p.y)),mm(t.GetWidth(pcbnew.F_Cu))/2,fc='#c0c0c0' if t.GetNetname()!='GND' else '#607060',ec='none',zorder=7))
            ax.add_patch(Circle((mm(p.x),mm(p.y)),mm(t.GetDrill())/2,fc='#000',ec='none',zorder=8))
            if netlabels and t.GetNetname()!='GND' and scale>=30: ax.text(mm(p.x),mm(p.y)-0.4,t.GetNetname().split('/')[-1][:8],color='#ffffff',fontsize=max(3,scale/10),ha='center',zorder=22)
        else:
            s=t.GetStart();e=t.GetEnd()
            if not (inb(mm(s.x),mm(s.y)) or inb(mm(e.x),mm(e.y)) or (min(mm(s.x),mm(e.x))<x0 and max(mm(s.x),mm(e.x))>x1 and y0<mm(s.y)<y1)or (min(mm(s.y),mm(e.y))<y0 and max(mm(s.y),mm(e.y))>y1 and x0<mm(s.x)<x1)): continue
            lay=t.GetLayer()
            if (lay==pcbnew.F_Cu and 'F' not in layers) or (lay==pcbnew.B_Cu and 'B' not in layers): continue
            col='#ff5050' if lay==pcbnew.F_Cu else '#50a0ff'
            lw=mm(t.GetWidth())*scale*72/100
            ax.plot([mm(s.x),mm(e.x)],[mm(s.y),mm(e.y)],color=col,lw=lw,solid_capstyle='round',zorder=4 if lay==pcbnew.F_Cu else 3,alpha=0.9)
            L=math.hypot(mm(e.x-s.x),mm(e.y-s.y))
            if netlabels and L>2.0 and scale>=30:
                mx=(mm(s.x)+mm(e.x))/2;my=(mm(s.y)+mm(e.y))/2
                if inb(mx,my,0):
                    ang=-math.degrees(math.atan2(mm(e.y-s.y),mm(e.x-s.x)))
                    if ang>90: ang-=180
                    if ang<=-90: ang+=180
                    ax.text(mx,my,t.GetNetname().split('/')[-1][:10],color='#ffff00' if lay==pcbnew.F_Cu else '#a0ffff',fontsize=max(3,scale/10),ha='center',va='center',rotation=ang,zorder=23)
    # grid ticks
    step=5 if W>40 else (2 if W>15 else 1)
    for gx in range(int(x0)//step*step,int(x1)+1,step):
        ax.axvline(gx,color='#ffffff',lw=0.2,alpha=0.3);ax.text(gx,y0+0.02*H,str(gx),color='#0f0',fontsize=6,zorder=30)
    for gy in range(int(y0)//step*step,int(y1)+1,step):
        ax.axhline(gy,color='#ffffff',lw=0.2,alpha=0.3);ax.text(x0+0.005*W,gy,str(gy),color='#0f0',fontsize=6,zorder=30)
    fig.savefig(out);plt.close(fig)
if __name__=='__main__':
    a=sys.argv
    kw={}
    for k in a[7:]:
        kk,v=k.split('=');kw[kk]=(v if kk in('layers','fill') else (float(v) if kk=='scale' else v=='1'))
    render(a[1],float(a[2]),float(a[3]),float(a[4]),float(a[5]),a[6],**kw)
