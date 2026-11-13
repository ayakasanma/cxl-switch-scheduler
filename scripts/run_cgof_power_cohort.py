"""Run the eleven remaining frozen CGOF captures through the local FastX helper."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/implementation/fastx-power-20261107/cohort-extension'
LOG = ROOT / '.setup-logs/implementation/fastx-power-20261107/cohort-remaining'
PYTHON = ROOT / '.venv-fastx-power/Scripts/python.exe'
CASES = [(weight, seed, arm) for weight in (1, 2) for seed in (509, 510, 511)
         for arm in ('A', 'B') if (weight, seed, arm) != (1, 509, 'A')]
CASES.sort(key=lambda item: (item != (1, 510, 'A'), item))


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def export(case):
    weight, seed, arm = case
    name = f'cgof{weight}-{arm}-s{seed}'
    directory = BASE / name
    record = dict(case=name, status='EXPORTING', started_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    receipt = LOG / (name + '.export.json')
    save(receipt, record)
    if directory.exists():
        if case != (1, 510, 'A'):
            raise FileExistsError(directory)
        started = time.monotonic()
        exit_path = ROOT / '.setup-logs/implementation/fastx-power-20261107/export-cgof1-A-s510.exit.txt'
        while not exit_path.exists():
            if time.monotonic() - started > 5400:
                raise TimeoutError('Existing first export did not finish')
            time.sleep(15)
        code = int(exit_path.read_text(encoding='utf-8-sig'))
        record['reused_in_flight_export'] = True
    else:
        command = [str(PYTHON), '-B', 'scripts/export_cgof_power_vectors.py', '--evidence-root',
                   str(ROOT.parent.parent), '--weight', str(weight), '--seed', str(seed), '--arm', arm,
                   '--out', str(directory)]
        record['command'] = command
        save(receipt, record)
        environment = {key: value for key, value in os.environ.items() if key != 'FASTX_PASSWORD'}
        with (LOG / (name + '.export.stdout.json')).open('wb') as stdout, (LOG / (name + '.export.stderr.txt')).open('wb') as stderr:
            code = subprocess.run(command, cwd=ROOT, env=environment, stdout=stdout, stderr=stderr, timeout=5400).returncode
    record.update(exit=code, finished_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    if code:
        record['status'] = 'EXPORT_FAILED'
        save(receipt, record)
        raise RuntimeError(f'{name}: export exit {code}')
    metadata = json.loads((directory / 'metadata.json').read_text())
    assert metadata['status'] == 'MODEL_AND_SERIALIZED_PINS_CHECKED_GATE_NOT_RUN'
    assert (metadata['high_weight'], metadata['seed'], metadata['arm']) == case
    record.update(status='EXPORTED_AUDITED_GATE_NOT_RUN', metadata_sha256=digest(directory / 'metadata.json'))
    save(receipt, record)
    print(name + ': export audited', flush=True)
    return directory


def package(directory):
    target = LOG / (directory.name + '.tar')
    with tarfile.open(target, 'x') as output:
        for name in ('metadata.json', 'audit.json', 'source-freeze.zip', 'vectors.txt.gz'):
            output.add(directory / name, arcname=name)
        with zipfile.ZipFile(directory / 'source-freeze.zip') as archive:
            for name in archive.namelist():
                data = archive.read(name)
                member = tarfile.TarInfo(name)
                member.size = len(data)
                member.mode = 0o644
                output.addfile(member, io.BytesIO(data))
    return target


async def main():
    LOG.mkdir(parents=True, exist_ok=True)
    BASE.mkdir(parents=True, exist_ok=True)
    helper_path = Path(sys.argv[1])
    sys.argv = [str(helper_path), *sys.argv[2:]]
    spec = importlib.util.spec_from_file_location('fastx_skill_transport', helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    args = helper.parse_args()
    index = dict(schema='cxl-cgof-power-extension-v1', status='RUNNING', expected_cases=11,
                 existing_accepted_case='cgof1-A-s509', remote_parallelism=1, local_export_workers=2,
                 started_utc=dt.datetime.now(dt.timezone.utc).isoformat(), cases=[])
    index_path = BASE / 'execution-index.json'
    save(index_path, index)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [(case, pool.submit(export, case)) for case in CASES]
        async with helper.asyncssh.connect(host=args.host, port=args.port, username=args.user,
                password=os.environ['FASTX_PASSWORD'], known_hosts=str(args.known_hosts),
                connect_timeout=args.connect_timeout,
                preferred_auth=('publickey', 'keyboard-interactive', 'password')) as connection:
            preflight = await connection.run('hostname -f; id -un; uptime; df -Pk /home/chiang22; ps -u chiang22 -o pid,etime,pcpu,comm', check=False, timeout=30)
            (LOG / 'preflight.txt').write_text(preflight.stdout + preflight.stderr, encoding='utf-8')
            assert preflight.exit_status == 0 and preflight.stdout.splitlines()[1] == 'chiang22'
            index['backend'] = preflight.stdout.splitlines()[0]
            save(index_path, index)
            async with connection.start_sftp_client() as sftp:
                for case, future in futures:
                    while not future.done():
                        await asyncio.sleep(15)
                    directory = future.result()
                    archive = await asyncio.to_thread(package, directory)
                    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dt%H%M%Sz').lower()
                    remote = '/home/chiang22/cxl/experiments/cgof-power-' + directory.name.lower() + '-' + stamp
                    record = dict(case=directory.name, status='UPLOADING', remote_run=remote,
                                  package_sha256=digest(archive), package_bytes=archive.stat().st_size)
                    index['cases'].append(record)
                    save(index_path, index)
                    await sftp.mkdir(remote)
                    await sftp.put(archive, remote + '/payload.tar')
                    await sftp.put(LOG / 'remote-case.sh', remote + '/run.sh')
                    command = shlex.join(['bash', '-l', remote + '/run.sh', remote, str(case[0]), record['package_sha256']])
                    record.update(status='RUNNING', command=command, started_utc=dt.datetime.now(dt.timezone.utc).isoformat())
                    save(index_path, index)
                    process = await connection.create_process(command)
                    last = ''
                    while process.exit_status is None:
                        await asyncio.sleep(30)
                        progress = await connection.run('cat ' + shlex.quote(remote + '/payload/execution/reports/exits.txt') + ' 2>/dev/null; tail -2 ' + shlex.quote(remote + '/payload/execution/reports/sim.log') + ' 2>/dev/null', check=False, timeout=30)
                        if progress.stdout != last:
                            print(directory.name + '\n' + progress.stdout, flush=True)
                            last = progress.stdout
                    stdout, stderr = await process.communicate()
                    (LOG / (directory.name + '.remote.stdout.txt')).write_text(stdout, encoding='utf-8')
                    (LOG / (directory.name + '.remote.stderr.txt')).write_text(stderr, encoding='utf-8')
                    record.update(remote_exit=process.exit_status, status='EXITED_REVIEW_PENDING')
                    save(index_path, index)
                    await sftp.get(remote + '/evidence.tar.gz', directory / 'remote-evidence.tar.gz')
                    await sftp.get(remote + '/bootstrap.log', directory / 'remote-bootstrap.log')
                    evidence = directory / 'remote-evidence'
                    with tarfile.open(directory / 'remote-evidence.tar.gz') as returned:
                        returned.extractall(evidence, filter='data')
                    if process.exit_status:
                        record['status'] = 'FAILED'
                        index['status'] = 'INCOMPLETE_REMOTE_FAILURE'
                        save(index_path, index)
                        raise RuntimeError(directory.name + ': remote exit ' + str(process.exit_status))
                    check_command = [str(PYTHON), '-B', 'scripts/check_cgof_power_replay.py', 'replay',
                                     '--metadata', str(directory / 'metadata.json'),
                                     '--result', str(evidence / 'payload/execution/reports/replay.txt'),
                                     '--saif', str(evidence / 'payload/execution/activity.saif'),
                                     '--pt-reports', str(evidence / 'payload/execution/reports')]
                    environment = {key: value for key, value in os.environ.items() if key != 'FASTX_PASSWORD'}
                    with (directory / 'local-audit.json').open('wb') as out, (directory / 'local-audit.stderr.txt').open('wb') as err:
                        checked = subprocess.run(check_command, cwd=ROOT, env=environment, stdout=out, stderr=err, timeout=180)
                    record.update(local_audit_exit=checked.returncode, local_audit_command=check_command,
                                  evidence_sha256=digest(directory / 'remote-evidence.tar.gz'))
                    if checked.returncode:
                        record['status'] = 'LOCAL_AUDIT_FAILED'
                        index['status'] = 'INCOMPLETE_LOCAL_AUDIT_FAILURE'
                        save(index_path, index)
                        raise RuntimeError(directory.name + ': local audit failed')
                    record.update(status='COMMAND_EVIDENCE_CHECKED_PARENT_ACCEPTANCE_PENDING',
                                  finished_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                                  power_W=json.loads((directory / 'local-audit.json').read_text())['pt']['power_W'])
                    save(index_path, index)
                    print(directory.name + ': replay/SAIF/PT/local audit exit 0', flush=True)
    index.update(status='COHORT_EXECUTION_COMPLETE_PARENT_ACCEPTANCE_PENDING',
                 finished_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    save(index_path, index)


if __name__ == '__main__':
    asyncio.run(main())
