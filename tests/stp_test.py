#!/usr/bin/env python3

from spanningtreemessage import SpanningTreeMessage
from switchyard.lib.userlib import *
from time import sleep
import struct

def mk_stp_pkt(root_id, hops):
    # Function to generate STP packets.
    spm = SpanningTreeMessage(root=root_id, hops_to_root=hops)
    Ethernet.add_next_header_class(EtherType.SLOW, SpanningTreeMessage)
    pkt = Ethernet(src="11:22:11:22:11:22", 
                   dst="22:33:22:33:22:33",
                   ethertype=EtherType.SLOW) + spm
    xbytes = pkt.to_bytes()
    p = Packet(raw=xbytes)
    return p
    
def mk_pkt(hwsrc, hwdst, ipsrc, ipdst, reply=False):
    # Function to generate normal packets.
    ether = Ethernet(src=hwsrc, dst=hwdst, ethertype=EtherType.IP)
    ippkt = IPv4(src=ipsrc, dst=ipdst, protocol=IPProtocol.ICMP, ttl=32)
    icmppkt = ICMP()
    if reply:
        icmppkt.icmptype = ICMPType.EchoReply
    else:
        icmppkt.icmptype = ICMPType.EchoRequest
    return ether + ippkt + icmppkt

def switch_tests():
    # Initialize switch with 3 ports.
    s = TestScenario("Switch Tests")
    s.add_interface('eth0', '10:00:00:00:00:00')
    s.add_interface('eth1', '10:00:00:00:00:01')
    s.add_interface('eth2', '10:00:00:00:00:02')

    # Verify STP packet is flooded out on all ports after initialization.
    stp_pkt = mk_stp_pkt('10:00:00:00:00:00', 0)
    s.expect(PacketOutputEvent("eth0", stp_pkt, "eth1", stp_pkt, "eth2", stp_pkt), "Expecting STP packets")

    # Verify STP packet is flooded out on all ports after 2 seconds.
    s.expect(PacketInputTimeoutEvent(3), "Waiting 2 seconds")
    s.expect(PacketOutputEvent("eth0", stp_pkt, "eth1", stp_pkt, "eth2", stp_pkt), "Expecting STP packets")

    # Receive new STP packet with smaller root.
    stp_pkt = mk_stp_pkt('09:00:00:00:00:00', 0)
    s.expect(PacketInputEvent("eth1", stp_pkt), "Expecting STP packet")

    # Verify updated STP packet is flooded out of all ports except input port
    stp_pkt = mk_stp_pkt('09:00:00:00:00:00', 1)
    s.expect(PacketOutputEvent("eth0", stp_pkt, "eth2", stp_pkt), "Expecting STP packets")
    
    return s

scenario = switch_tests()

