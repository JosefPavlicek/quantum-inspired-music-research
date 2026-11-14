#!/usr/bin/env python3
"""QHDE v0.33 final fixed-question analysis. No QPU actions; deterministic.

Read repository data from QHDE/results by default. ZIP input only as an optional
local archival verification route. Outputs reports under results/final_v33.
"""
import argparse,csv,io,json,zipfile,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline

MUSIC=['chord_entropy_bits','conditional_transition_entropy_bits','repeated_bigram_rate']
OPT=['feasible_fraction','log2_n_optimal','energy_gap','energy_sd']
LOCAL=['interaction_residual_rms','interaction_range','unary_margin_mean','transition_strength_rms']
MODELS={'mean':[], 'music':MUSIC,'optimization':OPT,'optimization_plus_music':OPT+MUSIC,
        'optimization_plus_local':OPT+LOCAL,'all':OPT+LOCAL+MUSIC}

def read_sources(instances,metrics):
    ip=Path(instances)
    if ip.is_dir():
        def get(name):return json.loads((ip/name).read_text())
    elif ip.suffix=='.zip':
        def get(name):
            with zipfile.ZipFile(ip) as z:return json.loads(z.read(name))
    else:raise ValueError('Instances must be directory or ZIP')
    manifest=get('manifest.json')
    mp=Path(metrics)
    if mp.suffix=='.zip':
        with zipfile.ZipFile(mp) as z: lines=z.read('metrics.csv').decode('utf-8')
    else:lines=mp.read_text()
    rows=list(csv.DictReader(io.StringIO(lines))); by={}
    for r in rows:
        key=(r['record_id'],int(r['depth']))
        if key in by:raise ValueError('duplicated metrics '+str(key))
        by[key]=r
    if len(rows)!=len(manifest['records'])*3:raise ValueError('Incomplete metrics')
    return manifest,get,by

def descriptors(instance):
    u=np.asarray(instance['unary_scores'],dtype=float)
    ts=np.asarray(instance['transition_scores'],dtype=float)
    if u.shape!=(4,4) or ts.shape!=(3,4,4):raise ValueError('unexpected factorization shape')
    # Two-way interaction after removal of unary-like row/column main effects.
    residual=ts-ts.mean(axis=2,keepdims=True)-ts.mean(axis=1,keepdims=True)+ts.mean(axis=(1,2),keepdims=True)
    strengths=ts-ts.mean(axis=(1,2),keepdims=True)
    unary_margin=np.sort(u,axis=1)[:,-1]-np.sort(u,axis=1)[:,-2]
    en=np.asarray(instance['energies_256'],dtype=float)
    idx=np.asarray([i for i in range(256) if i not in set(instance['invalid_indices'])],int)
    feasible=np.sort(en[idx]); optimum=feasible[0]
    second=next((x for x in feasible if x>optimum+1.e-9),optimum)
    return dict(interaction_residual_rms=float(np.sqrt(np.mean(residual**2))),
       interaction_range=float(np.max(residual)-np.min(residual)),
       unary_margin_mean=float(np.mean(unary_margin)),
       transition_strength_rms=float(np.sqrt(np.mean(strengths**2))),
       energy_gap=float(second-optimum), energy_sd=float(np.std(feasible)))

def build(manifest,get,by):
    result=[]; unique=set()
    for m in manifest['records']:
        rid=m['record_id']; d=get(m['file']);
        if d['record_id']!=rid or d['landscape_hash']!=m['landscape_hash']:raise ValueError('Data mismatch '+rid)
        item=dict(record_id=rid,stratum=m['stratum'],partition=m['partition'],
                  clean=bool(m.get('leakage_safe_validation',False)), landscape_hash=m['landscape_hash'])
        for f in MUSIC:item[f]=float(m[f])
        item.update(descriptors(d));item['feasible_fraction']=m['n_feasible']/256
        item['log2_n_optimal']=float(np.log2(m['n_optimal']))
        for p in (1,2,3):
            r=by[(rid,p)]
            if r['landscape_hash']!=m['landscape_hash']:raise ValueError('Metrics mismatch '+rid)
            item[f'opt_p{p}']=float(r['ideal_optimum_probability'])*100
            item[f'energy_p{p}']=float(r['expected_energy'])
        item['gain21']=item['opt_p2']-item['opt_p1']
        item['gain32']=item['opt_p3']-item['opt_p2']
        item['gain31']=item['opt_p3']-item['opt_p1']
        # p3 performance within 2 percentage points; choose shallowest quality-equivalent depth.
        best=max(item[f'opt_p{p}'] for p in (1,2,3))
        item['minimal_p_2pp']=next(p for p in (1,2,3) if item[f'opt_p{p}']>=best-2)
        if item['partition']=='internal_train':
            if m['landscape_hash'] in unique:item['split']='train_duplicate_excluded'
            else:item['split']='train_unique';unique.add(m['landscape_hash'])
        elif item['partition']=='internal_validation' and item['clean']:
            if m['landscape_hash'] in unique:raise ValueError('clean validation landscape leaked')
            item['split']='validation_clean'
        else:item['split']='validation_excluded'
        result.append(item)
    return result

