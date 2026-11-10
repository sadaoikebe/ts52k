import subprocess,json,sys,collections
PCB='/home/hatch/workspace/ts52k-fable/pcb/ts52k.kicad_pcb'
def run(out='/tmp/w/drc.json'):
    subprocess.run(['kicad-cli','pcb','drc','--severity-all','--schematic-parity','--format','json','--units','mm','-o',out,PCB],capture_output=True)
    subprocess.run(['git','-C','/home/hatch/workspace/ts52k-fable','checkout','pcb/ts52k.kicad_pro'],capture_output=True)
    return json.load(open(out))
def show(d,skip=('silk_overlap','silk_over_copper','silk_edge_clearance','text_height','text_thickness'),box=None,maxn=60):
    c=collections.Counter(v['type'] for v in d['violations'])
    print('viol',dict(c),'unconn',len(d['unconnected_items']),'parity',len(d.get('schematic_parity',[])))
    n=0
    for v in d['violations']:
        if v['type'] in skip: continue
        p=v['items'][0]['pos']
        if box and not (box[0]<=p['x']<=box[2] and box[1]<=p['y']<=box[3]): continue
        print(' ',v['type'],v['description'][:60],'|',' / '.join(f"{i['description'][:48]}@{i['pos']['x']:.2f},{i['pos']['y']:.2f}" for i in v['items']))
        n+=1
        if n>=maxn: break
    for p in d.get('schematic_parity',[])[:10]: print('  PAR',p['description'],[i['description'] for i in p['items']])
def unconn(d,maxn=80):
    for u in d['unconnected_items'][:maxn]:
        print('  U',' / '.join(f"{i['description'][:50]}@{i['pos']['x']:.2f},{i['pos']['y']:.2f}" for i in u['items']))
if __name__=='__main__':
    d=run(); show(d)
    if len(sys.argv)>1: unconn(d)
