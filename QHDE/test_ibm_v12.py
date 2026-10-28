"""Offline smoke checks. Run from repository root via unittest discovery."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from qhde_ibm_v12 import make_uniform

class TestIBMPreparation(unittest.TestCase):
    def test_uniform(self):
        from qiskit.quantum_info import Statevector
        qc=make_uniform()
        self.assertEqual(qc.num_qubits,4)
        self.assertEqual(qc.num_clbits,4)
        c=qc.remove_final_measurements(inplace=False)
        self.assertTrue(all(abs(x-1/16)<1e-12 for x in Statevector.from_instruction(c).probabilities()))

    def test_source_scores(self):
        from qhde_ibm_v12 import source_problem
        score=Path('QHDE/results/hooktheory_v04/scores_000.json')
        summary=Path('QHDE/results/hardware_v10/summary.json')
        if not score.exists() or not summary.exists(): self.skipTest('User experiment outputs not available')
        qc,uniform,metadata=source_problem(score,summary,1)
        self.assertEqual(qc.num_qubits,4)
        self.assertEqual(qc.num_clbits,4)
        self.assertGreater(metadata['ideal_qaoa_optimum_probability'],0)
        self.assertTrue(metadata['full_optimum_represented'])

if __name__=='__main__': unittest.main()
