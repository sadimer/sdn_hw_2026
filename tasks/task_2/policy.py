"""Task 2 (4 points): decision engine, independent of OpenFlow/Mininet."""
from common.models import BlockDecision, SourceRate


class PolicyEngine:
    def __init__(self, config: dict):
        """config format: {'rules': [{src_ip, max_pps, block_seconds}, ...]}."""
        # TODO: parse rules, validate limits, track active blocks by (dpid, IP)
        pass

    def evaluate(
        self, dpid: int, timestamp: float, rates: dict[str, SourceRate]
    ) -> list[BlockDecision]:
        """Return NEW blocks only, for sources with pps > configured threshold.

        No duplicate blocks while block_seconds has not elapsed.
        A different source or switch must not be affected.
        """
        # TODO
        return []

    def active(self, dpid: int, timestamp: float) -> list[dict]:
        """Return active blocks as [{'src_ip': ..., 'until': ...}, ...]."""
        # TODO
        return []

    def reset(self, dpid: int) -> None:
        """Forget blocks after disconnect/reconnect of this switch."""
        # TODO
        pass
