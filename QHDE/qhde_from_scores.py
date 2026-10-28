"""QHDE v0.2: score-table adapter; offline NumPy simulation only.
Run: python qhde_from_scores.py --input data/example_scores.json
Scores must be exported by a documented scoring model (EMH adapter pending).
"""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from qhde_simulator import rx_all


def read_problem(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    labels_a = data["chords_A"]
    labels_b = data["chords_B"]
    if not isinstance(labels_a, list) or not isinstance(labels_b, list):
        raise ValueError("chords_A and chords_B must be lists")
    if len(labels_a) != len(labels_b) or len(labels_a) < 2 or (len(labels_a) & (len(labels_a)-1)):
        raise ValueError("Both chord lists must have equal power-of-two size >= 2")
    n = len(labels_a)
    if len(set(labels_a)) != n or len(set(labels_b)) != n:
        raise ValueError("Each chord list must have unique entries")
    scores = np.asarray(data["pair_scores"], dtype=float)
    if scores.shape != (n, n) or not np.isfinite(scores).all():
        raise ValueError("pair_scores must be finite numeric n x n array, rows=A and columns=B")
    if data.get("source") in (None, ""):
        raise ValueError("Explicit provenance field 'source' is required")
    return data, labels_a, labels_b, scores


def simulate(path, outdir, grid=51):
    data, aa, bb, table = read_problem(path)
    n=len(aa); nq=2*int(np.log2(n)); size=n*n
    # Little endian encoding: index = A_index + n * B_index.
    score_vec=np.array([table[i % n, i // n] for i in range(size)], dtype=float)
    best=score_vec.max(); optimal=np.isclose(score_vec,best)
    uniform=np.full(size,1/size)
    best_run=None
    for gamma in np.linspace(0,np.pi,grid):
        for beta in np.linspace(0,np.pi,grid):
            psi=np.ones(size,dtype=complex)/np.sqrt(size)
            psi *= np.exp(1j*gamma*score_vec)  # energy=-score
            psi=rx_all(psi,beta,n=nq)
            probs=np.abs(psi)**2
            mean=float(probs @ score_vec)
            if best_run is None or mean>best_run[0]:
                best_run=(mean,float(gamma),float(beta),probs.copy())
    mean,gamma,beta,probs=best_run
    out=Path(outdir); out.mkdir(parents=True,exist_ok=True)
    with (out/'candidates.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['state','chord_A','chord_B','score','uniform_probability','qaoa_probability','is_optimal'])
        for i in range(size):
            w.writerow([format(i,f'0{nq}b'),aa[i%n],bb[i//n],float(score_vec[i]),float(uniform[i]),float(probs[i]),bool(optimal[i])])
    summary={'version':'QHDE-v0.2-score-interface','simulation_only':True,'source':data['source'],
        'source_input':str(path),'score_provenance_note':data.get('note',''),
        'n_qubits':nq,'candidate_pairs':size,'depth':1,'grid_points_per_parameter':grid,
        'best_gamma':gamma,'best_beta':beta,'uniform_expected_score':float(uniform@score_vec),
        'qaoa_expected_score':mean,'exact_optimum_score':float(best),
        'uniform_optimum_probability':float(uniform[optimal].sum()),
        'qaoa_optimum_probability':float(probs[optimal].sum()),
        'optimal_pairs':[{'chord_A':aa[i%n],'chord_B':bb[i//n]} for i in range(size) if optimal[i]]}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',required=True)
    p.add_argument('--out',default='results/v02');p.add_argument('--grid',type=int,default=51)
    a=p.parse_args()
    if a.grid<2: p.error('--grid must be >= 2')
    print(json.dumps(simulate(a.input,a.out,a.grid),ensure_ascii=False,indent=2))
