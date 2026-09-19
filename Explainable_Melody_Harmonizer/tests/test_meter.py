from emh.meter import SUPPORTED_METERS


def test_required_meters_are_supported():
    assert {"2/4", "3/4", "4/4", "6/8", "12/8"} <= SUPPORTED_METERS
