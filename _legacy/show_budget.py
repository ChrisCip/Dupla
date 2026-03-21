import json
b = json.loads(open(r'c:\Users\chris\Documents\Dupla\vision_output\PRESUPUESTO_FINAL.json','r',encoding='utf-8').read())
print(f'Project: {b["project"]}')
print(f'Chapters: {len(b["chapters"])}')
gt = 0
for ch in b['chapters']:
    ct = sum(float(i.get('total',0)) for i in ch.get('items',[]))
    gt += ct
    print(f'\n  {ch["code"]}. {ch["name"]}: RD$ {ct:,.2f}')
    for it in ch['items']:
        q = float(it["quantity"])
        p = float(it["unit_price"])
        t = float(it["total"])
        print(f'    {it["presto_code"]:<14} {it["description"][:38]:<38} {it["unit"]:>4} x{q:>8.1f} @{p:>10,.2f} = RD${t:>14,.2f}')
print(f'\n  TOTAL: RD$ {gt:,.2f}')
print(f'  Costo/m2: RD$ {gt/3426:,.2f}')
print(f'  Obs: {b.get("summary",{}).get("observations","")}')
