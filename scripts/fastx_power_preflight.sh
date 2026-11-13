#!/usr/bin/env bash
set -u

check() {
    local status
    printf '\nCOMMAND'
    printf ' %q' "$@"
    printf '\n'
    "$@" 2>&1
    status=$?
    printf 'EXIT_STATUS=%s\n' "$status"
}

printf 'CXL_FASTX_POWER_PREFLIGHT_V1\n'
check date -Is
check hostname -f
check id -un
check uname -sr
if type module >/dev/null 2>&1; then
    check module list
    check module load Synopsys_x86-64/2024
    check module list
else
    printf 'MODULE=UNAVAILABLE\n'
fi
for tool in dc_shell pt_shell vcs srun salloc sbatch squeue qstat bsub; do
    check command -v "$tool"
done
for tool in dc_shell pt_shell; do
    if command -v "$tool" >/dev/null 2>&1; then
        check /usr/bin/timeout 10 "$tool" -version </dev/null
    fi
done
check ps -u "$(id -un)" -o pid,ppid,etime,comm
printf 'SLURM_JOB_ID=%s\n' "${SLURM_JOB_ID:-UNSET}"
printf 'PBS_JOBID=%s\n' "${PBS_JOBID:-UNSET}"
printf 'LSB_JOBID=%s\n' "${LSB_JOBID:-UNSET}"
if (( $# > 32 )); then
    printf 'INPUT_LIMIT_EXCEEDED\n'
    exit 2
fi
for input in "$@"; do
    if [[ ! $input =~ ^/[A-Za-z0-9_./-]+$ || $input == *..* ]]; then
        printf 'INVALID_INPUT_PATH\n'
        exit 2
    fi
    check test -r "$input"
    if [[ -f $input && ! -L $input && -r $input ]]; then
        input_size=$(stat -c %s -- "$input")
        if (( input_size <= 104857600 )); then
            check /usr/bin/timeout 20 sha256sum -- "$input"
        else
            printf 'INPUT_TOO_LARGE=%s\n' "$input"
        fi
    fi
done
printf 'LICENSE_CHECKOUT=NOT_TESTED\n'
printf 'COMPUTE_PERMISSION=UNVERIFIED\n'
printf 'POWER=NOT_RUN\n'
printf 'PREFLIGHT_COMPLETE_REVIEW_REQUIRED\n'
