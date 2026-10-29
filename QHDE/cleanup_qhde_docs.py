#!/usr/bin/env python3
"""Consolidate QHDE transient installation notes into one README.

Dry run by default. No files other than known transient .md docs are deleted.
Git commit is opt-in; git push is never automatic.
"""
import argparse
import re
import subprocess
from pathlib import Path

DOC_PATTERN = re.compile(r"(?i)^(?:README[_-]V\d+(?:[_-].*)?|README[_-](?:CLEANUP|INSTALL)(?:[_-].*)?|INSTALL(?:ATION)?(?:[_-].*)?)\.md$")
MARKER = '<!-- QHDE-CONSOLIDATED-2026-10 -->'
SECTION = '''\n\n'''+MARKER+'''
## Research status (QHDE v0.12–v0.26)

QHDE studies quantum approximate optimization for **harmonic decision sequences** derived from the **corrected EMH** inside HARMONIX. The published standalone EMH is a frozen reproducibility baseline and must not be changed.

- **v0.19:** 4-qubit, two-segment IBM Pittsburgh benchmark, 16 instances, 16 states each. Hardware mean optimum probabilities: uniform 10.25%, p=1 33.33%, p=2 42.70%, p=3 51.10%.
- **v0.21:** Independent hardware replication on Pittsburgh. Hardware means: uniform 9.81%, p=1 34.23%, p=2 43.52%, p=3 52.46%. Reproduction does not imply quantum advantage.
- **v0.22:** Constructed 16 four-segment, 8-qubit problems (four candidates per segment; 256 states); 16/16 succeeded.
- **v0.23:** Exact Pauli-Z decomposition audit. 12/16 Hamiltonians are neighbor-local; 4/16 require higher-order/nonlocal penalty terms. The original 8-qubit cost model must remain exact; do not discard constraints to reduce circuit depth without changing the declared problem.
- **v0.24:** Optimized QAOA p=1,2,3 for all 16 in ideal simulation, preparing 36 logical circuits for the 12 local problems.
- **v0.25:** IBM Marrakesh job `dbh8j5kdgr2s73ct1100`, 48 circuits × 1,024 shots, 8 qubits, 12 local instances, charge 16 s of QPU time. Hardware mean optimum probabilities: uniform 1.204%, p=1 6.681%, p=2 10.343%, p=3 12.492%. Ideal means: 1.237%, 9.914%, 19.116%, 28.166%.
- **v0.26:** Offline hardware/ideal gap audit from v0.25. Mean hardware-to-ideal loss increases with QAOA depth. Paired p=3 vs p=2 hardware gain +2.15 percentage points (9 positive, 2 negative, 1 tied among 12). Instance-level statistical dependence and device drift remain open caveats.

### Reproducibility and important limitations

- The optimum is defined by the **modeled corrected-EMH scoring function**, not by a human-listener preference study.
- The 256-state optimization problem is easy to enumerate classically; **no quantum computational advantage** has been demonstrated.
- Some records may share the same effective energy landscape; don't assume all song records are independent optimization instances.
- Logical circuit gate counts differ from backend-transpiled physical circuit counts. Use the saved `preparation.json`/QPY and backend details for device costs.
- Store job IDs, raw result data, optimized parameters, instance manifests and test scripts in the repository; never commit IBM API credentials or the `qiskit-ibm.json` token file.

### Main entry points

From the repository root, with Python available at `HARMONIX/.venv/bin/python`:

```bash
HARMONIX/.venv/bin/python QHDE/qhde_four_segments_v22.py --limit 16
HARMONIX/.venv/bin/python QHDE/qhde_structured_qaoa_v23.py
HARMONIX/.venv/bin/python QHDE/qhde_optimize_v24.py --starts 12 --maxiter 200
HARMONIX/.venv/bin/python QHDE/qhde_ibm_v25.py --analyze
HARMONIX/.venv/bin/python QHDE/qhde_audit_v26.py
```

IBM submission is a separate, **explicitly confirmed** action. Do not resubmit existing jobs. The corresponding result artifacts live under `QHDE/results/`.
'''

def cmd(*args, cwd=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='Apply changes (default: preview)')
    ap.add_argument('--commit', action='store_true', help='Commit QHDE changes; requires --apply')
    a=ap.parse_args()
    if a.commit and not a.apply: ap.error('--commit requires --apply')
    repo=Path.cwd().resolve()
    try: top=Path(cmd('git','rev-parse','--show-toplevel',cwd=repo)).resolve()
    except (subprocess.CalledProcessError, OSError): ap.error('Run from GitHub Codespaces repository root')
    if top != repo: ap.error(f'Run from repository root: {top}')
    qhde=repo/'QHDE'
    if not qhde.is_dir(): ap.error('QHDE directory missing')
    candidates=sorted(p for p in qhde.glob('*.md') if DOC_PATTERN.fullmatch(p.name))
    mainreadme=qhde/'README.md'
    readme_exists=mainreadme.exists()
    print('Repository:', top)
    print('Main README:', 'preserve + append short research summary' if readme_exists else 'create')
    print('Transient markdown files to remove:', len(candidates))
    for p in candidates: print('  DELETE',p.relative_to(repo))
    print('Files to keep: all code, tests, .json, .csv, .qpy, and other research artifacts')
    if not a.apply:
        print('\nDRY RUN. No changes. Run with --apply to consolidate, then inspect git diff.')
        return
    old=mainreadme.read_text(encoding='utf-8') if readme_exists else '# QHDE — Quantum Harmonic Dependency Experiment\n'
    if MARKER not in old:
        mainreadme.write_text(old.rstrip()+SECTION+'\n',encoding='utf-8')
    for p in candidates: p.unlink()
    print('\nDONE. Preview changes with: git diff -- QHDE/README.md; git status --short')
    if a.commit:
        cmd('git','add','-A','--','QHDE',cwd=repo)
        staged=cmd('git','diff','--cached','--name-status',cwd=repo)
        print('\nSTAGED:\n'+staged)
        if not staged:
            print('Nothing to commit')
            return
        forbidden=['qiskit-ibm.json', '.env', 'token', 'credentials']
        staged_names=[line.split('\t')[-1] for line in staged.splitlines()]
        bad=[name for name in staged_names if any(f in name.lower() for f in forbidden)]
        if bad: raise SystemExit('ABORT: suspicious staged filenames: '+str(bad)+'; review and unstage')
        print('Committing QHDE changes (no automatic push)...')
        print(cmd('git','commit','-m','QHDE: preserve v0.26 experiments and consolidate documentation',cwd=repo))
        print('Push only after reviewing: git push origin main')

if __name__=='__main__': main()
