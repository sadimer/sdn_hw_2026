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

from common.forwarding import FORWARD_COOKIE, FULL_COOKIE_MASK, ForwardingSwitch
from common.metrics import MetricsPublisher
from common.ofp_helpers import forwarding_counters
from tasks.task_1.monitor import FlowRateTracker

CONFIG = json.loads((ROOT / 'config/monitor.json').read_text(encoding='utf-8'))


class FlowMonitorApp(ForwardingSwitch):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tracker = FlowRateTracker()
        self.metrics = MetricsPublisher(ROOT / CONFIG['metrics_path'])
        self._pending = {}  
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
        dpid = datapath.id
        now = time.monotonic()
        timeout = max(float(CONFIG['poll_interval']) * 2.0, 2.0)
        pending = self._pending.get(dpid)
        if pending is not None and (now - pending['sent_at']) < timeout:
            return

        ofp = datapath.ofproto
        parser = datapath.ofproto_parser
        req = parser.OFPFlowStatsRequest(
            datapath=datapath, 
            table_id=ofp.OFPTT_ALL,
            out_port=ofp.OFPP_ANY, 
            out_group=ofp.OFPG_ANY,
            cookie=FORWARD_COOKIE,
            cookie_mask=FULL_COOKIE_MASK,
            match=parser.OFPMatch(),
        )
        datapath.set_xid(req)
        self._pending[dpid] = {
            'xid': req.xid,
            'sent_at': now,
            'stats': [],
        }
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_reply_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        dpid = datapath.id
        ofp = datapath.ofproto

        pending = self._pending.get(dpid)
        if pending is None or msg.xid != pending ['xid']:
            return 
        
        pending['stats'].extend(msg.body)
        if msg.flags & ofp.OFPMPF_REPLY_MORE:
            return 

        stats = pending['stats']
        self._pending.pop(dpid, None)
        self.publish_sample(dpid, time.monotonic(), forwarding_counters(stats))


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
