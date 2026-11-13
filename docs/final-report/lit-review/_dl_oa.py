import urllib.request, pathlib
urls={
 'pond':'https://arxiv.org/pdf/2203.00241',
 'tpp':'https://arxiv.org/pdf/2206.02878',
 'cxl_intro':'https://arxiv.org/pdf/2306.11227',
 'rethinking_pool':'https://www.research.ed.ac.uk/files/647579832/XingandBarbalaceHDCS2025RethinkingApplicationsAddressSpace.pdf',
}
b=pathlib.Path('lit-review/fulltexts')
for k,u in urls.items():
    try:
        req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req,timeout=90) as r: data=r.read()
        p=b/(k+'.pdf'); p.write_bytes(data)
        print(k,len(data),data[:4])
    except Exception as e: print(k,'ERR',e)
