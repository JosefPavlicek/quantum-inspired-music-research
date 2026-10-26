"""Compare frozen EMH vs independent candidate variants on fixed HookTheory excerpts.

Exploratory TEST results are not an unbiased held-out confirmation.
"""
import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from .emh_bridge import VENDOR
from .baseline import verify_snapshot
from .shared_data import require_hooktheory

VARIANTS = ('baseline', 'corrected', 'extended')


def summarize(rows):
    good = [r for r in rows if r['status'] == 'ok']
    sums = {name: {'clean': 0, 'covered': 0, 'selected': 0, 'segments': 0}
            for name in VARIANTS}
    for row in good:
        for name in VARIANTS:
            for field in sums[name]:
                sums[name][field] += row['metrics'][name][field]
    for name in VARIANTS:
        entry = sums[name]
        entry['coverage_rate_clean'] = (entry['covered'] / entry['clean']) if entry['clean'] else None
        entry['selection_rate_clean'] = (entry['selected'] / entry['clean']) if entry['clean'] else None
    return {'n_requested': len(rows), 'n_evaluated': len(good),
            'n_failed': len(rows)-len(good), 'variants': sums,
            'warning': ('Descriptive fixed-corpus comparison; references consulted only post-generation. '
                        'Previously inspected TEST examples are exploratory, NOT an unbiased TEST confirmation. '
                        'Exact root and pitch-class agreement is not musical quality or intent preservation. '
                        'Candidate-count changes affect the optimization search space.')}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', required=True)
    parser.add_argument('--output', default='results/candidate_comparison.json')
    parser.add_argument('--limit', type=int, default=20)
    parser.add_argument('--allow-exploratory-test', action='store_true',
                        help='Explicitly acknowledge that previously inspected TEST is exploratory only')
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error('--limit must be positive')
    selection = json.loads(Path(args.selection).read_text(encoding='utf8'))
    split = selection.get('split')
    if split == 'TEST' and not args.allow_exploratory_test:
        parser.error('TEST was already inspected. Use --allow-exploratory-test for exploratory diagnostics only.')
    if split not in ('DEV', 'TRAIN', 'VALIDATION', 'TEST'):
        parser.error('Selection manifest must declare a recognized split')
    verify_snapshot()
    archive = require_hooktheory()
    worker = Path(__file__).with_name('_candidate_comparison_worker.py')
    rows = []
    for item in selection['selected'][:args.limit]:
        ident = item['id']
        proc = subprocess.run([sys.executable, str(worker), str(archive), ident],
                              cwd=VENDOR, capture_output=True, text=True)
        if proc.returncode:
            rows.append({'id': ident, 'status': 'failed',
                         'error': (proc.stderr or proc.stdout)[-1800:]})
        else:
            try:
                result = json.loads(proc.stdout)
                if result.get('split') != split:
                    raise ValueError(f'Manifest split {split} != record split {result.get("split")}')
                rows.append({'status': 'ok', **result})
            except Exception as exc:
                rows.append({'id': ident, 'status': 'failed', 'error': str(exc)})
        print(f'{ident}: {rows[-1]["status"]}', flush=True)
    report = {'split': split, 'exploratory': split == 'TEST',
              'summary': summarize(rows), 'songs': rows}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    print(json.dumps(report['summary'], indent=2, ensure_ascii=False))
    print('Report:', output)
    if report['summary']['n_failed']:
        print('WARNING: inspect failed records in JSON; no silent exclusions')


if __name__ == '__main__':
    main()
