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

from os_ken.lib.packet import ether_types

from common.forwarding import BLOCK_PRIORITY
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
        datapath = self.datapaths.get(dpid)
        if datapath is None:
            return
        for decision in self.policy.evaluate(dpid, timestamp, rates):
            self.install_block(datapath, decision.src_ip, decision.block_seconds)
            self.logger.warning(
                'Blocked dpid=%s src=%s for %ss',
                dpid,
                decision.src_ip, 
                decision.block_seconds,
            )

    def install_block(self, datapath, src_ip, seconds):
        ofp = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch(
            eth_type=ether_types.ETH_TYPE_IP,
            ipv4_src=src_ip,
        )
        mod = parser.OFPFlowMod(
            datapath=datapath,
            command=ofp.OFPFC_ADD,
            priority=BLOCK_PRIORITY,
            match=match,
            instructions=[],
            hard_timeout=int(seconds),
        )
        datapath.send_msg(mod)

    def blocked_sources(self, dpid, timestamp):
        return self.policy.active(dpid, timestamp)
