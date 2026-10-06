"""DRC breakdown (kicad-cli json) by severity/type, with refs for errors."""
import json, sys, collections, re
for b in ('Core','Base'):
    d=json.load(open(f'lr_drc/drc_{b}.json'))
    print(f"== {b}: unconnected_items {len(d.get('unconnected_items',[]))}, schematic_parity {len(d.get('schematic_parity',[]))}, violations {len(d['violations'])}")
    c=collections.Counter((v['severity'],v['type']) for v in d['violations'])
    for (s,t),n in sorted(c.items(), key=lambda x:(x[0][0]!='error',-x[1])): print(f"   {s:8s} {t:32s} {n}")
    pc=collections.Counter(v['type'] for v in d.get('schematic_parity',[]))
    if pc: print('   parity:',dict(pc))
    for v in d['violations']:
        if v['severity']=='error':
            items='; '.join(i['description'][:70]+' @(%.2f,%.2f)'%(i['pos']['x'],i['pos']['y']) for i in v['items'])
            print(f"   ERR {v['type']}: {v['description'][:60]} | {items}")
    for v in d.get('schematic_parity',[])[:12]:
        print('   PAR', v['type'], v['description'][:80], '|', '; '.join(i['description'][:60] for i in v['items']))

print('\n== detail')
for b in ('Core','Base'):
    d=json.load(open(f'lr_drc/drc_{b}.json'))
    for v in d.get('schematic_parity',[]):
        if v['type']!='missing_footprint': print(b,'PAR',v['type'],v['description'][:90],'|','; '.join(i['description'][:70] for i in v['items']))
    for t in ('connection_width','copper_sliver','holes_co_located','padstack','lib_footprint_mismatch'):
        for v in d['violations']:
            if v['type']==t: print(b,t,'|','; '.join(i['description'][:60]+' @(%.2f,%.2f)'%(i['pos']['x'],i['pos']['y']) for i in v['items']))
    sm=collections.Counter()
    for v in d['violations']:
        if v['type']=='solder_mask_bridge':
            refs=set()
            for i in v['items']:
                m=re.search(r' of (\S+)',i['description']); 
                refs.add(m.group(1) if m else i['description'].split(' ')[0])
            sm[tuple(sorted(refs))]+=1
    if sm:
        byref=collections.Counter()
        for k,n in sm.items():
            for r in k: byref[r]+=n
        print(b,'solder_mask_bridge by item:',byref.most_common(40))
