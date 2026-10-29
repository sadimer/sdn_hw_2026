"""Translate OpenFlow replies into testable, OSKen-independent FlowCounter records."""
from common.forwarding import FORWARD_COOKIE, FORWARD_PRIORITY
from common.models import FlowCounter


def forwarding_counters(stats):
    result = []
    for flow in stats:
        if flow.cookie != FORWARD_COOKIE or flow.priority != FORWARD_PRIORITY:
            continue
        match = flow.match
        src_ip = match.get('ipv4_src')
        if not src_ip:
            continue
        # Include enough match fields to distinguish two counters from the
        # same source on the same switch; do not use byte/packet counters here.
        identity = ':'.join(str(value) for value in (
            flow.table_id,
            flow.cookie,
            flow.priority,
            match.get('in_port'),
            match.get('eth_dst'),
            match.get('ipv4_src'),
        ))
        result.append(FlowCounter(
            flow_id=identity,
            src_ip=src_ip,
            packets=flow.packet_count,
            bytes=flow.byte_count,
            duration=flow.duration_sec + flow.duration_nsec / 1_000_000_000,
        ))
    return result