def predict(rows,target):
    train=[x for x in rows if x['split']=='train_unique']
    val=[x for x in rows if x['split']=='validation_clean']
    y=np.array([x[target] for x in train]);true=np.array([x[target] for x in val]);pred={}
    for name,columns in MODELS.items():
        if not columns:pred[name]=np.full(len(val),float(y.mean()))
        else:
            model=make_pipeline(StandardScaler(),Ridge(alpha=10.0))
            model.fit(np.array([[x[f] for f in columns] for x in train]),y)
            pred[name]=model.predict(np.array([[x[f] for f in columns] for x in val]))
    return val,true,pred

def summary(rows):
    out={'version':'QHDE-v0.33-final','research_question':'How do musical complexity and harmonic decision dependencies influence QAOA effectiveness and useful circuit depth?',
         'data_scope':'HookTheory TRAIN, internal hash validation only; full-song music proxies',
         'target':'ideal optimal-state probability gain, percentage points', 'models':{},'descriptive':{},'correlations':{}}
    out['split_counts']=dict(Counter(r['split'] for r in rows))
    for group in ('train_unique','validation_clean'):
        sub=[r for r in rows if r['split']==group]
        out['descriptive'][group]={'n':len(sub),'gain21_mean_pp':float(np.mean([x['gain21'] for x in sub])),
            'gain32_mean_pp':float(np.mean([x['gain32'] for x in sub])),
            'gain32_positive':sum(x['gain32']>0 for x in sub),
            'minimal_p_2pp':dict(Counter(x['minimal_p_2pp'] for x in sub))}
    val,true,pred=predict(rows,'gain32')
    baseline=np.abs(pred['mean']-true)
    rng=np.random.default_rng(33042); ids=rng.integers(0,len(val),size=(4000,len(val)))
    for name,p in pred.items():
        loss=np.abs(p-true)
        improvement=baseline-loss
        out['models'][name]={'validation_mae_pp':float(np.mean(loss)), 'gain_vs_mean_pp':float(np.mean(improvement)),
          'bootstrap_CI95_gain_pp':[float(v) for v in np.quantile(np.mean(improvement[ids],axis=1),[.025,.975])],
          'target':'gain32'}
    out['incremental_comparisons']={}
    for label,base,extended in [('local_over_optimization','optimization','optimization_plus_local'),('music_over_optimization','optimization','optimization_plus_music'),('music_over_optimization_plus_local','optimization_plus_local','all')]:
        gains=np.abs(pred[base]-true)-np.abs(pred[extended]-true)
        out['incremental_comparisons'][label]={'mae_gain_pp':float(np.mean(gains)), 'instance_bootstrap_CI95':[float(v) for v in np.quantile(np.mean(gains[ids],axis=1),[.025,.975])]}
    train=[x for x in rows if x['split']=='train_unique']
    for f in MUSIC+OPT+LOCAL:
        for t in ('gain21','gain32'):
            rho,p=spearmanr([x[f] for x in train],[x[t] for x in train]);
            out['correlations'][f+'__'+t]={'rho':float(rho),'p_uncorrected_exploratory':float(p)}
    return out,val,true,pred

