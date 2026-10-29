"""Optional real OVS/Mininet smoke test; start OSKen first.

Examples:
  sudo python3 tests/integration/check_live.py --task 1
  sudo python3 tests/integration/check_live.py --task 2

Not executed by plain pytest. Requires OVS, Mininet, root, ping and controller.
"""
import argparse
import json
import os
import re
from functools import partial
import subprocess
import time
from pathlib import Path

from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.topo import SingleSwitchTopo

ROOT = Path(__file__).resolve().parents[2]


def get_source_rate(path, ip):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data['switches']['1']['sources'][ip]
    except (OSError, KeyError, ValueError):
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', type=int, choices=[1, 2], required=True)
    options = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit('Run this integration test with sudo.')

    data = json.loads((ROOT / 'config/monitor.json').read_text())
    metrics_path = ROOT / data['metrics_path']
    metrics_path.unlink(missing_ok=True)
    net = Mininet(topo=SingleSwitchTopo(k=4), controller=None,
                  switch=partial(OVSSwitch, protocols='OpenFlow13'), autoSetMacs=True)
    net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6653)
    net.start()
    try:
        switch = net.get('s1')
        h1, h4 = net.get('h1', 'h4')
        time.sleep(2)
        ping = h1.cmd('ping -c 5 -W 1 10.0.0.4')
        received = re.search(r'(\d+) received', ping)
        if received is None or int(received.group(1)) == 0:
            raise AssertionError('No base connectivity:\n' + ping)
        print('PASS: basic IPv4 connectivity')

        # Generate enough packets for several actual FlowStats intervals.
        proc = h1.popen(['ping', '-i', '0.005', '-c', '800', '10.0.0.4'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        max_pps = 0.0
        saw_block = False
        try:
            end = time.monotonic() + 8.0
            while time.monotonic() < end:
                time.sleep(0.5)
                rate = get_source_rate(metrics_path, '10.0.0.1')
                if rate:
                    max_pps = max(max_pps, rate['pps'])
                if options.task == 2:
                    flows = switch.cmd('ovs-ofctl -O OpenFlow13 dump-flows s1')
                    if 'priority=300' in flows and 'nw_src=10.0.0.1' in flows and 'actions=drop' in flows:
                        saw_block = True
                        break
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

        assert max_pps > 0, 'No positive measured packet rate in metrics.json'
        print(f'PASS: measured traffic, max observed pps={max_pps:.2f}')
        if options.task == 2:
            assert saw_block, 'Expected temporary OpenFlow drop rule on high PPS'
            print('PASS: temporary drop rule installed for anomalous source')
    finally:
        net.stop()


if __name__ == '__main__':
    main()
