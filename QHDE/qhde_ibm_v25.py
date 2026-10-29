"""QHDE v0.25: prepare, submit, collect and analyze 8-qubit/4-chord QAOA.
Run from repo root. Submission ONLY with --submit --confirm-spend-QPU.
"""
from __future__ import annotations
import argparse,hashlib,json,math
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from qhde_structured_qaoa_v23 import analyze as decompose,make_circuit
from qhde_optimize_v24 import simulate,get_optimal

BASE=Path('QHDE/results/ibm_v25')
SRC=Path('QHDE/results/four_segments_v22')
OPT=Path('QHDE/results/optimize_v24/optimization.json')
TWOQ={'cx','cz','ecr','iswap','rzz','swap','rxx','ryy','rzx'}
def utc():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,obj):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def check_map(c):
 lay=getattr(c,'layout',None)
 if lay is None:raise ValueError(f'{c.name}: missing transpiler layout')
 mapping=lay.final_index_layout(filter_ancillas=True)
 if len(mapping)!=8 or len(set(mapping))!=8:raise ValueError(f'{c.name}: invalid 8-qubit mapping')
 measured={}
 for inst in c.data:
  if inst.operation.name!='measure':continue
  q=c.find_bit(inst.qubits[0]).index;b=c.find_bit(inst.clbits[0]).index
  if q in measured:raise ValueError('duplicate measurement')
  measured[q]=b
 if c.num_clbits!=8 or len(measured)!=8:raise ValueError(f'{c.name}: invalid measurement count')
 for logical,physical in enumerate(mapping):
  if measured.get(physical)!=logical:raise ValueError(f'{c.name}: bit mapping inconsistent logical={logical}, physical={physical}, measured={measured.get(physical)}')
 return list(map(int,mapping))
def build(source,optimization):
 from qiskit import QuantumCircuit
 from qiskit.quantum_info import Statevector
 manifest=load(source/'manifest.json');optimized=load(optimization)
 if optimized.get('version')!='QHDE-v0.24':raise ValueError('Expected v0.24 optimization')
 if sha(source/'manifest.json')!=optimized['source_manifest_sha256']:raise ValueError('Source manifest changed since optimization')
 records={r['record_id']:r for r in optimized['records']};circuits=[];metadata=[];ids=set()
 for i,row in enumerate(manifest['records']):
  rid=row['record_id'];o=records.get(rid)
  if o is None:raise ValueError(f'Missing optimized record {rid}')
  if not o['exact_chain_local']:continue
  if rid in ids:raise ValueError('duplicate record id')
  ids.add(rid)
  item=load(source/row['file']);energy=np.asarray(item['energies_256'],float)
  feasible=np.array([s is not None for s in item['scores_256']],dtype=bool)
  if feasible.shape!=(256,) or not feasible.all():raise ValueError(f'{rid}: not entirely feasible / local')
  coeff,terms,higher,err=decompose(energy)
  if err>1e-9 or higher:raise ValueError(f'{rid}: energy not exact local')
  opt=get_optimal(energy,feasible).tolist();names=[];checks={}
  for label,p in [('uniform',0),('p1',1),('p2',2),('p3',3)]:
   name=f'clip_{i:02d}_{label}'
   if p==0:
    qc=QuantumCircuit(8);qc.h(range(8));distribution=np.ones(256)/256
   else:
    m=o['models'][label];params=np.asarray(m['params'],float)
    if params.shape!=(2*p,):raise ValueError(f'{rid}: incorrect parameter shape')
    distribution=simulate(energy,params,p)
    if abs(float(distribution[opt].sum())-m['ideal_optimum_probability'])>1e-8:raise ValueError(f'{rid}: ideal optimum mismatch')
    if abs(float(distribution@energy)-m['expected_energy'])>1e-8:raise ValueError(f'{rid}: expected energy mismatch')
    qc=make_circuit(energy,p,params[:p],params[p:],coeff)
   qdist=np.abs(Statevector.from_instruction(qc).data)**2
   delta=float(np.max(np.abs(qdist-distribution)))
   if delta>1e-8:raise ValueError(f'{rid}: Qiskit/NumPy mismatch {label} {delta}')
   qc.add_register(__import__('qiskit').ClassicalRegister(8,'c'))
   qc.measure(range(8),range(8));qc.name=name
   circuits.append(qc);names.append(name)
   checks[label]={'ideal_optimum_probability':float(distribution[opt].sum()),'ideal_expected_energy':float(distribution@energy),'max_distribution_error':delta}
  metadata.append({'record_id':rid,'stratum':row['stratum'],'source_file':row['file'], 'names':names,
    'optimal_basis_indices':opt,'energies_256':energy.tolist(),'feasible_256':feasible.tolist(), 'checks':checks})
 if len(metadata)!=12 or len(circuits)!=48:raise ValueError(f'Expected 12 local instances/48 circuits: got {len(metadata)}/{len(circuits)}')
 return circuits,metadata

