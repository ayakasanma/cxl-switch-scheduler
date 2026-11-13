import urllib.request, pathlib
urls={
 'case_pool':'https://conferences.sigcomm.org/hotnets/2023/papers/hotnets23_levis.pdf',
 'rixner':'https://groups.csail.mit.edu/cag/PSRG/papers/rixner_isca27.pdf',
}
b=pathlib.Path('lit-review/fulltexts')
for k,u in urls.items():
    try:
        req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'})
        with urllib.request.urlopen(req,timeout=90) as r: d=r.read()
        (b/(k+'.pdf')).write_bytes(d); print(k,len(d),d[:4])
    except Exception as e: print(k,'ERR',e)
