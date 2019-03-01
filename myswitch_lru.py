from switchyard.lib.userlib import *

def main(net):
    my_interfaces = net.interfaces() 
    mymacs = [intf.ethaddr for intf in my_interfaces]

    broadcast_mac = EthAddr('ff:ff:ff:ff:ff:ff')

    # A list of 5 ethaddr (ordered from oldest to newest)
    lru_list = []

    # A dictionary of <ethaddr, interface.name> (note: should only contain at most 5 references)
    port_map = {}

    while True:
        try:
            timestamp,input_port,packet = net.recv_packet()
        except NoPackets:
            continue
        except Shutdown:
            return

        src = packet[0].src
        dst = packet[0].dst

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
                        net.send_packet(intf.name, packet)
    net.shutdown()
