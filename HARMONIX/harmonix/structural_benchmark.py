"""Reference-blind four-arm structural benchmark (exploratory TRAIN/VALID).

Uses the same corrected HARMONIX chord candidates and frozen EMH scoring in
all arms. Human reference is loaded ONLY after all four paths are computed.
"""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import sys
import time

ARMS = {'corrected': (0.0, 0.0), 'repetition': (0.12, 0.0),
        'function': (0.0, 0.06), 'combined': (0.12, 0.06)}


def _rates(evaluation, links):
    segments = evaluation['segments']
    valid = [s for s in segments if s['status'] == 'evaluated']
    def avg(values):
        return sum(values) / len(values) if values else None
    # Reference labels are never used in selecting links or generating paths.
    # A repeated-pair score measures matching BOTH reference chords, rather
    # than merely rewarding any generated repetition.
    pairs = [(segments[a], segments[b]) for a, b in links
             if a < len(segments) and b < len(segments)
             and segments[a]['status'] == segments[b]['status'] == 'evaluated']
    transitions = [(a, b) for a, b in zip(segments, segments[1:])
                   if a['status'] == b['status'] == 'evaluated']
    return {
        'n_evaluated': len(valid), 'n_repetition_links_evaluable': len(pairs),
        'n_transitions_evaluable': len(transitions),
        'chord_agreement': avg([s['chord_agreement'] for s in valid]),
        'root_agreement': avg([s['root_agreement'] for s in valid]),
        'function_agreement': avg([s['function_agreement'] for s in valid
                                   if s['function_agreement'] is not None]),
        'exact_chord_transition': avg([a['chord_agreement'] and b['chord_agreement']
                                       for a, b in transitions]),
        'repeated_pair_both_correct': avg([a['chord_agreement'] and b['chord_agreement']
                                           for a, b in pairs]),
        'repeated_pair_reference_relation': avg([
            (a['human_root_pc'] == b['human_root_pc']) ==
            (a['generated_root_pc'] == b['generated_root_pc']) for a, b in pairs]),
    }


def _initialize():
    from .baseline import verify_snapshot
    from .emh_bridge import VENDOR
    from .shared_data import require_hooktheory
    verify_snapshot()
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / 'Explainable_Melody_Harmonizer'))
    sys.path.insert(0, str(VENDOR))
    from hooktheory.loader import melody_only, reference_only
    from hooktheory.adapter import adapt
    from hooktheory.evaluator import evaluate
    from emh.key_detection import detect_key
    from emh.segmentation import segment_notes
    from emh.model import ChordCandidate, Decision, ScoreComponents
    from emh.optimizer import optimize
    from .knowledge_candidates import generate as knowledge_generate
    from .structural_decisions import optimize_structural, structural_links
    from music21.key import Key
    import yaml
    config = yaml.safe_load((VENDOR / 'config.yaml').read_text(encoding='utf8'))
    return locals()


