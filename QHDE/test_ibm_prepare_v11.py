"""Safety and metadata tests; no IBM service access."""
import unittest
from unittest.mock import Mock
from qhde_ibm_prepare_v11 import backend_inventory, main

class TestPreparation(unittest.TestCase):
    def test_inventory(self):
        b=Mock(name='backend'); b.name='synthetic'; b.num_qubits=5
        b.operation_names=['rz','sx','cx','measure']
        b.status.return_value=Mock(operational=True,pending_jobs=0)
        rows=backend_inventory(Mock(backends=Mock(return_value=[b])))
        self.assertEqual(rows[0]['backend'],'synthetic')
        self.assertEqual(rows[0]['qubits'],5)

    def test_backend_requires_name(self):
        with self.assertRaises(SystemExit) as cm:
            main(['--mode','backend'])
        self.assertEqual(cm.exception.code,2)

if __name__ == '__main__': unittest.main()
