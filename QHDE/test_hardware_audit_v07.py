import unittest
from qhde_hardware_audit_v07 import BASIS
class TestHardwareAudit(unittest.TestCase):
    def test_supported_basis(self):
        self.assertIn('cx', BASIS)
        self.assertIn('ecr', BASIS)
    def test_single_qubit_basis(self):
        for gates in BASIS.values():
            self.assertTrue({'rz','sx','x'}.issubset(set(gates)))
if __name__=='__main__': unittest.main()
