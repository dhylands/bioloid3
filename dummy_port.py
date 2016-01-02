"""This module implements a dummy port class which simulates talking to
devices on the bioloid device.s

"""

import packet

class DummyPort(object):
    """Implements a Bus which just calls dump_mem on the generated packet.
    """

    def __init__(self):
        self.index = -1
        self.response = None

    def read_byte(self):
        """Fakes a timeout."""
        if self.index >= 0:
            byte = self.response[self.index]
            self.index += 1
            if self.index >= len(self.response):
                self.index = -1
            return byte

    def write_packet(self, packet_data):
        """Doesn't do anything. Relies on the Bus class to dump the packet."""
        id = packet_data[2]
        cmd = packet_data[4]
        self.response = None
        if cmd == packet.Command.PING or cmd == packet.Command.WRITE or cmd == packet.Command.REG_WRITE:
            # Fake a success response
            if id > 0 and id < 5:
                self.response = bytearray((0xff, 0xff, id, 2, 0, 0))
        elif cmd == packet.Command.READ:
            # test.py issues a read for the model and version
            self.response = bytearray((0xff, 0xff, id, 5, 0, 12, 0, 0x11, 0))
        if self.response:
            # A response packet was generated, fill in the checksum
            self.response[-1] = ~sum(self.response[2:-1]) & 0xff
            self.index = 0
        else:
            self.index = -1
