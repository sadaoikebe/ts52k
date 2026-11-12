# Residual charge on an unselected column (key on its last row pressed) leaking into the first read after the mux switches to it.
import numpy as np
def run(Ccol,Ck=6e-12,Cs_rest=410e-12,Rpd=100e3,G=44,V=3.3,t_high=6e-6,t_purge=6e-6,t_switch=3e-6):
    # unselected column: step +V via Ck, decay t_high, step -V, decay (t_purge+t_switch), then share with SENSE node at 0 V
    k=Ck/(Ck+Ccol); tau=Rpd*(Ccol+Ck)
    v=V*k*np.exp(-t_high/tau) - V*k
    v*=np.exp(-(t_purge+t_switch)/tau)
    node=v*(Ccol+Ck)/(Ccol+Ck+Cs_rest)
    return v*1e3,node*1e3,node*G/3.3*1023
for name,C in (('TC69 (Ccol 20 pF)',20e-12),('TS52K 4-layer (Ccol 60 pF)',60e-12)):
    for ck in (6e-12,3e-12):
        v,n,c=run(C,Ck=ck)
        print(f'{name:28s} pressed Ck={ck*1e12:.0f} pF: column residual {v:7.1f} mV -> node {n:6.2f} mV -> {c:6.1f} counts (10-bit) if purge is NOT done after the mux switch')
