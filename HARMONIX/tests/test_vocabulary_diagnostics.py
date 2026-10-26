import unittest
from harmonix.vocabulary_diagnostics import analyze

class VocabularyDiagnosticsTest(unittest.TestCase):
    def test_counts_and_no_mutation(self):
        report={"segments":[
            {"id":"a","status":"covered"},
            {"id":"a","status":"out_of_vocabulary","quality":"major_triad",
             "root_pitch_class":0,"relative_pitch_classes":[0,4,7],
             "root_match_any":True,"pitch_class_match_any":False},
            {"id":"b","status":"out_of_vocabulary","quality":"sus4",
             "root_pitch_class":7,"relative_pitch_classes":[0,5,7],
             "root_match_any":False,"pitch_class_match_any":False},
        ],"failures":[{"id":"c"}]}
        before=repr(report)
        result=analyze(report)
        self.assertEqual(result["oov_count"],2)
        self.assertEqual(result["oov_common_quality_count"],1)
        self.assertEqual(result["oov_complex_quality_count"],1)
        self.assertEqual(result["oov_root_available_count"],1)
        self.assertEqual(result["n_worker_failures"],1)
        self.assertEqual(repr(report),before)
