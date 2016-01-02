from io_adapter import IO_Adapter

class Fake_IO_Adapter(IO_Adapter):

    def __init__(self, dev_id, dev_port, show_packets=True):
        super().__init__(dev_port, show_packets)
        self.dev_id.val = dev_id

    def packet_received(self, pkt):
        super().packet_received(pkt)
        self.update_adcs()
        self.update_gpios()
