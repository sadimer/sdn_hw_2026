"""Task 1 (6 points): compute per-source traffic rates from flow counters.

Pure Python: the tests exercise this module without Mininet or OSKen.
"""
from common.models import FlowCounter, SourceRate


class FlowRateTracker:
    def __init__(self):
        # TODO: store previous samples independently for each datapath.
        pass

    def reset(self, dpid: int) -> None:
        """Discard old measurements when a switch disconnects/reconnects."""
        # TODO
        pass

    def update(
        self, dpid: int, timestamp: float, flows: list[FlowCounter]
    ) -> dict[str, SourceRate]:
        """Return per-source cumulative counters and latest pps/bps.

        Rules:
        * First snapshot is a baseline (pps=bps=0).
        * Rate = delta packets/time, delta bytes*8/time.
        * Sum traffic across multiple flows of the same src_ip.
        * A newly installed flow must NOT cause a false traffic spike.
        * Handle flow deletion, counter resets and non-increasing timestamps.
        * Do not mix different switch DPIDs.
        """
        # TODO: implement the algorithm. Returning {} is intentional.
        return {}
