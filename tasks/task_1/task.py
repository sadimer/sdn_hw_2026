"""Task 1 (6 points): monitor OpenFlow 1.3 forwarding rules.

Start from the repository root:
    osken-manager --ofp-tcp-listen-port 6653 tasks/task_1/task.py
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from os_ken.controller import ofp_event
from os_ken.controller.handler import MAIN_DISPATCHER, set_ev_cls
from os_ken.lib import hub

from common.forwarding import ForwardingSwitch
from common.metrics import MetricsPublisher
from common.ofp_helpers import forwarding_counters
from tasks.task_1.monitor import FlowRateTracker

CONFIG = json.loads((ROOT / 'config/monitor.json').read_text(encoding='utf-8'))


class FlowMonitorApp(ForwardingSwitch):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tracker = FlowRateTracker()
        self.metrics = MetricsPublisher(ROOT / CONFIG['metrics_path'])
        self._pending = {}  # optional: assemble OFP multipart replies by xid
        self._poll_thread = hub.spawn(self._poll_loop)

    def on_switch_reset(self, dpid):
        if hasattr(self, 'tracker'):
            self.tracker.reset(dpid)
            self.metrics.reset(dpid)
            self._pending.pop(dpid, None)

    def _poll_loop(self):
        while True:
            for dp in list(self.datapaths.values()):
                self.request_stats(dp)
            hub.sleep(float(CONFIG['poll_interval']))

    def request_stats(self, datapath):
        """TODO: periodically send OFPFlowStatsRequest to a switch.

        Request only the IPv4 forwarding rules (FORWARD_COOKIE) where possible.
        Do not send a new request if the previous one is still outstanding,
        unless it has timed out.
        """
        pass

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_reply_handler(self, ev):
        """TODO: process stats reply, including OFPMPF_REPLY_MORE fragments.

        Ignore late responses to obsolete requests. Use forwarding_counters()
        to convert OFPFlowStats to FlowCounter objects. Then call:
            self.publish_sample(dpid, time.monotonic(), flow_counters)
        """
        pass

    def publish_sample(self, dpid, timestamp, flow_counters):
        rates = self.tracker.update(dpid, timestamp, flow_counters)
        self.after_rates(dpid, timestamp, rates)
        self.metrics.update(dpid, timestamp, rates, self.blocked_sources(dpid, timestamp))
        for ip, rate in sorted(rates.items()):
            self.logger.info('dpid=%s src=%s pps=%.2f bps=%.2f',
                             dpid, ip, rate.pps, rate.bps)

    def after_rates(self, dpid, timestamp, rates):
        """Task 2 uses this hook to react to anomalous activity."""

    def blocked_sources(self, dpid, timestamp):
        """Task 2 uses this hook to export currently blocked IPs."""
        return []
