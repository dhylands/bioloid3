import struct

from bioloid.bus import Bus
from bioloid.device import Device

from io_adapter import IO_Adapter

class Fake_IO_Adapter(IO_Adapter):

    # LED is at offset 0x19
    NUM_CTL_BYTES = 0x1A

    def __init__(self, dev_id, dev_port, show=Bus.SHOW_NONE):
        super().__init__(dev_port, show)
        self.ctl.dev_id = dev_id

    def packet_received(self, pkt):
        super().packet_received(pkt)
        self.update_adcs()
        self.update_gpios()
