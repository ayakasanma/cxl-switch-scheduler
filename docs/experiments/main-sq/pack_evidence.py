"""Package the accepted production replay for offline re-audit; no proprietary assets or builds."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--run',type=Path,required=True)
ap.add_argument('--output',type=Path,required=True)
args = ap.parse_args()
root = Path(__file__).resolve().parents[3]
summary_path = args.run/'summary.json'
summary = json.loads(summary_path.read_text())
assert summary['overall']=='PASS' and summary['run_id']=='20261023T083405Z_1850'
files = {p.relative_to(args.run).as_posix():p.read_bytes() for folder in ('results','junit') for p in (args.run/folder).iterdir() if p.is_file()}
for name in ('source_hashes_before.json','source_hashes_after.json','main_sq_diagnosis_scope.json'):
    files[name] = (args.run/name).read_bytes()
# Preserve original raw summary locally; portable projection retains every gate field read by the auditor.
portable = {k:summary[k] for k in ('overall','scope','run_id','sim_build_relaxations')}
portable['steps'] = [{k:v for k,v in s.items() if k in ('kind','name','status','exit_codes','junit','tests','failures','errors','skipped')} for s in summary['steps']]
portable['projection_of_original_sha256'] = hashlib.sha256(summary_path.read_bytes()).hexdigest()
files['summary.json'] = (json.dumps(portable,indent=2)+'\n').encode()
for policy in range(3):
    name = f'cocotb_hs_p{policy}_w5000000_seed509__hog_sparse_metrics.json'
    files['reference/'+name] = (root/'artifacts/implementation/HS-main/20261022T034507Z_311/results'/name).read_bytes()
manifest = dict(kind='curated project-owned raw replay, no simulator binaries/builds',
                summary='portable gate-field projection; original summary/logs retained in run directory',
                files={n:hashlib.sha256(b).hexdigest() for n,b in sorted(files.items())})
files['BUNDLE_MANIFEST.json'] = (json.dumps(manifest,indent=2)+'\n').encode()
with args.output.open('xb') as raw:
    with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,filename='') as gz:
        with tarfile.open(fileobj=gz,mode='w') as archive:
            for name,data in sorted(files.items()):
                item = tarfile.TarInfo(name)
                item.size,item.mode,item.mtime = len(data),0o644,0
                archive.addfile(item,io.BytesIO(data))
with tarfile.open(args.output,'r:gz') as archive:
    assert set(archive.getnames())==set(files)
    for name,data in files.items():
        assert archive.extractfile(name).read()==data
print(json.dumps(dict(status='PASS',files=len(files),bytes=args.output.stat().st_size,sha256=hashlib.sha256(args.output.read_bytes()).hexdigest())))
