import numpy as np
from gnuradio import gr
import pmt
import threading
import random

class mac_lbt_block(gr.sync_block):
    """
    Embedded MAC Block for Listen-Before-Talk (LBT)
    - Input Stream (in_sig): Carrier Sense (1 = Busy, 0 = Clear)
    - Input Message (tx_in): PDUs (Frames) from DLC layer
    - Output Message (tx_out): PDUs (Frames) cleared for transmission
    """
    def __init__(self, base_backoff=0.02, max_attempts=10):
        gr.sync_block.__init__(
            self,
            name="MAC LBT Router",
            in_sig=[np.byte],  # Reads a byte stream from the Threshold block
            out_sig=None       # No output stream, using messages instead
        )

        # 1. Register Message Ports
        self.message_port_register_in(pmt.intern("tx_in"))
        self.message_port_register_out(pmt.intern("tx_out"))
        
        # 2. Bind the incoming frame handler
        self.set_msg_handler(pmt.intern("tx_in"), self.handle_tx_in)

        # 3. State Variables
        self.channel_busy = False
        self.tx_queue = []
        self.base_backoff = base_backoff
        self.max_attempts = max_attempts
        
        # Asynchronous timer to prevent blocking the GNU Radio scheduler
        self.timer = None
        self.lock = threading.Lock()

    def work(self, input_items, output_items):
        """
        Continuously reads the Carrier Sense stream to update the channel state.
        """
        cs_stream = input_items[0]
        
        if len(cs_stream) > 0:
            with self.lock:
                # If any sample in this incoming chunk is 1, channel is busy
                self.channel_busy = np.any(cs_stream > 0)
                
        return len(cs_stream)

    def handle_tx_in(self, msg):
        """
        Triggered asynchronously whenever a new PDU frame arrives from DLC.
        """
        with self.lock:
            # Add the frame to our queue and initialize its attempt counter
            self.tx_queue.append({'frame': msg, 'attempts': 0})
            self._process_queue()

    def _process_queue(self):
        """
        Evaluates the channel and executes transmission or backoff.
        Must be called while holding the thread lock.
        """
        # If queue is empty or a timer is already running, do nothing
        if not self.tx_queue or self.timer is not None:
            return

        packet = self.tx_queue[0]

        if not self.channel_busy:
            # Channel is CLEAR: Transmit immediately
            self.message_port_pub(pmt.intern("tx_out"), packet['frame'])
            self.tx_queue.pop(0)
            
            # Start a tiny hardware dwell delay before processing the next packet
            self.timer = threading.Timer(0.005, self._on_timer_expired)
            self.timer.start()
        else:
            # Channel is BUSY: Apply exponential backoff
            packet['attempts'] += 1
            
            if packet['attempts'] > self.max_attempts:
                # Max retries hit: Drop the frame
                self.tx_queue.pop(0)
                self.timer = threading.Timer(0.001, self._on_timer_expired)
                self.timer.start()
            else:
                # Calculate random backoff interval
                cw_max = min(16, 2 ** packet['attempts'])
                random_slots = random.randint(1, cw_max)
                backoff_time = random_slots * self.base_backoff
                
                # Start non-blocking backoff timer
                self.timer = threading.Timer(backoff_time, self._on_timer_expired)
                self.timer.start()

    def _on_timer_expired(self):
        """
        Callback triggered when a backoff or dwell timer finishes.
        """
        with self.lock:
            self.timer = None
            self._process_queue()
