"""Small, dependency-free data contracts for the tasks and unit tests."""
from dataclasses import dataclass


@dataclass(frozen=True)
class FlowCounter:
    flow_id: str  # stable within a particular switch
    src_ip: str
    packets: int  # cumulative packets since this flow was installed
    bytes: int    # cumulative bytes since this flow was installed
    duration: float | None = None  # optional OpenFlow duration_sec + duration_nsec/1e9


@dataclass(frozen=True)
class SourceRate:
    packets: int   # current sum of cumulative counters
    bytes: int
    pps: float     # packets per second during the last measurement interval
    bps: float     # bits per second during the last measurement interval


@dataclass(frozen=True)
class BlockDecision:
    dpid: int
    src_ip: str
    block_seconds: int