def prepare(a):
 from qiskit_ibm_runtime import QiskitRuntimeService
 from qiskit.transpiler import generate_preset_pass_manager
 from qiskit import qpy
 out=Path(a.out)
 if (out/'submitted_job.json').exists():raise ValueError('Already submitted; refusing overwrite')
 source=Path(a.source);optimization=Path(a.optimization)
 circuits,records=build(source,optimization)
 service=QiskitRuntimeService(**({'instance':a.instance} if a.instance else {}));candidates=[]
 for name in a.backends:
  try:
   backend=service.backend(name)
   if not backend.status().operational:continue
   pm=generate_preset_pass_manager(backend=backend,seed_transpiler=a.seed,optimization_level=a.level,approximation_degree=1.0)
   compiled=[];stats=[]
   for raw in circuits:
    transpiled=pm.run(raw)
    bad=set(transpiled.count_ops())-set(backend.target.operation_names)-{'barrier','delay'}
    if bad:raise ValueError(f'Unsupported operations {bad}')
    layout=check_map(transpiled)
    gates={str(k):int(v) for k,v in transpiled.count_ops().items()}
    twoq=sum(v for k,v in gates.items() if k in TWOQ)
    stats.append({'name':transpiled.name,'depth':int(transpiled.depth()),'two_qubit_gates':twoq,'operations':gates,'logical_to_physical':layout})
    compiled.append(transpiled)
   total=sum(r['two_qubit_gates'] for r in stats);queue=int(backend.status().pending_jobs)
   candidates.append((total,queue,name,compiled,stats))
   print(f'{name}: 48 circuits, 2q total={total}, deepest={max(s["depth"] for s in stats)}, queue={queue}',flush=True)
  except Exception as e:print(f'{name}: preparation failed: {e}',flush=True)
 if not candidates:raise RuntimeError('No backend could be safely transpiled')
 candidates.sort(key=lambda x:x[:3]);total,queue,name,compiled,stats=candidates[0]
 out.mkdir(parents=True,exist_ok=True)
 with (out/'circuits.qpy').open('wb') as fh:qpy.dump(compiled,fh)
 save(out/'preparation.json',{'version':'QHDE-v0.25','backend':name,'queue':queue,'shots':a.shots,'source_manifest':str(source/'manifest.json'),
 'source_manifest_sha256':sha(source/'manifest.json'),'optimization':str(optimization),'optimization_sha256':sha(optimization),
 'circuits_sha256':sha(out/'circuits.qpy'),'circuit_names':[c.name for c in compiled],'records':records,'transpiled':stats,
 'total_2q_gates':total,'created_utc':utc(),'warning':'TRAIN selection, exact classical oracle; 12 local four-segment tasks; no speedup claim'})
 print(f'SELECTED {name}; saved preparation.json and circuits.qpy; NO QPU JOBS SUBMITTED')

def submit(a):
 if not a.confirm_spend_qpu:raise ValueError('Explicit --confirm-spend-QPU required')
 from qiskit_ibm_runtime import QiskitRuntimeService,SamplerV2
 from qiskit import qpy
 out=Path(a.out)
 if (out/'submitted_job.json').exists():raise ValueError('Already submitted; DO NOT RESUBMIT')
 p=load(out/'preparation.json')
 if sha(p['optimization'])!=p['optimization_sha256'] or sha(p['source_manifest'])!=p['source_manifest_sha256'] or sha(out/'circuits.qpy')!=p['circuits_sha256']:raise ValueError('Prepared inputs changed')
 if a.shots!=p['shots']:raise ValueError('Shot mismatch')
 with (out/'circuits.qpy').open('rb') as fh:circuits=qpy.load(fh)
 if len(circuits)!=48 or [c.name for c in circuits]!=p['circuit_names']:raise ValueError('Circuit manifest mismatch')
 service=QiskitRuntimeService(**({'instance':a.instance} if a.instance else {}))
 backend=service.backend(p['backend'])
 if not backend.status().operational:raise ValueError('Backend not operational')
 print(f'SUBMITTING 48 circuits x {a.shots} shots to {p["backend"]}; charge unknown',flush=True)
 job=SamplerV2(mode=backend).run(circuits,shots=a.shots)
 save(out/'submitted_job.json',{'job_id':job.job_id(),'backend':p['backend'],'shots':a.shots,'circuits_sha256':p['circuits_sha256'],'circuit_names':p['circuit_names'],'time':utc()})
 print('JOB ID',job.job_id(),'— DO NOT RESUBMIT')

