import pytest
from faultseeker.core.paper_profile import reentrancy_tier


@pytest.mark.parametrize('score,tier',[(.0,'NOT_REENTRANCY'),(.0999,'NOT_REENTRANCY'),
    (.10,'UNLIKELY_REENTRANCY'),(.2999,'UNLIKELY_REENTRANCY'),
    (.30,'POSSIBLE_REENTRANCY'),(.5499,'POSSIBLE_REENTRANCY'),
    (.55,'HIGH_RISK_REENTRANCY'),(.7999,'HIGH_RISK_REENTRANCY'),(.8,'CONFIRMED_REENTRANCY')])
def test_every_tier_boundary_and_its_lower_neighbor(score,tier):
    assert reentrancy_tier(score) == tier
