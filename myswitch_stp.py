import datetime
import threading
import time

from switchyard.lib.userlib import *
from spanningtreemessage import SpanningTreeMessage


def mk_stp_pkt(root_id, hops, hwsrc):
    spm = SpanningTreeMessage(root=root_id, hops_to_root=hops)
    Ethernet.add_next_header_class(EtherType.SLOW, SpanningTreeMessage)
    pkt = Ethernet(src=hwsrc,
                   dst="ff:ff:ff:ff:ff:ff",
                   ethertype=EtherType.SLOW) + spm
    xbytes = pkt.to_bytes()
    p = Packet(raw=xbytes)
    return p

def root_stp_flood(do_stp_loop, lock, net, switch_id, current_root, my_interfaces, last_stp):
    t = threading.currentThread()
    while do_stp_loop[0]:
        lock.acquire()

        delta = datetime.datetime.now() - last_stp

        if delta.seconds >= 2:
            if switch_id.raw == current_root.raw:
                last_stp = datetime.datetime.now()

                for intf in my_interfaces:
                    net.send_packet(intf.name, mk_stp_pkt(switch_id, 0, switch_id))

        lock.release()

        time.sleep(0.5)

def main(net):
    my_interfaces = net.interfaces() 
    mymacs = [intf.ethaddr for intf in my_interfaces]
    mymacs.sort(key=lambda x: x.raw)

    broadcast_mac = EthAddr('ff:ff:ff:ff:ff:ff')

    switch_id = mymacs[0]

    current_root = switch_id
    hops_to_root = 0
    root_port = None
    do_stp_loop = [True]

    # A list of 5 ethaddr (ordered from oldest to newest)
    lru_list = []

    # A dictionary of <ethaddr, interface.name> (note: should only contain at most 5 references)
    port_map = {}

    # Dictionary of blocked ports (block when flooding, block on input???)
    blocked_ports = {}

    # Startup flood STP to determine root
    for intf in my_interfaces:
        net.send_packet(intf.name, mk_stp_pkt(current_root, 0, switch_id))

    last_stp = datetime.datetime.now()

    lock = threading.Lock()

    t = threading.Thread(target=root_stp_flood, args=(do_stp_loop, lock, net, switch_id, current_root, my_interfaces, last_stp))
    t.daemon = True
    t.start()

    while True:
        try:
            timestamp,input_port,packet = net.recv_packet()
        except NoPackets:
            continue
        except Shutdown:
            return

        # When we receive an STP packet, parse it
        if packet.has_header(SpanningTreeMessage):
            lock.acquire()

            last_stp = datetime.datetime.now()

            stm = packet.get_header(SpanningTreeMessage)

            # Check if our root assignment is correct (update if it is not)
            if stm.root.raw < current_root.raw:
                # We are locking here so we don't get a flood with mismatching current_roots or errors in net

                # Record the hops to the new root
                current_root = stm.root
                root_port = input_port
                hops_to_root = stm.hops_to_root + 1

                # Increment the packet's hops to root
                stm.hops_to_root = stm.hops_to_root + 1

                # Set the incomming port to forward mode
                if input_port in blocked_ports:
                    del blocked_ports[input_port]

                # Change the src of the packet
                packet[0].src = switch_id

                # Forward the STP packet
                for intf in my_interfaces:
                    if input_port != intf.name:
                        net.send_packet(intf.name, packet)
            elif stm.root.raw == current_root.raw:
                if stm.hops_to_root + 1 < hops_to_root:
                    # Record the hops to the new root
                    root_port = input_port
                    hops_to_root = stm.hops_to_root + 1
                    
                    # Increment the packet's hops to root
                    stm.hops_to_root = stm.hops_to_root + 1

                    # Set the incomming port to forward mode
                    if input_port in blocked_ports:
                        del blocked_ports[input_port]

                    # Change the src of the packet
                    packet[0].src = switch_id

                    # Forward the STP packet
                    for intf in my_interfaces:
                        if input_port != intf.name:
                            net.send_packet(intf.name, packet)
                elif stm.hops_to_root + 1 > hops_to_root:
                    pass
                elif stm.hops_to_root + 1 == hops_to_root:
                    # Block duplicate routes
                    if input_port != root_port:
                        blocked_ports[input_port] = 0
            
            lock.release()

            # Don't process STP packets
            continue

        eth = packet.get_header(Ethernet)

        src = eth.src
        dst = eth.dst

        # If src is not mapped, map it while keeping our list at n=5 (remove LRU and set MRU to src if table is full)
        if not src in port_map:
            lru_list.append(src)

            while len(lru_list) > 5:
                addr = lru_list.pop(0)
                del port_map[addr]
        else:
            lru_list.remove(src)
            lru_list.append(src)
        
        # If src is mapped, make sure the port is correct
        port_map[src] = input_port

        if dst in mymacs:
            # Handle packet that is meant for this switch
            log_debug ("Packet intended for me")
        else:
            # Check if the dst is in our port map (if it is and this is not broadcast address, send it there and update MRU to dst)
            if dst in port_map and not dst == broadcast_mac:
                lru_list.remove(dst)
                lru_list.append(dst)

                net.send_packet(port_map[dst], packet)
            else:
                # If dst is broadcast or if dst isn't mapped, send to all interfaces (except sending interface)
                for intf in my_interfaces:
                    if input_port != intf.name:
                        # Don't flood out a blocked port
                        if not intf.name in blocked_ports:
                            net.send_packet(intf.name, packet)

    # Stop the stp thread
    do_stp_loop[0] = False
    t.join()

    net.shutdown()
