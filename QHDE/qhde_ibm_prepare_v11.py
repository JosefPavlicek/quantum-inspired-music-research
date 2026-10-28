"""QHDE v0.11: IBM backend discovery and transpilation only. NEVER submits QPU jobs.

Run from the repository root. Does not modify HARMONIX or EMH.
Requires qhde_hardware_v10.py and its offline HookTheory score exports.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys


def service_for_metadata(instance=None):
    """Access existing IBM configuration. No credential capture or job submission."""
    from qiskit_ibm_runtime import QiskitRuntimeService
    kw = {"instance": instance} if instance else {}
    return QiskitRuntimeService(**kw)


def make_example_backend():
    """Small synthetic chain; useful only for OFFLINE engineering tests."""
    from qiskit.providers.fake_provider import GenericBackendV2
    return GenericBackendV2(num_qubits=5, coupling_map=[[0, 1], [1, 2], [2, 3], [3, 4]],
                            basis_gates=["rz", "sx", "x", "cx", "reset", "measure"])


def backend_inventory(service):
    rows = []
    for backend in service.backends():
        status = backend.status()
        rows.append({
            "backend": backend.name,
            "qubits": backend.num_qubits,
            "operational": bool(getattr(status, "operational", False)),
            "pending_jobs": getattr(status, "pending_jobs", None),
            "basis_gates": list(getattr(backend, "operation_names", [])),
        })
    return rows


def audit(backend, scores_file, summary_file, p=1, optimization_level=2, seed=42):
    import numpy as np
    from qiskit.transpiler import generate_preset_pass_manager
    from qhde_hardware_v10 import build_problem, make_circuit

    data = json.loads(Path(scores_file).read_text(encoding="utf8"))
    problem = build_problem(data)
    summary = json.loads(Path(summary_file).read_text(encoding="utf8"))
    target = next((r for r in summary["records"] if Path(r["score_file"]).name == Path(scores_file).name), None)
    if target is None:
        raise ValueError("Cannot match score file to v0.10 summary. Do not silently re-optimize.")
    model = target["models"][f"p{p}"]
    params = np.asarray(model["params"], dtype=float)
    if len(params) != 2*p:
        raise ValueError("Parameters inconsistent with QAOA depth")
    qc = make_circuit(problem["energies"], params, measure=True)
    manager = generate_preset_pass_manager(
        optimization_level=optimization_level, backend=backend,
        seed_transpiler=seed, approximation_degree=1.0)
    compiled = manager.run(qc)
    gate_counts = dict(compiled.count_ops())
    two_qubit_ops = {name: int(n) for name, n in gate_counts.items()
                     if name in {"cx", "ecr", "cz", "rzz", "iswap", "swap"}}
    result = {
        "backend": backend.name,
        "backend_qubits": backend.num_qubits,
        "score_file": str(scores_file),
        "record_id": data.get("record_id"),
        "p": p,
        "seed_transpiler": seed,
        "optimization_level": optimization_level,
        "physical_depth": compiled.depth(),
        "physical_size": compiled.size(),
        "gate_counts": gate_counts,
        "two_qubit_operations": two_qubit_ops,
        "two_qubit_total": sum(two_qubit_ops.values()),
        "layout": str(compiled.layout),
        "full_optimum_represented": problem["full_optimum_represented"],
        "qpu_jobs_submitted": 0,
        "warning": "Compilation is not execution; gate counts and backend calibrations may change. No QPU fidelity claim.",
    }
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["offline", "inventory", "backend"], default="offline")
    parser.add_argument("--instance", help="Optional IBM instance identifier; do not supply API tokens")
    parser.add_argument("--backend", help="Exact backend name; required with --mode backend")
    parser.add_argument("--scores", default="QHDE/results/hooktheory_v04/scores_000.json")
    parser.add_argument("--summary", default="QHDE/results/hardware_v10/summary.json")
    parser.add_argument("--p", type=int, choices=[1, 2], default=1)
    parser.add_argument("--level", type=int, choices=[0, 1, 2, 3], default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="QHDE/results/ibm_prepare_v11")
    args = parser.parse_args(argv)
    if args.mode == "backend" and not args.backend:
        parser.error("--backend is required with --mode backend")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.mode == "offline":
        backend = make_example_backend()
    else:
        service = service_for_metadata(instance=args.instance)
        inventory = backend_inventory(service)
        (out / "available_backends.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf8")
        print("Available IBM backends (metadata only):")
        for item in inventory:
            print(f"  {item['backend']}: {item['qubits']} qubits, operational={item['operational']}, queue={item['pending_jobs']}")
        if args.mode == "inventory":
            print("Saved", out / "available_backends.json", "; NO jobs submitted")
            return 0
        backend = service.backend(args.backend)
    result = audit(backend, args.scores, args.summary, args.p, args.level, args.seed)
    name = "offline_audit.json" if args.mode == "offline" else "backend_audit.json"
    (out / name).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(f"{result['backend']} p={args.p}: depth={result['physical_depth']} "
          f"2q={result['two_qubit_total']} gates={result['physical_size']}")
    print("Gate counts:", result["gate_counts"])
    print("Saved", out / name, "; NO QPU jobs submitted")
    return 0

if __name__ == "__main__":
    sys.exit(main())
