from pathlib import Path
from harmonix.baseline import verify_snapshot, ROOT, VENDOR

def test_vendor_snapshot_unchanged():
    assert verify_snapshot() > 0

def test_baseline_is_local_to_harmonix():
    assert VENDOR.resolve().is_relative_to(ROOT.resolve())
    assert (VENDOR / "emh" / "optimizer.py").is_file()
