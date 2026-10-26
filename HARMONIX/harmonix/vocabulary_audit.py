"""Reference-only diagnostic audit; does not alter frozen EMH or intervention ranking."""
import argparse
import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from .emh_bridge import VENDOR
from .baseline import verify_snapshot
from .shared_data import require_hooktheory


def classify(root, intervals):
    """Descriptive pitch-class quality, not a chord-symbol transcription."""
    pcs = {0}
    n = 0
    for step in intervals:
        n = (n + int(step)) % 12
        pcs.add(n)
    signatures = {
        frozenset((0,4,7)): 'major_triad',
        frozenset((0,3,7)): 'minor_triad',
        frozenset((0,3,6)): 'diminished_triad',
        frozenset((0,4,8)): 'augmented_triad',
        frozenset((0,2,7)): 'sus2',
        frozenset((0,5,7)): 'sus4',
        frozenset((0,4,7,9)): 'major_sixth',
        frozenset((0,3,7,9)): 'minor_sixth',
        frozenset((0,4,7,10)): 'dominant_seventh',
        frozenset((0,4,7,11)): 'major_seventh',
        frozenset((0,3,7,10)): 'minor_seventh',
        frozenset((0,3,6,10)): 'half_diminished_seventh',
        frozenset((0,3,6,9)): 'diminished_seventh',
        frozenset((0,3,7,11)): 'minor_major_seventh',
    }
    quality = signatures.get(frozenset(pcs))
    if quality is None:
        if len(pcs) >= 5:
            quality = 'extended_or_complex'
        elif len(pcs) == 4:
            quality = 'other_four_note'
        elif len(pcs) == 3:
            quality = 'other_triad'
        else:
            quality = 'other_or_incomplete'
    return quality, sorted(pcs)


def audit_record(record):
    """Convert worker observations to stable rows without inferring unknown roots."""
    rows = record['audit_rows']
    for row in rows:
        if row['status'] == 'out_of_vocabulary':
            if row['root_match_any']:
                row['diagnosis'] = 'root_present_but_pitch_classes_differ'
            elif row['pitch_class_match_any']:
                row['diagnosis'] = 'pitch_classes_present_but_root_differs'
            else:
                row['diagnosis'] = 'neither_exact_root_nor_pitch_classes'
        elif row['status'] == 'covered':
            row['diagnosis'] = 'covered'
        else:
            row['diagnosis'] = row['status']
    return rows


def summarize(rows, failures):
    by_status = Counter(r['status'] for r in rows)
    uncovered = [r for r in rows if r['status'] == 'out_of_vocabulary']
    return {
        'n_segments': len(rows),
        'n_worker_failures': len(failures),
        'status_counts': dict(sorted(by_status.items())),
        'out_of_vocabulary_by_quality': dict(sorted(Counter(r['quality'] for r in uncovered).items())),
        'out_of_vocabulary_by_diagnosis': dict(sorted(Counter(r['diagnosis'] for r in uncovered).items())),
        'warning': ('Descriptive audit on reference annotations only. Pitch-class sets cannot establish '
                    'voicing, inversions, omitted tones or musical quality. No harmonizer or oracle '
                    'intervention parameters are changed. Do not tune on TEST and then claim unbiased TEST performance.'),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', required=True)
    parser.add_argument('--output-prefix', default='results/vocabulary_audit')
    parser.add_argument('--limit', type=int, default=20)
    args = parser.parse_args()
    verify_snapshot()
    archive = require_hooktheory()
    selection = json.loads(Path(args.selection).read_text(encoding='utf8'))
    if selection.get('split') != 'TEST':
        raise ValueError('Only the original TEST selection is supported for this diagnostic audit')
    rows, failures = [], []
    worker = Path(__file__).with_name('_vocabulary_audit_worker.py')
    for item in selection['selected'][:args.limit]:
        ident = item['id']
        proc = subprocess.run([sys.executable, str(worker), str(archive), ident],
                              cwd=VENDOR, capture_output=True, text=True)
        if proc.returncode:
            failures.append({'id': ident, 'error': proc.stderr[-2000:] or proc.stdout[-2000:]})
            print(f'{ident}: ERROR', flush=True)
            continue
        try:
            record = json.loads(proc.stdout)
            rows.extend(audit_record(record))
            print(f'{ident}: {len(record["audit_rows"])} segments', flush=True)
        except Exception as exc:
            failures.append({'id': ident, 'error': f'{type(exc).__name__}: {exc}; stdout={proc.stdout[-500:]}'})
    summary = summarize(rows, failures)
    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    output_json = prefix.with_suffix('.json')
    output_csv = prefix.with_suffix('.csv')
    output_json.write_text(json.dumps({'summary': summary, 'failures': failures, 'segments': rows},
                                      indent=2, ensure_ascii=False)+'\n', encoding='utf8')
    fields = ['id','segment_index','measure','start_beat','status','diagnosis','quality',
              'root_pitch_class','intervals','relative_pitch_classes',
              'root_match_any','pitch_class_match_any','candidate_count']
    with output_csv.open('w', encoding='utf8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            r = dict(row)
            for key in ('intervals','relative_pitch_classes'):
                r[key] = json.dumps(r.get(key))
            writer.writerow(r)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print('Reports:', output_json, output_csv)
    if failures:
        print('NOTE: inspect failures in JSON; no failures were silently discarded.')


if __name__ == '__main__':
    main()