def render(a):
    d=a['descriptive']; models=a['models']; text=['# QHDE v0.33 — FINAL fixed-question analysis','',
      '## Locked research question','',a['research_question'],'',
      '## Scope and data limitations','',
      '- 400 offline tasks; internal validation within HookTheory TRAIN; not independent external music corpus.',
      '- Music entropy and repetition refer to full songs, **not locally aligned four-chord windows**.',
      '- Optimized ideal-state QAOA probabilities reflect fixed parameter-search budget (6 starts, 120 maxiter).',
      '- Local interaction metrics are derived from corrected EMH scoring tables. They quantify model coupling, not independently validated human musical meaning.',
      '- Predictions are ideal/noiseless only. No per-instance IBM outcomes are supplied in this input; hardware results must be treated separately.',
      '- Distinct landscapes do not guarantee distinct independent songs. Bootstrap intervals are instance-level, not independent-song-level.',
      '- The energy gap, feasible-state count and number of optima require knowledge of the full score landscape; models using them are diagnostic, not a cheap deployable depth router.',
      '- Optimizer-score optimum is a model optimum, not independently established perceptual quality or quantum advantage.',
      '','## Sample construction','',f"- Split counts: `{a['split_counts']}`",'','## Ideal optimization outcomes','',
      '| Split | n | Mean gain p2−p1 (pp) | Mean gain p3−p2 (pp) | p3>p2 |','|---|---:|---:|---:|---:|']
    for k in ('train_unique','validation_clean'):
        x=d[k];text.append(f"| {k} | {x['n']} | {x['gain21_mean_pp']:.3f} | {x['gain32_mean_pp']:.3f} | {x['gain32_positive']} |")
    text+=['','## Prediction of ideal p3−p2 gain (validation)','',
      'Fixed Ridge(alpha=10), standardized predictors, trained on unique training landscapes only.',
      '','| Features | MAE (pp) | Improvement over train-mean (pp) | Instance bootstrap 95% CI (pp) |','|---|---:|---:|---:|']
    for name,r in models.items():text.append(f"| {name} | {r['validation_mae_pp']:.3f} | {r['gain_vs_mean_pp']:+.3f} | [{r['bootstrap_CI95_gain_pp'][0]:+.3f}, {r['bootstrap_CI95_gain_pp'][1]:+.3f}] |")
    text+=['','## Incremental predictive value (paired validation)','',
      '| Comparison | Improvement in MAE (pp) | Instance bootstrap 95% CI |','|---|---:|---:|']
    for name,v in a['incremental_comparisons'].items():text.append(f"| {name} | {v['mae_gain_pp']:+.3f} | [{v['instance_bootstrap_CI95'][0]:+.3f}, {v['instance_bootstrap_CI95'][1]:+.3f}] |")
    text+=['','## Hardware benchmark (separate uploaded IBM summary)','',
      '- IBM Marrakesh, job dbhmj3c2d77s739d1v00; 24 selected tasks, 4096 shots per model.',
      '- Uniform 0.76%, p1 7.76%, p2 12.65%, p3 15.17% mean optimal-state probability.',
      '- Mean hardware gain p3−p2 = 2.53 percentage points; 22 positive and 2 negative tasks.',
      '- Hardware–ideal gap rises from 2.72 pp (p1) to 8.02 pp (p2) and 14.53 pp (p3).',
      '- Whole-song transition entropy vs hardware p3−p2 gain: Spearman rho=0.131, uncorrected p=0.542 (exploratory).',
      '- **This analysis does not fit hardware-depth predictors** without per-instance paired IBM observations.',
      '','## Fixed conclusion','',
      'Increasing QAOA depth improves average model-optimum probability for these tasks; real hardware noise substantially erodes these gains. Whether local harmonic decision interactions explain *additional* gains beyond generic optimization structure is evaluated using the holdout models above; negative outcomes must remain negative. No demonstrated quantum advantage against classical dynamic programming.','']
    return '\n'.join(text)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--instances',default='QHDE/results/expanded_v29_full');ap.add_argument('--metrics',default='QHDE/results/optimize_v30_full/metrics.csv');ap.add_argument('--out',default='QHDE/results/final_v33');a=ap.parse_args()
    m,get,by=read_sources(a.instances,a.metrics);rows=build(m,get,by);out,val,truth,pred=summary(rows)
    dest=Path(a.out);dest.mkdir(parents=True,exist_ok=True)
    with (dest/'per_instance.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with (dest/'predictions.csv').open('w',newline='') as f:
        fields=['record_id','gain32_actual_pp']+[f'{k}_predicted_pp' for k in pred]
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for i,r in enumerate(val):w.writerow(dict(record_id=r['record_id'],gain32_actual_pp=truth[i],**{f'{k}_predicted_pp':float(v[i]) for k,v in pred.items()}))
    (dest/'audit.json').write_text(json.dumps(out,indent=2,ensure_ascii=False))
    (dest/'REPORT.md').write_text(render(out))
    print('FINAL',len(rows),'instances; train',out['split_counts'].get('train_unique'),'validation',len(val));print('REPORT:',dest/'REPORT.md')

if __name__=='__main__':main()
