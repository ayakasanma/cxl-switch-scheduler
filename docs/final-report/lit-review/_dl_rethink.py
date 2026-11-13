import urllib.request, pathlib
u='https://www.research.ed.ac.uk/files/647579832/XingandBarbalaceHDCS2025RethinkingApplicationsAddressSpace.pdf'
req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36','Referer':'https://www.research.ed.ac.uk/'})
try:
    with urllib.request.urlopen(req,timeout=90) as r: d=r.read()
    pathlib.Path('lit-review/fulltexts/rethinking_pool.pdf').write_bytes(d); print(len(d),d[:4])
except Exception as e: print('ERR',e)
