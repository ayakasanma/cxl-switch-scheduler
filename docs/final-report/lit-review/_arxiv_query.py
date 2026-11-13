import urllib.parse, urllib.request, xml.etree.ElementTree as ET
qs=['Pond CXL-Based Memory Pooling Systems for Cloud Platforms','TPP Transparent Page Placement for CXL-Enabled Tiered-Memory','An Introduction to the Compute Express Link CXL Interconnect','A Case Against CXL Memory Pooling','Contention Aware DRAM Caching for CXL-Enabled Pooled Memory','Synchronization for CXL Based Memory','Rethinking Applications Address Space with CXL Shared Memory Pools','Memory Access Scheduling Rixner Dally']
for q in qs:
    u='http://export.arxiv.org/api/query?search_query='+urllib.parse.quote('all:"'+q+'"')+'&max_results=3'
    try:
        with urllib.request.urlopen(u,timeout=30) as r: raw=r.read().decode('utf-8')
        root=ET.fromstring(raw); ns={'a':'http://www.w3.org/2005/Atom'}
        ents=root.findall('a:entry',ns)
        print('QUERY',q)
        for e in ents: print('  ',e.find('a:id',ns).text,e.find('a:title',ns).text.strip().replace('\n',' '))
    except Exception as e: print('ERR',q,e)
