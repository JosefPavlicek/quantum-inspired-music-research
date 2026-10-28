"""QHDE v0.5: exact NumPy statevector QAOA simulation from HookTheory exports.

No Qiskit dependency, no backend calls, no classical optimizer superiority claim.
"""
import argparse
import json
import math
from pathlib import Path
import numpy as np

N_QUBITS = 7
DIM = 1 << N_QUBITS


def load_problem(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    pairs = data['pairs']
    if not pairs or data.get('candidate_variant') != 'corrected':
        raise ValueError('Expected nonempty corrected HARMONIX candidate pairs')
    n = data['candidate_count']
    if n != 10:
        raise ValueError('This study requires 10 corrected candidates per position')
    scores = np.full(DIM, np.nan, dtype=float)
    seen = set()
    for row in pairs:
        i, j = int(row['a_index']), int(row['b_index'])
        if not (0 <= i < n and 0 <= j < n):
            raise ValueError('Invalid candidate indices')
        k = n*i+j
        if k in seen:
            raise ValueError('Duplicate pair index')
        seen.add(k)
        scores[k] = float(row['score'])
    if not np.all(np.isfinite(scores[:n*n])) or len(seen) != n*n:
        raise ValueError('Missing, nonfinite or duplicated corrected pair scores')
    return data, scores


def energies_from_scores(scores, invalid_penalty=2.0):
    """Minimize E = -(score-min)/(max-min); invalid states have positive penalty."""
    valid = scores[:100]
    span = float(np.ptp(valid))
    if span < 1e-12:
        raise ValueError('Degenerate scores: all pairs tied')
    energies = np.full(DIM, float(invalid_penalty))
    energies[:100] = -(valid - min(valid)) / span
    return energies


def rx_mixer(state, beta):
    """Product of Rx(2 beta) gates on 7 qubits; correct qubit ordering."""
    x = state.copy()
    c, s = np.cos(beta), -1j*np.sin(beta)
    for q in range(N_QUBITS):
        block = 1 << q
        a = x.reshape(-1, 2*block)
        lo = a[:, :block].copy()
        hi = a[:, block:].copy()
        a[:, :block] = c*lo + s*hi
        a[:, block:] = s*lo + c*hi
    return x


def statevector(energy, params):
    p = len(params)//2
    state = np.full(DIM, 1 / math.sqrt(DIM), dtype=np.complex128)
    for layer in range(p):
        gamma, beta = params[2*layer:2*layer+2]
        state *= np.exp(-1j*gamma*energy)
        state = rx_mixer(state, beta)
    return state


def optimize(energy, depth, seed=42, trials=72, refine=2):
    """Predeclared reproducible classical random starts + coordinate refinement.

    Limited optimizer budget. No claim of global variational parameter optimum.
    """
    rng = np.random.default_rng(seed)
    shape = 2*depth
    best = None
    best_value = -np.inf

    def objective(params):
        probs = np.abs(statevector(energy, params))**2
        return -float(probs @ energy) # maximize normalized score incl. invalid penalty

    starts = [np.zeros(shape)]
    starts += [rng.uniform(0, np.pi, size=shape) for _ in range(trials)]
    for cand in starts:
        val = objective(cand)
        if val > best_value:
            best, best_value = cand.copy(), val
    for step in [0.4, 0.12][:refine]:
        changed = True
        iteration = 0
        while changed and iteration < 5:
            changed = False
            iteration += 1
            for axis in range(shape):
                for direction in (-1, 1):
                    attempt = best.copy()
                    attempt[axis] = (attempt[axis]+direction*step) % (2*np.pi)
                    val = objective(attempt)
                    if val > best_value + 1e-12:
                        best, best_value, changed = attempt, val, True
    return best, best_value


def separable_approximation(energy):
    """No-entangling control: fit cost by sum of independent bit terms.

    This changes the objective approximation and is NOT a matched expressivity ablation.
    """
    bits = ((np.arange(DIM)[:, None] >> np.arange(N_QUBITS)) & 1).astype(float)
    x = np.column_stack((np.ones(DIM), bits))
    coeff = np.linalg.lstsq(x, energy, rcond=None)[0]
    return x @ coeff


def metrics(probs, scores):
    valid_p = float(probs[:100].sum())
    best_score = float(np.max(scores[:100]))
    optimal = np.flatnonzero(np.isclose(scores[:100], best_score, atol=1e-10, rtol=0))
    top10 = np.argsort(-scores[:100], kind='stable')[:10]
    return {
        'valid_probability': valid_p,
        'invalid_probability': float(1-valid_p),
        'optimum_probability_unconditional': float(probs[optimal].sum()),
        'optimum_probability_given_valid': float(probs[optimal].sum()/valid_p) if valid_p else None,
        'top10_probability_given_valid': float(probs[top10].sum()/valid_p) if valid_p else None,
        'expected_score_given_valid': float(probs[:100] @ scores[:100] / valid_p) if valid_p else None,
    }


def run_one(path, trials, seed):
    src, scores = load_problem(path)
    energy = energies_from_scores(scores)
    optimum = float(scores[:100].max())
    optimum_idx = np.flatnonzero(np.isclose(scores[:100], optimum, atol=1e-10, rtol=0))
    uniform_valid = np.concatenate([np.full(100, .01), np.zeros(28)])
    uniform_full = np.full(DIM, 1/DIM)
    out = {
        'source': str(path), 'record_id': src.get('record_id'),
        'n_qubits': N_QUBITS, 'n_valid': 100, 'n_invalid': 28,
        'score_source': src.get('model'), 'cadence_final': src.get('second_segment_is_final'),
        'classical_optimum': optimum,
        'optimal_pairs': [{'a': src['pairs'][int(k)]['a'], 'b': src['pairs'][int(k)]['b'], 'index': int(k)} for k in optimum_idx],
        'baselines': {'uniform_valid': metrics(uniform_valid,scores), 'uniform_all_128': metrics(uniform_full,scores)},
        'models': {}
    }
    for depth in (1,2):
        for name, e in [('full', energy), ('separable_cost_control', separable_approximation(energy))]:
            params, obj = optimize(e, depth, seed=seed+depth*101, trials=trials)
            prob = np.abs(statevector(e, params))**2
            out['models'][f'qaoa_p{depth}_{name}'] = {
                'params': [float(x) for x in params],
                'trained_objective': obj,
                'metrics': metrics(prob, scores),
                'note': 'Ideal statevector; classical parameter search. Separable control changes phase-cost model.' if name != 'full' else 'Ideal statevector; classical parameter search.'
            }
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input-dir', default='QHDE/results/hooktheory_v04')
    ap.add_argument('--out', default='QHDE/results/qaoa_v05')
    ap.add_argument('--limit', type=int, default=5)
    ap.add_argument('--trials', type=int, default=72)
    ap.add_argument('--seed', type=int, default=42)
    args = ap.parse_args()
    paths = sorted(Path(args.input_dir).glob('scores_*.json'))[:args.limit]
    if not paths:
        ap.error('No scores_*.json files found in input directory')
    dest = Path(args.out)
    dest.mkdir(parents=True, exist_ok=True)
    all_rows=[]
    for i, path in enumerate(paths):
        result = run_one(path,args.trials,args.seed+i*1000)
        (dest/f'result_{i:03d}.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
        all_rows.append(result)
        base = result['baselines']['uniform_valid']['optimum_probability_given_valid']
        q1 = result['models']['qaoa_p1_full']['metrics']['optimum_probability_given_valid']
        q2 = result['models']['qaoa_p2_full']['metrics']['optimum_probability_given_valid']
        print(f'{path.name}: optimum={result["classical_optimum"]:.5f} baseline={base:.2%} p1={q1:.2%} p2={q2:.2%}')
    summary = {'version':'QHDE-v0.5','simulation_only':True,'n_records':len(all_rows),
               'notes':['No hardware was called.','No quantum advantage is claimed.',
                        'Invalid indices 100..127 have positive energy penalty.',
                        'Separable cost is a diagnostic control, not a matched gate ablation.'],
               'records':all_rows}
    (dest/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print('Saved',dest/'summary.json')

if __name__ == '__main__':
    main()
