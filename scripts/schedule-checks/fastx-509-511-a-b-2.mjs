import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
const root = 'C:/Users/USER/Documents/Coding Space/CXL/cxl-scheduler/.cindy-worktrees/sharp-bohr';
const base = path.join(root, 'artifacts/implementation/fastx-power-20261107/cohort-extension');
const logs = path.join(root, '.setup-logs/implementation/fastx-power-20261107/cohort-remaining');
const index = JSON.parse(fs.readFileSync(path.join(base, 'execution-index.json'), 'utf8'));
const prefix = index.recovery ? 'recovery' : 'coordinator';
const stderr = path.join(logs, prefix + '.stderr.txt');
const exitFile = path.join(logs, prefix + '.exit.txt');
const state = {status:index.status, cases:index.cases.filter(row => !['UPLOADING','RUNNING'].includes(row.status)), stderr_bytes:fs.existsSync(stderr)?fs.statSync(stderr).size:0, coordinator_exit:fs.existsSync(exitFile)?fs.readFileSync(exitFile,'utf8').trim():null};
const marker = path.join(logs, 'last-followup-state.json');
const previous = fs.existsSync(marker) ? JSON.stringify(JSON.parse(fs.readFileSync(marker, 'utf8'))) : '';
let missing = false;
if (index.status === 'RUNNING' && state.coordinator_exit === null) {
  const pid = index.recovery?.pid ?? 40540;
  if (!Number.isSafeInteger(pid) || pid <= 0) throw new Error('Invalid coordinator PID');
  const listing = execFileSync('C:/Windows/System32/tasklist.exe', ['/FI','PID eq ' + pid,'/FO','CSV','/NH'], {encoding:'utf8',timeout:5000,windowsHide:true});
  missing = !listing.split(/\r?\n/).some(line => {
    const fields = line.match(/^"([^"\r\n]+)","(\d+)"/);
    return fields && Number(fields[2]) === pid && /^python(?:w)?\.exe$/i.test(fields[1]);
  });
}
const actionable = state.cases.length > 0 || state.stderr_bytes > 0 || state.coordinator_exit !== null || index.status !== 'RUNNING';
console.log('CINDY_PRECHECK_OK');
process.exit(missing || (actionable && JSON.stringify(state) !== previous) ? 0 : 2);
