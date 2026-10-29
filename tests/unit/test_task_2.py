"""Task 2: threshold and temporary-block state machine."""
import pytest

from common.models import SourceRate
from tasks.task_2.policy import PolicyEngine


CONFIG = {'rules': [
    {'src_ip': '10.0.0.1', 'max_pps': 100, 'block_seconds': 10},
    {'src_ip': '10.0.0.2', 'max_pps': 50, 'block_seconds': 3},
]}


def rates(**entries):
    return {ip: SourceRate(500, 60000, pps, pps * 800) for ip, pps in entries.items()}


def test_below_threshold_is_not_blocked():
    engine = PolicyEngine(CONFIG)
    assert engine.evaluate(1, 100, rates(**{'10.0.0.1': 99})) == []


def test_equal_to_threshold_is_not_blocked():
    engine = PolicyEngine(CONFIG)
    assert engine.evaluate(1, 100, rates(**{'10.0.0.1': 100})) == []


def test_strictly_above_threshold_blocks_for_configured_duration():
    engine = PolicyEngine(CONFIG)
    decisions = engine.evaluate(1, 100, rates(**{'10.0.0.1': 101}))
    assert len(decisions) == 1
    assert decisions[0].dpid == 1
    assert decisions[0].src_ip == '10.0.0.1'
    assert decisions[0].block_seconds == 10


def test_unlisted_source_does_not_get_blocked():
    engine = PolicyEngine(CONFIG)
    assert engine.evaluate(1, 100, rates(**{'10.0.0.99': 999999})) == []


def test_active_block_is_not_reinstalled():
    engine = PolicyEngine(CONFIG)
    engine.evaluate(1, 100, rates(**{'10.0.0.1': 101}))
    assert engine.evaluate(1, 102, rates(**{'10.0.0.1': 9999})) == []
    assert engine.active(1, 102) == [{'src_ip': '10.0.0.1', 'until': 110}]


def test_block_expires_and_can_be_reestablished():
    engine = PolicyEngine(CONFIG)
    engine.evaluate(1, 100, rates(**{'10.0.0.1': 101}))
    assert engine.active(1, 110) == []
    decisions = engine.evaluate(1, 111, rates(**{'10.0.0.1': 150}))
    assert len(decisions) == 1


def test_sources_are_independent():
    engine = PolicyEngine(CONFIG)
    decisions = engine.evaluate(1, 100, rates(**{'10.0.0.1': 200, '10.0.0.2': 70}))
    assert {(d.src_ip, d.block_seconds) for d in decisions} == {
        ('10.0.0.1', 10), ('10.0.0.2', 3)
    }
    assert len(engine.active(1, 102)) == 2
    assert len(engine.active(1, 104)) == 1


def test_switches_are_independent():
    engine = PolicyEngine(CONFIG)
    assert len(engine.evaluate(1, 100, rates(**{'10.0.0.1': 150}))) == 1
    assert len(engine.evaluate(2, 100, rates(**{'10.0.0.1': 150}))) == 1
    assert len(engine.active(2, 101)) == 1


def test_reset_clears_only_requested_switch():
    engine = PolicyEngine(CONFIG)
    engine.evaluate(1, 100, rates(**{'10.0.0.1': 150}))
    engine.evaluate(2, 100, rates(**{'10.0.0.1': 150}))
    engine.reset(1)
    assert engine.active(1, 101) == []
    assert len(engine.active(2, 101)) == 1


def test_invalid_configuration_rejected():
    with pytest.raises(ValueError):
        PolicyEngine({'rules': [{'src_ip': 'not_an_ip', 'max_pps': 50, 'block_seconds': 10}]})
    with pytest.raises(ValueError):
        PolicyEngine({'rules': [{'src_ip': '10.0.0.1', 'max_pps': -1, 'block_seconds': 10}]})
    with pytest.raises(ValueError):
        PolicyEngine({'rules': [{'src_ip': '10.0.0.1', 'max_pps': 20, 'block_seconds': 0}]})
