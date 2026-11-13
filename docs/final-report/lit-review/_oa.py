import json, pathlib
b=pathlib.Path('lit-review')
want=['10.1145/3575693.3578835','10.1145/3582016.3582063','10.1145/3669900','10.1145/3626111.3628195','10.1145/3713082.3730393','10.1145/3695794.3695808','10.1145/3695794.3695810','10.1145/3723851.3723858','10.1145/339647.339668']
d=json.loads((b/'openalex_works.json').read_text(encoding='utf-8'))
print('entries',len(d))
for k in want:
    v=d.get(k)
    if not v: print(k,'MISSING'); continue
    if 'error' in v: print(k,'ERR',v['error']); continue
    oa=v.get('open_access',{})
    best=v.get('best_oa_location') or {}
    print(k, '| oa=',oa.get('is_oa'),oa.get('oa_status'),'| pdf=',best.get('pdf_url'),'| landing=',best.get('landing_page_url'))
