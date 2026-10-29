"""Launch a Mininet CLI with one OpenFlow 1.3 OVS and four hosts."""
import os
from functools import partial

from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.topo import SingleSwitchTopo


def main():
    if os.geteuid() != 0:
        raise SystemExit('Mininet requires root; use sudo.')
    topo = SingleSwitchTopo(k=4)
    network = Mininet(topo=topo, controller=None, switch=partial(OVSSwitch, protocols='OpenFlow13'),
                      autoSetMacs=True, autoStaticArp=False)
    network.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6653)
    network.start()
    try:
        print('\nHosts: h1=10.0.0.1, h2=10.0.0.2, h3=10.0.0.3, h4=10.0.0.4')
        print('Test: h1 ping -i 0.01 -c 300 10.0.0.4')
        CLI(network)
    finally:
        network.stop()


if __name__ == '__main__':
    setLogLevel('info')
    main()
