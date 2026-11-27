"""Task 1 (6 points): compute per-source traffic rates from flow counters.

Pure Python: the tests exercise this module without Mininet or OSKen.
"""
from common.models import FlowCounter, SourceRate


class FlowRateTracker:
    def __init__(self):
        self._state: dict[int, tuple[float, dict[str, FlowCounter]]] = {}

    def reset(self, dpid: int) -> None:
        """Discard old measurements when a switch disconnects/reconnects."""
        self._state.pop(dpid, None)

    def update(
        self, dpid: int, timestamp: float, flows: list[FlowCounter]
    ) -> dict[str, SourceRate]:
        """Return per-source cumulative counters and latest pps/bps."""
        prev = self._state.get(dpid)
        curr_flows = {flow.flow_id: flow for flow in flows}

        agg_packets: dict[str, int] = {}
        agg_bytes: dict[str, int] = {}
        delta_packets: dict[str, int] = {}
        delta_bytes: dict[str, int] = {}

        if prev is None:
            dt = 0.0
            prev_flows = {}
        else:
            prev_ts, prev_flows = prev
            dt = timestamp - prev_ts

        for flow in flows:
            src = flow.src_ip
            agg_packets[src] = agg_packets.get(src, 0) + flow.packets
            agg_bytes[src] = agg_bytes.get(src, 0) + flow.bytes

            dp = 0
            db = 0
            old_flow = prev_flows.get(flow.flow_id)
            if old_flow is not None and dt > 0:
                recreated = (
                    flow.duration is not None 
                    and old_flow.duration is not None
                    and flow.duration < old_flow.duration
                )
                if not recreated:
                    dp = max(0, flow.packets - old_flow.packets)
                    db = max(0, flow.bytes - old_flow.bytes)

            delta_packets[src] = delta_packets.get(src, 0) + dp
            delta_bytes[src] = delta_bytes.get(src, 0) + db
        
        self._state[dpid] = (timestamp, curr_flows)

        result: dict[str, SourceRate] = {}
        for src in agg_packets:
            if prev is None or dt <= 0:
                pps = 0.0
                bps = 0.0
            else:
                pps = delta_packets[src] / dt
                bps = (delta_bytes[src] * 8) / dt
            result[src] = SourceRate(
                packets=agg_packets[src],
                bytes=agg_bytes[src],
                pps=pps,
                bps=bps,
            )   
        return result
