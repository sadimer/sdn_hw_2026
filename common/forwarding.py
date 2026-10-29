"""Ready-to-use OpenFlow 1.3 L2 forwarding for the assignment.

Students MUST NOT edit this module. Only IPv4 forwarding entries are included
in monitoring. ARP and table-miss traffic are handled separately.
"""
from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import DEAD_DISPATCHER, MAIN_DISPATCHER, CONFIG_DISPATCHER, set_ev_cls
from os_ken.lib.packet import ethernet, ether_types, ipv4, packet
from os_ken.ofproto import ofproto_v1_3

FORWARD_COOKIE = 0x53444E2026
FORWARD_PRIORITY = 100
BLOCK_PRIORITY = 300
FULL_COOKIE_MASK = 0xFFFFFFFFFFFFFFFF


class ForwardingSwitch(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.datapaths = {}
        self.mac_tables = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofp = datapath.ofproto
        parser = datapath.ofproto_parser
        self._add_flow(
            datapath,
            priority=0,
            match=parser.OFPMatch(),
            actions=[parser.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)],
        )

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            # Clear the old state on reconnection, even when DPID is unchanged.
            if self.datapaths.get(datapath.id) is not datapath:
                self.mac_tables[datapath.id] = {}
                self.on_switch_reset(datapath.id)
            self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER and self.datapaths.get(datapath.id) is datapath:
            self.datapaths.pop(datapath.id, None)
            self.mac_tables.pop(datapath.id, None)
            self.on_switch_reset(datapath.id)

    def on_switch_reset(self, dpid):
        """Override in monitoring applications to discard obsolete counters."""

    def _add_flow(self, datapath, priority, match, actions, cookie=0, hard_timeout=0):
        parser = datapath.ofproto_parser
        instructions = [parser.OFPInstructionActions(datapath.ofproto.OFPIT_APPLY_ACTIONS, actions)]
        datapath.send_msg(parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=instructions,
            cookie=cookie,
            hard_timeout=hard_timeout,
        ))

    def _delete_forwarding_flows(self, datapath):
        ofp, parser = datapath.ofproto, datapath.ofproto_parser
        datapath.send_msg(parser.OFPFlowMod(
            datapath=datapath,
            command=ofp.OFPFC_DELETE,
            cookie=FORWARD_COOKIE,
            cookie_mask=FULL_COOKIE_MASK,
            out_port=ofp.OFPP_ANY,
            out_group=ofp.OFPG_ANY,
            match=parser.OFPMatch(),
        ))

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp, parser = dp.ofproto, dp.ofproto_parser
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None or eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        table = self.mac_tables.setdefault(dp.id, {})
        old_port = table.get(eth.src)
        if old_port is not None and old_port != in_port:
            # Do not leave stale forwarding rules after a MAC move.
            self._delete_forwarding_flows(dp)
        table[eth.src] = in_port

        out_port = table.get(eth.dst, ofp.OFPP_FLOOD)
        actions = [parser.OFPActionOutput(out_port)]
        ip = pkt.get_protocol(ipv4.ipv4)
        if ip is not None and out_port != ofp.OFPP_FLOOD:
            # Unique IPv4 source is present in every forwarding flow; the
            # monitoring application can aggregate by source IP.
            match = parser.OFPMatch(
                in_port=in_port,
                eth_type=ether_types.ETH_TYPE_IP,
                ipv4_src=ip.src,
                eth_dst=eth.dst,
            )
            self._add_flow(dp, FORWARD_PRIORITY, match, actions, cookie=FORWARD_COOKIE)

        data = msg.data if msg.buffer_id == ofp.OFP_NO_BUFFER else None
        dp.send_msg(parser.OFPPacketOut(
            datapath=dp,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data,
        ))