def _run_record(record, env, weights, iterations, pair_diagnostics=False):
    try:
        # Generation-facing record intentionally strips ALL harmony annotations.
        melody = env['adapt'](env['melody_only'](record))
        key = env['detect_key'](melody.notes)
        segments = env['segment_notes'](melody.notes, melody.time_signatures, env['config'])
        candidates = [env['ChordCandidate'](c.symbol, c.roman, c.pitch_classes, c.function)
                      for c in env['knowledge_generate'](key.tonic, key.mode, 'corrected')]
        scale = {p.pitchClass for p in env['Key'](key.tonic, key.mode).pitches}
        baseline = env['optimize'](segments, candidates, scale, env['config'])
        if not baseline or len(baseline) != len(segments):
            raise ValueError('Invalid baseline decisions')
        generated = {'corrected': baseline}
        explanations = {}
        for arm in ('repetition', 'function', 'combined'):
            rw, fw = weights[arm]
            path, explanation = env['optimize_structural'](
                segments, candidates, scale, env['config'],
                repetition_weight=rw, transition_weight=fw, iterations=iterations)
            if len(path) != len(segments):
                raise ValueError('Invalid structural decisions')
            generated[arm] = [env['Decision'](seg, chord, env['ScoreComponents'](), [])
                              for seg, chord in zip(segments, path)]
            explanations[arm] = {'objective': explanation['objective'],
                                 'baseline_objective': explanation['baseline_objective']}
        # IMPORTANT: reference first becomes accessible after ALL arms are generated.
        reference = env['reference_only'](record)
        meters = record['annotations']['meters']
        if not meters:
            raise ValueError('Missing reference meter')
        meter = meters[0]
        links = env['structural_links'](segments)
        scores = {arm: _rates(env['evaluate'](decisions, reference, meter, candidates), links)
                  for arm, decisions in generated.items()}
        diagnostic = None
        if pair_diagnostics:
            # Reference is consulted only AFTER all paths have been generated.
            evaluations = {arm: env['evaluate'](decisions, reference, meter, candidates)['segments']
                           for arm, decisions in generated.items()}
            # v0.19 diagnostics: distinguish absolute-pitch repetition from
            # transposition of the relative melodic signature. This information
            # is calculated AFTER generation, and never enters path selection.
            diagnostic = {'n_links_total': len(links), 'strata': {},
                          'transposition_strata': {}}
            transposition_names = (
                'untransposed_same_reference_root',
                'untransposed_changed_reference_root',
                'transposed_reference_tracks_melody',
                'transposed_reference_not_tracking_melody')
            for name in transposition_names:
                diagnostic['transposition_strata'][name] = {'n_pairs': 0, 'arms': {
                    arm: {'relation_correct': 0, 'both_chords_correct': 0,
                          'generated_same_root': 0, 'generated_tracks_melody': 0,
                          'generated_matches_reference_interval': 0}
                    for arm in generated}}
            for stratum in ('same_reference_root', 'changed_reference_root'):
                diagnostic['strata'][stratum] = {'n_pairs': 0, 'arms': {
                    arm: {'relation_correct': 0, 'both_chords_correct': 0,
                          'generated_same_root': 0} for arm in generated}}
            for a, b in links:
                baseline_segments = evaluations['corrected']
                if a >= len(baseline_segments) or b >= len(baseline_segments):
                    continue
                left, right = baseline_segments[a], baseline_segments[b]
                if left['status'] != 'evaluated' or right['status'] != 'evaluated':
                    continue
                same_reference = left['human_root_pc'] == right['human_root_pc']
                stratum = 'same_reference_root' if same_reference else 'changed_reference_root'
                bucket = diagnostic['strata'][stratum]
                bucket['n_pairs'] += 1
                def first_pc(segment):
                    return next((int(n.pitch_class) % 12 for n in segment.notes
                                 if not n.is_rest and n.pitch_class is not None), None)
                pa, pb = first_pc(segments[a]), first_pc(segments[b])
                if pa is None or pb is None:
                    continue
                melody_shift = (pb - pa) % 12
                reference_shift = (right['human_root_pc'] - left['human_root_pc']) % 12
                if melody_shift == 0:
                    name = ('untransposed_same_reference_root' if reference_shift == 0
                            else 'untransposed_changed_reference_root')
                else:
                    name = ('transposed_reference_tracks_melody'
                            if reference_shift == melody_shift
                            else 'transposed_reference_not_tracking_melody')
                t_bucket = diagnostic['transposition_strata'][name]
                t_bucket['n_pairs'] += 1
                for arm, evaluated in evaluations.items():
                    x, y = evaluated[a], evaluated[b]
                    generated_same = x['generated_root_pc'] == y['generated_root_pc']
                    bucket['arms'][arm]['relation_correct'] += int(generated_same == same_reference)
                    bucket['arms'][arm]['both_chords_correct'] += int(bool(x['chord_agreement'] and y['chord_agreement']))
                    bucket['arms'][arm]['generated_same_root'] += int(generated_same)
                    generated_shift = (y['generated_root_pc'] - x['generated_root_pc']) % 12
                    target = t_bucket['arms'][arm]
                    target['relation_correct'] += int(generated_same == same_reference)
                    target['both_chords_correct'] += int(bool(x['chord_agreement'] and y['chord_agreement']))
                    target['generated_same_root'] += int(generated_same)
                    target['generated_tracks_melody'] += int(generated_shift == melody_shift)
                    target['generated_matches_reference_interval'] += int(generated_shift == reference_shift)
        return {'status': 'ok', 'n_segments': len(segments), 'n_links': len(links),
                **({'pair_diagnostics': diagnostic} if pair_diagnostics else {}),
                'n_candidates': len(candidates), 'scores': scores,
                'structural_objectives': explanations}
    except Exception as exc:
        return {'status': 'failed', 'reason': type(exc).__name__ + ': ' + str(exc)[:300]}


