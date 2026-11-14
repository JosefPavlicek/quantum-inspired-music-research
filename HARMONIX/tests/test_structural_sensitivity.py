import pytest
from harmonix.structural_sensitivity import GRID_R, GRID_F, weights_for


def test_grid_and_arm_weights():
    assert len(GRID_R)*len(GRID_F) == 9
    assert weights_for(.12, .06) == {
        'repetition': (.12, 0.), 'function': (0., .06), 'combined': (.12, .06)}
    with pytest.raises(ValueError):
        weights_for(-.1, .06)
