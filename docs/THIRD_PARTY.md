# Third-party scaffolding

Claude Code's official `rat-init-project` skill deploys project guides, Claude rules, a filelist, Makefiles, simulation/regression wrappers, lint/CDC wrappers, synthesis/equivalence wrappers, and a shared tool-runner library from [RTL Agent Team](https://github.com/babyworm/rtl-agent-team).

Source used during this setup: version `0.14.6`, marketplace revision `56c02875d77bd7b6d44fe9c5acd27d7d03f34b12`. The upstream MIT license is retained in [RTL_AGENT_TEAM_LICENSE.txt](RTL_AGENT_TEAM_LICENSE.txt). This attribution does not select a license for the original project work.

Imported scripts are generic scaffolding and have not been validated with scheduler RTL or university commercial EDA tools. Project-specific environment auditing and remote FastX orchestration live in `scripts/check_environment.py`, `scripts/remote_eda.py`, `scripts/remote_entry.sh`, `syn/dc.tcl`, and `sta/pt.tcl`. Their local checks are distinct from actual synthesis or STA runs.