def _summary(rows, total):
    counts = Counter(r['status'] for r in rows)
    metrics = ('chord_agreement', 'root_agreement', 'function_agreement',
               'exact_chord_transition', 'repeated_pair_both_correct',
               'repeated_pair_reference_relation')
    per_arm = {}
    for arm in ARMS:
        per_arm[arm] = {}
        for metric in metrics:
            values = [r['scores'][arm][metric] for r in rows
                      if r['status'] == 'ok' and r['scores'][arm][metric] is not None]
            per_arm[arm][metric] = {'n_records': len(values),
                                    'mean_per_record': sum(values) / len(values) if values else None}
    return {'requested': total, 'processed': len(rows), 'status_counts': dict(counts),
            'failure_reasons': dict(Counter(r.get('reason') for r in rows if r['status'] != 'ok')),
            'arms': per_arm, 'caution': 'Exploratory unweighted record means; not group-clustered confidence intervals or confirmatory results.'}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--summary', required=True)
    p.add_argument('--archive')
    p.add_argument('--limit', type=int, default=50, help='0 = entire manifest')
    p.add_argument('--iterations', type=int, default=4)
    p.add_argument('--progress-every', type=int, default=25)
    p.add_argument('--allow-exploratory-test', action='store_true')
    args = p.parse_args(argv)
    if args.limit < 0 or args.iterations < 1 or args.progress_every < 1:
        p.error('Invalid numerical parameter')
    manifest = json.loads(Path(args.manifest).read_text(encoding='utf8'))
    if manifest.get('preflight_only') is not True or manifest.get('split') not in ('TRAIN', 'VALID', 'TEST'):
        p.error('Expected audited preflight TRAIN/VALID/TEST manifest')
    if manifest['split'] == 'TEST' and not args.allow_exploratory_test:
        p.error('Previously inspected TEST is exploratory; supply --allow-exploratory-test')
    ids = [r['id'] for r in manifest['selected']]
    if len(ids) != len(set(ids)):
        p.error('Duplicate manifest IDs')
    if args.limit:
        ids = ids[:args.limit]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Avoid silently mixing variants or old outputs. Explicit resume is supported
    # for exactly the same IDs and settings; settings stored in a sidecar.
    settings = {'split': manifest['split'], 'ids': ids, 'weights': ARMS,
                'iterations': args.iterations, 'model': 'harmonix_structural_v0.15'}
    sidecar = output.with_suffix(output.suffix + '.settings.json')
    if sidecar.exists():
        if json.loads(sidecar.read_text(encoding='utf8')) != json.loads(json.dumps(settings)):
            raise ValueError('Resume settings mismatch; use a new output file')
    elif output.exists() and output.stat().st_size:
        raise ValueError('Existing output without matching settings sidecar; use new output')
    else:
        sidecar.write_text(json.dumps(settings, ensure_ascii=False), encoding='utf8')
    previous = {}
    if output.exists():
        for line in output.read_text(encoding='utf8').splitlines():
            if line.strip():
                row = json.loads(line)
                if row['id'] in previous or row['id'] not in ids:
                    raise ValueError('Duplicate or unexpected ID in prior output')
                previous[row['id']] = row
    env = _initialize()
    archive = Path(args.archive) if args.archive else env['require_hooktheory']()
    with gzip.open(archive, 'rt', encoding='utf8') as stream:
        dataset = json.load(stream)
    start = time.monotonic()
    with output.open('a', encoding='utf8') as stream:
        for index, ident in enumerate(ids, 1):
            if ident not in previous:
                result = (_run_record(dataset[ident], env, ARMS, args.iterations)
                          if ident in dataset else {'status': 'failed', 'reason': 'Missing record'})
                row = {'id': ident, 'split': manifest['split'], **result}
                stream.write(json.dumps(row, ensure_ascii=False) + '\n')
                stream.flush()
                previous[ident] = row
            if index % args.progress_every == 0:
                print(f'{index}/{len(ids)}; elapsed {time.monotonic()-start:.1f}s', flush=True)
    report = {'split': manifest['split'], 'model': 'harmonix_structural_v0.15',
              'parameters': {'weights': ARMS, 'iterations': args.iterations},
              'summary': _summary([previous[i] for i in ids], len(ids))}
    dest = Path(args.summary)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
