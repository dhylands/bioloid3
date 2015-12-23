"""File which parses packets from The Arbotix Commander"""

from dump_mem import dump_mem

class CommanderRx(object):
    """Parses packets from the commmander."""

    NOT_DONE = 0
    SUCCESS = 1
    CHECKSUM = 2

    def __init__(self):
        self.index = -1
        self.checksum = 0
        self.pkt_bytes = bytearray(7)
        self.lookv = 0
        self.lookh = 0
        self.walkv = 0
        self.walkh = 0
        self.button = 0
        self.ext = 0

    def process_byte(self, byte):
        """Runs a single byte through the packet parsing state amchine.

           Returns NOT_DONE if the packet is incomplete.
           Returns SUCCESS is the packet was received successfully.
           Returns CHECKSUM if a checksum error is detected.
        """
        if self.index == -1:
            if byte == 0xff:
                self.index = 0
                self.checksum = 0
        elif self.index == 0:
            if byte != 0xff:
                self.checksum += byte
                self.pkt_bytes[0] = byte
                self.index += 1
        else:
            self.checksum += byte
            self.pkt_bytes[self.index] = byte
            self.index += 1
            if self.index == 7:  # packet complete
                self.index = -1
                if self.checksum & 0xff != 0xff:
                    return CommanderRx.CHECKSUM
                self.lookv = self.pkt_bytes[0] - 128 # 0 - 255 ==> -128 - 127
                self.lookh = self.pkt_bytes[1] - 128
                self.walkv = self.pkt_bytes[2] - 128
                self.walkh = self.pkt_bytes[3] - 128
                self.button = self.pkt_bytes[4]
                self.ext = self.pkt_bytes[5]
                return CommanderRx.SUCCESS
        return CommanderRx.NOT_DONE

