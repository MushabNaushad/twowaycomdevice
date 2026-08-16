import time
import random
import threading

import socket

"""
constants and socket configuration
"""
GNU_RADIO_IP = "127.0.0.1" #local host:python to gnu radio
GNU_RADIO_TX_PORT = 5000 #configure in gnu radio source block

PREAMBLE = b'\xAA\x55\xAA\x55'
START_FLAG = b'\x7E'
END_FLAG = b'\x7E'
MAX_FRAME_LEN = 300  # Safeguard: max expected bytes between flags
RX_STALL_TIMEOUT = 0.15     #150ms to clear imcomplete/corrupted frames

rx_buffer = bytearray()     #gloabal buffer for receival
last_rx_data_time = 0.0

#socket setup
tx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

rx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
rx_socket.bind((GNU_RADIO_IP,5001))     #registering port 5001 with the OS to receive through it
rx_socket.settimeout(0.1)   #checks for receiving data for 100ms

"""
state tracker for listen before talk(lbt)
"""
class ChannelState:
    IDLE = "IDLE"
    RECEIVING = "RECEIVING"
    TRANSMITTING = "TRANSMITTING"

class MACStateTracker:
    def __init__(self, sifs_gap = 0.015):       #sifs:short inter frame gap: need to finetune T(processing + turnaround + propagation)
        self.state = ChannelState.IDLE
        self.last_rx_endtime = 0.0
        self.sifs_gap = sifs_gap   #min quiet time required after reception
        self.lock = threading.Lock()

    def set_state(self, new_state):
        with self.lock:
            if self.state == ChannelState.RECEIVING and new_state == ChannelState.IDLE:
                self.last_rx_endtime = time.time()
            self.state = new_state

    def is_channel_free(self):
        with self.lock:
            if self.state != ChannelState.IDLE:
                return False
            
            if (time.time() - self.last_rx_endtime) < self.sifs_gap:
                return False
            return True
        

"""
TRANSMIT(TX) FUNCTIONS
"""
#************************************************************************************************#
def addressing(payload, dest_id, src_id):       #need payload from dlc layer

    dest_id_bytes = dest_id.to_bytes(1, byteorder='big')  #or dest_id_bytes = bytes([0x41])
    src_id_bytes = src_id.to_bytes(1, byteorder='big')     #or src_id_bytes = bytes([0x42])


    payload_for_bit_stuffing = dest_id_bytes + src_id_bytes + payload

    return payload_for_bit_stuffing


#***********************************************************************************************#
def final_framing(bit_stuffed_part):        #need bit_stuffed_part from dlc layer

    preamble = b'\xAA\x55\xAA\x55'
    start_flag = end_flag = b'\x7E'
    final_frame = preamble + start_flag + bit_stuffed_part + end_flag

    return final_frame  #ready to be sent to gnu radio source


#***********************************************************************************************#



def pass_to_udp_source(final_frame):
    #adress socket and pass to udp source in  gnu radio
    tx_socket.sendto(final_frame, (GNU_RADIO_IP, GNU_RADIO_TX_PORT))



#***********************************************************************************************#
def transmit_after_lbt(final_frame, channel_tracker, max_attempts = 10):
    base_backoff = 0.02     #20ms

    for attempt in range(max_attempts):
        #listen,check if channel free
        if channel_tracker.is_channel_free():
            #acquire channel and transmit
            channel_tracker.set_state(ChannelState.TRANSMITTING)

            pass_to_udp_source(final_frame)

            time.sleep(0.005)       #for physical layer actions

            channel_tracker.set_state(ChannelState.IDLE)
            return True
        #channel busy, contention window expands with each failed attempt
        cw_max = min(16, 2 ** attempt)
        random_slots = random.randint(1,cw_max)
        backoff_time = random_slots * base_backoff

        time.sleep(backoff_time)
    #transmission failed
    return False
#***********************************************************************************************#
"""
RECEIVE(RX) FUNCTIONS
"""



def receive_from_udp_sink(channel_tracker):
    #detect preamble, store recieved part of preamble and wait for rest
    #buffer emptying when garbage is stored and rest of the packet is lost (specified bytes after preamble)
    
    global rx_buffer, last_rx_data_time

    #read raw new bytes from gnu radio and append to buffer
    try:
        raw_chunk, _ = rx_socket.recvfrom(2048)     #2048 = buffer size for a single read operation
        rx_buffer.extend(raw_chunk)
    except socket.timeout:
        pass #no new bytes arrived

    #: Reset buffer if partial frame has stalled
    if len(rx_buffer) > 0 and (time.time() - last_rx_data_time) > RX_STALL_TIMEOUT:
        rx_buffer.clear()
        channel_tracker.set_state(ChannelState.IDLE)
        return None

    preamble_idx = rx_buffer.find(PREAMBLE)     #search for preamble
    if preamble_idx == -1:
        # Preamble not found; keep only the last few bytes (in case preamble is split)
        if len(rx_buffer) > len(PREAMBLE):
            rx_buffer = rx_buffer[-(len(PREAMBLE) - 1):]
            channel_tracker.set_state(ChannelState.IDLE)
        return None
    
    channel_tracker.set_state(ChannelState.RECEIVING)    
    rx_buffer = rx_buffer[preamble_idx:]    #discard noise before preamble

    #verify start flag starts immediately after preamble
    start_flag_pos = len(PREAMBLE)
    if len(rx_buffer) <= start_flag_pos:
        return None     #wait for more data
    
    if rx_buffer[start_flag_pos:start_flag_pos + 1] != START_FLAG:
        #invalid frame structure;drop preamble byte and continue search
        rx_buffer = rx_buffer[1:]
        channel_tracker.set_state(ChannelState.IDLE)
        return None
    
    data_start = start_flag_pos + 1
    end_flag_idx = rx_buffer.find(END_FLAG, data_start)

    if end_flag_idx == -1:
        #end flag not arrived yet, if buffer grew too large, frame is corrupted
        if len(rx_buffer) > MAX_FRAME_LEN:
            rx_buffer = rx_buffer[start_flag_pos:]      #reset and clear corrupted segment
            channel_tracker.set_state(ChannelState.IDLE)
        return None
    
    rcvd_bitstuffed_payload_plus_crc = bytes(rx_buffer[data_start:end_flag_idx]) # extract in between start and end flags from buffer
    
    rx_buffer = rx_buffer[end_flag_idx + 1:]    #flush the extracted frame out of the buffer

    channel_tracker.set_state(ChannelState.IDLE)
    return rcvd_bitstuffed_payload_plus_crc     #pass payload+crc(bit stuffed) to dlc layer for debitstuffing



#***********************************************************************************************#
def verify_addressing(data,my_node_id):     #pass in the debitstuffed payload+crc from dlc layer
    """
    data format: [Dest ID (1B) | Src ID (1B) | Encrypted Payload + CRC]
    """

    if len(data) < 2:
        return None,None
    
    dest_adrress = data[0]
    src_address = data[1]

    if (dest_adrress == my_node_id or dest_adrress == 0xFF):
        rcvd_payload_plus_crc = data[2:]
        return src_address, rcvd_payload_plus_crc       #outputs source address and received payload+crc
    # Silently discard packets addressed to other nodes
    return None, None




