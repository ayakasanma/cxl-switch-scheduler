import pathlib, json
from pypdf import PdfReader
b=pathlib.Path('lit-review/fulltexts')
rep={}
for p in sorted(b.glob('*.pdf')):
    try:
        r=PdfReader(str(p)); n=len(r.pages)
        txt='\n'.join((pg.extract_text() or '') for pg in r.pages)
        (b/(p.stem+'.txt')).write_text(txt,encoding='utf-8')
        rep[p.name]={'pages':n,'chars':len(txt)}
        print(f'{p.name:34s} pages={n:3d} chars={len(txt):7d}')
    except Exception as e:
        rep[p.name]={'error':str(e)}; print(p.name,'ERR',e)
(b/'extract_report.json').write_text(json.dumps(rep,indent=1),encoding='utf-8')
