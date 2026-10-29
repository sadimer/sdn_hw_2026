"""Task 1: pure-Python checks; no root privileges or OSKen needed."""
import pytest

from common.models import FlowCounter
from tasks.task_1.monitor import FlowRateTracker


def f(flow_id, ip, packets, nbytes):
    return FlowCounter(flow_id, ip, packets, nbytes)


def test_first_sample_is_baseline():
    tracker = FlowRateTracker()
    result = tracker.update(1, 100.0, [f('a', '10.0.0.1', 1000, 120000)])
    assert result['10.0.0.1'].packets == 1000
    assert result['10.0.0.1'].bytes == 120000
    assert result['10.0.0.1'].pps == 0
    assert result['10.0.0.1'].bps == 0


def test_rate_uses_real_elapsed_time_and_bits():
    tracker = FlowRateTracker()
    tracker.update(1, 10.0, [f('a', '10.0.0.1', 10, 100)])
    result = tracker.update(1, 12.5, [f('a', '10.0.0.1', 60, 3100)])
    assert result['10.0.0.1'].pps == pytest.approx(20)
    assert result['10.0.0.1'].bps == pytest.approx(9600)
    assert result['10.0.0.1'].packets == 60


def test_aggregate_multiple_flows_from_one_source():
    tracker = FlowRateTracker()
    tracker.update(1, 1, [f('a', '10.0.0.1', 5, 500), f('b', '10.0.0.1', 10, 600)])
    result = tracker.update(1, 2, [f('a', '10.0.0.1', 15, 1500), f('b', '10.0.0.1', 30, 2600)])
    assert result['10.0.0.1'].pps == 30
    assert result['10.0.0.1'].bps == 24000
    assert result['10.0.0.1'].packets == 45


def test_multiple_sources_remain_independent():
    tracker = FlowRateTracker()
    tracker.update(1, 10, [f('a', '10.0.0.1', 10, 1000), f('b', '10.0.0.2', 50, 4000)])
    result = tracker.update(1, 11, [f('a', '10.0.0.1', 14, 1400), f('b', '10.0.0.2', 70, 7000)])
    assert result['10.0.0.1'].pps == 4
    assert result['10.0.0.2'].pps == 20


def test_dpid_counters_must_not_mix():
    tracker = FlowRateTracker()
    tracker.update(1, 10, [f('same', '10.0.0.1', 80, 5000)])
    first_on_other_switch = tracker.update(2, 11, [f('same', '10.0.0.1', 350, 20000)])
    assert first_on_other_switch['10.0.0.1'].pps == 0
    result = tracker.update(1, 12, [f('same', '10.0.0.1', 100, 6000)])
    assert result['10.0.0.1'].pps == 10


def test_new_flow_is_not_counted_as_huge_spike():
    tracker = FlowRateTracker()
    tracker.update(1, 1, [f('a', '10.0.0.1', 10, 1000)])
    result = tracker.update(1, 2, [
        f('a', '10.0.0.1', 20, 2000),
        f('new', '10.0.0.1', 6000, 600000),
    ])
    assert result['10.0.0.1'].pps == 10
    assert result['10.0.0.1'].packets == 6020


def test_deleted_flow_does_not_create_negative_rate():
    tracker = FlowRateTracker()
    tracker.update(1, 1, [f('a', '10.0.0.1', 100, 1000), f('b', '10.0.0.1', 200, 2000)])
    result = tracker.update(1, 2, [f('a', '10.0.0.1', 130, 1300)])
    assert result['10.0.0.1'].pps == 30
    assert result['10.0.0.1'].bps == 2400


def test_reset_counters_does_not_create_invalid_rates():
    tracker = FlowRateTracker()
    tracker.update(1, 1, [f('a', '10.0.0.1', 200, 5000)])
    result = tracker.update(1, 2, [f('a', '10.0.0.1', 10, 100)])
    assert result['10.0.0.1'].pps == 0
    result = tracker.update(1, 3, [f('a', '10.0.0.1', 20, 200)])
    assert result['10.0.0.1'].pps == 10


def test_nonpositive_time_delta_ignored():
    tracker = FlowRateTracker()
    tracker.update(1, 10, [f('a', '10.0.0.1', 10, 100)])
    result = tracker.update(1, 10, [f('a', '10.0.0.1', 100, 1000)])
    assert result['10.0.0.1'].pps == 0
    result = tracker.update(1, 11, [f('a', '10.0.0.1', 110, 1100)])
    assert result['10.0.0.1'].pps >= 0


def test_empty_snapshot_removes_old_flows():
    tracker = FlowRateTracker()
    tracker.update(1, 1, [f('a', '10.0.0.1', 200, 5000)])
    assert tracker.update(1, 2, []) == {}
    result = tracker.update(1, 3, [f('a', '10.0.0.1', 900, 90000)])
    assert result['10.0.0.1'].pps == 0


def test_explicit_reset_removes_history():
    tracker = FlowRateTracker()
    tracker.update(1, 1, [f('a', '10.0.0.1', 200, 5000)])
    tracker.reset(1)
    assert tracker.update(1, 2, [f('a', '10.0.0.1', 20000, 900000)])['10.0.0.1'].pps == 0


def test_recreated_flow_with_same_match_restarts_duration():
    tracker = FlowRateTracker()
    old = FlowCounter('flow', '10.0.0.1', 100, 10000, duration=50)
    restarted = FlowCounter('flow', '10.0.0.1', 200, 20000, duration=0.5)
    tracker.update(1, 1, [old])
    result = tracker.update(1, 2, [restarted])
    assert result['10.0.0.1'].pps == 0
    result = tracker.update(1, 3, [FlowCounter('flow', '10.0.0.1', 215, 21500, duration=1.5)])
    assert result['10.0.0.1'].pps == 15
