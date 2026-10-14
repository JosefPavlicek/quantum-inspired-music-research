"""Read-only tonal-context audit; no changes to frozen EMH or generated results."""
import argparse
import gzip
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', default='data/hooktheory/Hooktheory.json.gz')
    p.add_argument('--selection', default='selection.json')
    p.add_argument('--results', default='results/hooktheory')
    args = p.parse_args()
    selected = json.loads(Path(args.selection).read_text(encoding='utf-8'))['selected']
    with gzip.open(args.dataset, 'rt', encoding='utf-8') as f:
        dataset = json.load(f)
    outdir = Path(args.results)
    rows = []
    for item in selected:
        ident = item['id']
        result_path = outdir / (ident + '.json')
        row = {'id': ident, 'artist': item.get('artist'), 'song': item.get('song')}
        if not result_path.exists():
            row['status'] = 'excluded_or_missing_result'
        else:
            result = json.loads(result_path.read_text(encoding='utf-8'))
            row['status'] = 'ok'
            row['emh_detected_key'] = result.get('detected_key')
        record = dataset.get(ident, {})
        annotations = record.get('annotations') or {}
        row['hooktheory_key_annotations'] = annotations.get('keys')
        rows.append(row)
    dest = outdir / 'key_audit_raw.json'
    dest.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    ok = [r for r in rows if r['status'] == 'ok']
    print('Processed cases:', len(ok))
    print('Excluded/missing:', len(rows) - len(ok))
    print('Reference key fields (first three cases):')
    for r in ok[:3]:
        print(json.dumps({'id':r['id'], 'emh_detected_key':r['emh_detected_key'],
                          'hooktheory_key_annotations':r['hooktheory_key_annotations']},
                         ensure_ascii=False, indent=2))
    print('Saved:', dest)
    print('NOTE: No match rate calculated until HookTheory key encoding is verified.')

if __name__ == '__main__':
    main()
