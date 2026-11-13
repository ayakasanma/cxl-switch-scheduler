import json, urllib.parse, urllib.request, time
dois=['10.1145/3669900','10.1145/3582016.3582063','10.1145/3575693.3578835','10.1145/3626111.3628195','10.1145/3695794.3695808','10.1145/3695794.3695810','10.1145/3723851.3723858','10.1145/339647.339668']
out={}
for doi in dois:
    u='https://api.openalex.org/works/https://doi.org/'+doi+'?mailto=research@example.edu'
    try:
        with urllib.request.urlopen(u,timeout=30) as r: d=json.load(r)
        out[doi]={'title':d.get('title'),'oa':d.get('open_access'),'best':d.get('best_oa_location'),'locs':[{'pdf':x.get('pdf_url'),'landing':x.get('landing_page_url'),'source':(x.get('source') or {}).get('display_name')} for x in d.get('locations',[]) if x.get('pdf_url')]}
        print(doi,'OK',d.get('open_access',{}).get('is_oa'),[x['pdf'] for x in out[doi]['locs']])
    except Exception as e:
        print(doi,'ERR',e)
    time.sleep(.3)
open('lit-review/oa_missing.json','w',encoding='utf-8').write(json.dumps(out,indent=1,ensure_ascii=False))