def collect(a):
 from qiskit_ibm_runtime import QiskitRuntimeService
 out=Path(a.out);p=load(out/'submitted_job.json')
 job=QiskitRuntimeService(**({'instance':a.instance} if a.instance else {})).job(p['job_id'])
 status=str(job.status());print('JOB',job.job_id(),'STATUS',status)
 if 'DONE' not in status.upper():return
 res=job.result()
 if len(res)!=48:raise ValueError('Expected 48 result PUBs')
 counts=[]
 for pub in res:
  c=getattr(pub.data,'c',None)
  if c is None:raise ValueError('Missing c register')
  counts.append({str(k):int(v) for k,v in c.get_counts().items()})
 try:metrics=job.metrics()
 except Exception as e:metrics={'error':str(e)}
 save(out/'raw_results.json',{'version':'QHDE-v0.25','job_id':job.job_id(),'status':status,'circuits_sha256':p['circuits_sha256'],
 'circuit_names':p['circuit_names'],'counts_ordered':counts,'metrics':metrics,'retrieved_utc':utc()})
 print('Saved raw_results.json; run --analyze')

def wilson(k,n):
 z=1.96;prob=k/n;den=1+z*z/n;cent=(prob+z*z/(2*n))/den
 margin=z*math.sqrt(prob*(1-prob)/n+z*z/(4*n*n))/den
 return [cent-margin,cent+margin]
def analyze(a):
 out=Path(a.out);p=load(out/'preparation.json');raw=load(out/'raw_results.json')
 if raw['circuits_sha256']!=p['circuits_sha256'] or raw['circuit_names']!=p['circuit_names']:raise ValueError('Collected experiment does not match preparation')
 if len(raw['counts_ordered'])!=48:raise ValueError('Not 48 results')
 report=[];means={s:[] for s in ('uniform','p1','p2','p3')}
 for i,row in enumerate(p['records']):
  energies=np.asarray(row['energies_256'],float);feasible=np.asarray(row['feasible_256'],bool)
  opt=set(row['optimal_basis_indices']);models=[]
  for j,label in enumerate(('uniform','p1','p2','p3')):
   counts=raw['counts_ordered'][4*i+j];n=sum(counts.values())
   if n!=p['shots']:raise ValueError('Wrong shot count')
   dist=np.zeros(256)
   for bits,k in counts.items():
    b=bits.replace(' ','');idx=int(b,2)
    if len(b)!=8 or idx<0 or idx>=256:raise ValueError(f'Wrong measured bits {bits}')
    dist[idx]+=k/n
   hits=sum(int(dist[x]*n+0.5) for x in opt);prob=hits/n
   means[label].append(prob)
   models.append({'model':label,'shots':n,'optimum_hits':hits,'optimum_probability':prob,'wilson_95':wilson(hits,n),
    'feasible_probability':float(dist[feasible].sum()),'expected_energy':float(dist@energies),
    'ideal_optimum_probability':row['checks'][label]['ideal_optimum_probability'],
    'ideal_expected_energy':row['checks'][label]['ideal_expected_energy'],
    'state_probabilities':dist.tolist()})
  report.append({'record_id':row['record_id'],'stratum':row['stratum'],'n_optimal_states':len(opt),'results':models})
 averages={label:float(np.mean(vals)) for label,vals in means.items()}
 save(out/'analysis.json',{'version':'QHDE-v0.25','job_id':raw['job_id'],'backend':p['backend'],'metrics':raw['metrics'],
 'mean_optimum_probability':averages,'records':report,'warning':'All tasks 256 feasible states. Single job, model-scored optimum, classical exact enumeration available.'})
 print('MEAN', {key:round(val*100,2) for key,val in averages.items()},'%');print('Saved',out/'analysis.json')

def main():
 ap=argparse.ArgumentParser(description=__doc__);g=ap.add_mutually_exclusive_group()
 for x in ('prepare','submit','collect','analyze'):g.add_argument('--'+x,action='store_true')
 ap.add_argument('--confirm-spend-QPU',action='store_true',dest='confirm_spend_qpu')
 ap.add_argument('--source',default=str(SRC));ap.add_argument('--optimization',default=str(OPT));ap.add_argument('--out',default=str(BASE))
 ap.add_argument('--backends',nargs='+',default=['ibm_pittsburgh','ibm_marrakesh']);ap.add_argument('--instance')
 ap.add_argument('--shots',type=int,default=1024);ap.add_argument('--seed',type=int,default=42);ap.add_argument('--level',type=int,default=2,choices=[0,1,2,3])
 a=ap.parse_args()
 if not 1<=a.shots<=10000:ap.error('shots must be 1..10000')
 if a.submit:submit(a)
 elif a.collect:collect(a)
 elif a.analyze:analyze(a)
 else:prepare(a)
if __name__=='__main__':main()
