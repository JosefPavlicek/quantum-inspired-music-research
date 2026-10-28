"""QHDE prototype v0.1: NumPy exact simulation; DOES NOT call IBM hardware.
Two harmonic positions, four chords per position, 4 qubits and 16 combinations.
Scores are ILLUSTRATIVE, not validated EMH scores. Higher score is better.
"""
import csv
import json
from pathlib import Path
import numpy as np

CHORDS = ('Cmaj7', 'Dm7', 'G7', 'A7')
# Demonstration-only chord and transition scores (not from EMH).
MELODY_A = {'Cmaj7': 1.0, 'Dm7': 0.8, 'G7': 0.4, 'A7': 0.3}
MELODY_B = {'Cmaj7': 0.9, 'Dm7': 0.5, 'G7': 0.6, 'A7': 0.3}
TRANSITIONS = {('G7', 'Cmaj7'): 1.4, ('A7', 'Dm7'): 1.2,
               ('Dm7', 'G7'): 1.0, ('Cmaj7', 'G7'): 0.6}


def score(a, b):
    return MELODY_A[a] + MELODY_B[b] + TRANSITIONS.get((a, b), 0.0)


def cases():
    # State index: low 2 bits = chord A, high 2 bits = chord B.
    return [(idx, CHORDS[idx % 4], CHORDS[idx // 4],
             score(CHORDS[idx % 4], CHORDS[idx // 4])) for idx in range(16)]


def rx_all(state, beta, n=4):
    # exp(-i beta X) on each qubit: QAOA transverse-field mixer.
    c, s = np.cos(beta), -1j * np.sin(beta)
    state = state.copy()
    for q in range(n):
        stride = 1 << q
        for start in range(0, len(state), 2 * stride):
            lo = slice(start, start + stride)
            hi = slice(start + stride, start + 2 * stride)
            a, b = state[lo].copy(), state[hi].copy()
            state[lo] = c * a + s * b
            state[hi] = s * a + c * b
    return state


def qaoa(gamma, beta, energies):
    state = np.ones(16, dtype=complex) / 4.0
    # Diagonal cost phase followed by noncommuting mixing (interference).
    state *= np.exp(-1j * gamma * energies)
    return rx_all(state, beta)


def run():
    rows = cases()
    scores = np.array([r[3] for r in rows])
    # E = -score; minimize expected energy / maximize expected score.
    energies = -scores
    best = float(max(scores))
    mask = np.isclose(scores, best)
    initial = np.full(16, 1/16)
    best_config = None
    # Exhaustive two-parameter grid is deterministic and reproducible.
    for gamma in np.linspace(0, np.pi, 51):
        for beta in np.linspace(0, np.pi, 51):
            probs = np.abs(qaoa(gamma, beta, energies)) ** 2
            mean = float(probs @ scores)
            if best_config is None or mean > best_config[0]:
                best_config = (mean, float(gamma), float(beta), probs)
    mean, gamma, beta, probs = best_config
    out = Path(__file__).resolve().parent / 'results'
    out.mkdir(exist_ok=True)
    with (out / 'harmonic_candidates.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['state', 'chord_A', 'chord_B', 'illustrative_score',
                         'uniform_probability', 'qaoa_probability'])
        for i, a, b, sc in rows:
            writer.writerow([format(i, '04b'), a, b, sc, initial[i], float(probs[i])])
    summary = {
        'version': 'QHDE-prototype-0.1', 'simulation_only': True,
        'note': 'Illustrative rule weights; NOT corrected EMH scores or empirical music preferences.',
        'qubits': 4, 'candidate_pairs': 16, 'qaoa_depth_p': 1,
        'best_gamma': gamma, 'best_beta': beta,
        'uniform_expected_score': float(initial @ scores),
        'qaoa_expected_score': mean,
        'exact_optimum_score': best,
        'uniform_optimum_probability': float(sum(initial[mask])),
        'qaoa_optimum_probability': float(sum(probs[mask])),
        'optimal_pairs': [{'a': a, 'b': b, 'score': sc} for _, a, b, sc in rows if np.isclose(sc, best)]
    }
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print('Saved results/summary.json and results/harmonic_candidates.csv')


if __name__ == '__main__':
    run()
