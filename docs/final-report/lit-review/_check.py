import json, pathlib
b=pathlib.Path('lit-review')
p=b/'_all_records.json'; d=json.loads(p.read_text(encoding='utf-8'))
keys=['cxl_intro','pond','tpp','directcxl','case_pool','my_cxl_pool','stfm','fqmem','atlas','tcm','bliss','fai','cxl_interplay','contention_cache','hpc_pool','cxldmsim','redit','sync_cxl','rethinking_pool','rixner','gupta','wfq_sort','arbiter_ppa']
text=(b.parent/'main.tex').read_text(encoding='utf-8')
import re
bibs=re.findall(r'\\bibitem\{([^}]+)\}\s*(.*?)(?=\n\\bibitem|\n\\end\{thebibliography\})',text,re.S)
print('bibs',len(bibs));print('recs',len(d))
for k,body in bibs:
    title=re.search(r'``(.*?)'')',body)
    print(k)
