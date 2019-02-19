from switchyard.lib.userlib import *

def main(net):
    my_interfaces = net.interfaces() 
    mymacs = [intf.ethaddr for intf in my_interfaces]

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

        log_debug ("In {} received packet {} on {}".format(net.name, packet, input_port))

        # If src is not mapped, map it while keeping our list at n=5 (remove LRU and set MRU to src if table is full)

        # If src is mapped, make sure the port is correct

        if packet[0].dst in mymacs:
            # Handle packet that is meant for this switch
            log_debug ("Packet intended for me")
        else:
            # Check if the dst is in our port map (if it is and this is not broadcast address, send it there and update MRU to dst)

            # If dst is broadcast or if dst isn't mapped, send to all interfaces (except sending interface)
            for intf in my_interfaces:
                if input_port != intf.name:
                    net.send_packet(intf.name, packet)
    net.shutdown()
