# TC69 AFE time-domain model: row step -> Ck -> column(Ccol,100k) -> mux Ron -> SENSE(Cs) -> x44 op-amp (GBW, slew)
import numpy as np
def sim(Ck=1e-12,Ccol=20e-12,Cs=410e-12,Ron=800.,Rpd=100e3,G=44.,gbw=8.2e6,sr=5e6,V=3.3,T=40e-6,dt=1e-9,trise=5e-9):
    n=int(T/dt); vc=vs=vo=0.; out=np.zeros(n); vr_prev=0.
    wc=2*np.pi*gbw/G
    for i in range(n):
        t=i*dt; vr=V*min(1,t/trise)
        # charge injected through Ck by dVr (Ck small vs Ccol): dq = Ck*(dvr - dvc) -> implicit small-step
        ic=(vc-vs)/Ron
        dvc=(Ck*(vr-vr_prev) - (ic+vc/Rpd)*dt)/(Ccol+Ck)
        vs+= ic*dt/Cs; vc+=dvc; vr_prev=vr
        dvo=wc*(G*vs-vo)*dt; dvo=max(-sr*dt,min(sr*dt,dvo)); vo+=dvo
        vo=min(vo,3.25); out[i]=vo
    return out
def report(label,**kw):
    o=sim(**kw); dt=1e-9; ip=o.argmax(); 
    f=lambda us:o[int(us*1e-6/dt)]
    slope=lambda us:(f(us+0.25)-f(us-0.25))/0.5/o.max()*100
    print(f"{label:38s} peak {o.max()*1000:6.1f} mV at {ip*dt*1e6:4.1f} us | V(1.5/2.5/4/6/10/20us) =",
          ' '.join(f"{f(u)/o.max()*100:5.1f}%" for u in (1.5,2.5,4,6,10,20)),
          "| slope %/us @2,4,6:",' '.join(f"{slope(u):+5.1f}" for u in (2,4,6)))
    return o.max()
print("--- 1 pF step, node model")
a=report("TC69 est (Ccol20,Cs410,Ron800)")
report("TC69 Ron=200",Ron=200.); report("TC69 Ron=3k",Ron=3000.)
b=report("TS52K-4L (Ccol60,Cs410)",Ccol=60e-12)
c=report("TS52K-4L, C2->300p (Cs380)",Ccol=60e-12,Cs=380e-12)
print("ratio 4L/TC69 %.3f ; with 300p %.3f"%(b/a,c/a))
report("TS52K-4L Rpd=220k",Ccol=60e-12,Rpd=220e3)
report("5 pF (pressed, large signal)",Ck=5e-12)
print("ADC counts per pF (10bit): %.0f ; (12bit): %.0f"%(a/3.3*1023,a/3.3*4095))
