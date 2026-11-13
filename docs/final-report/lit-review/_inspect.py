import json, pathlib
base=pathlib.Path('lit-review')
files=['openalex_works.json','directed_openalex.json','_all_records.json','crossref_abstracts.json']
for fn in files:
    p=base/fn
    if not p.exists(): continue
    d=json.loads(p.read_text(encoding='utf-8'))
    print('===',fn,type(d).__name__)
    if isinstance(d,dict):
        print(list(d)[:5])
    elif isinstance(d,list):
        print('len',len(d), (list(d[0])[:8] if d else ''))
