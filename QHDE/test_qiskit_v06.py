"""Tests for QHDE v0.6; execute only after installing qiskit."""
import unittest
import numpy as np
from qiskit.quantum_info import Statevector
from qhde_qiskit_v06 import make_circuit
from qhde_qaoa_v05 import DIM, statevector

class TestQiskitCircuits(unittest.TestCase):
    def test_equivalence_p1(self):
        energies = np.sin(np.arange(DIM)*0.13)
        params = [0.71, 1.23]
        np.testing.assert_allclose(Statevector.from_instruction(make_circuit(energies,params)).data,
                                   statevector(energies,params), atol=1e-10)
    def test_equivalence_p2(self):
        energies = np.cos(np.arange(DIM)*0.17)
        params = [0.71, 1.23, 0.37, 2.20]
        np.testing.assert_allclose(Statevector.from_instruction(make_circuit(energies,params)).data,
                                   statevector(energies,params), atol=1e-10)
    def test_measurements_are_optional(self):
        energies = np.arange(DIM)*0.01
        self.assertEqual(make_circuit(energies,[0.2,0.7]).num_clbits, 0)
        self.assertEqual(make_circuit(energies,[0.2,0.7],measurement=True).num_clbits, 7)
    def test_invalid_args(self):
        with self.assertRaises(ValueError):
            make_circuit(np.zeros(127), [0.2,0.7])

if __name__ == '__main__':
    unittest.main()
