"""Task 2 (4 points): add temporary drop rules on traffic-rate anomalies.

Start from the repository root:
    osken-manager --ofp-tcp-listen-port 6653 tasks/task_2/task.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tasks.task_1.task import FlowMonitorApp
from tasks.task_2.policy import PolicyEngine

POLICY = json.loads((ROOT / 'config/policies.json').read_text(encoding='utf-8'))


class AnomalyDetectionApp(FlowMonitorApp):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.policy = PolicyEngine(POLICY)

    def on_switch_reset(self, dpid):
        super().on_switch_reset(dpid)
        if hasattr(self, 'policy'):
            self.policy.reset(dpid)

    def after_rates(self, dpid, timestamp, rates):
        """TODO: check rates using PolicyEngine and add OFP drop flows."""
        pass

    def install_block(self, datapath, src_ip, seconds):
        """TODO: send a higher-priority IPv4 src drop flow.

        Requirements:
        * match eth_type=0x0800 and ipv4_src=src_ip
        * priority higher than the forwarding rules
        * no output actions/instructions (drop)
        * hard_timeout=seconds; block disappears automatically in OVS
        * leave ARP and traffic of other sources untouched
        """
        pass

    def blocked_sources(self, dpid, timestamp):
        return self.policy.active(dpid, timestamp)
