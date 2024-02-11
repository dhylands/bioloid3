import struct

from bioloid.bus import Bus
from bioloid.device import Device

class FakeServo(Device):

    # LED is at offset 0x19
    NUM_CTL_BYTES = 0x1A

    def __init__(self, dev_id, dev_port, show=Bus.SHOW_NONE):
        self.initial_bytes = bytearray(FakeServo.NUM_CTL_BYTES)
        struct.pack_into('<HBB', self.initial_bytes, 0, 12, 1, dev_id)

        self.ctl_bytes = bytearray(FakeServo.NUM_CTL_BYTES)

        self.notifications = (
            (Device.LED, 1, self.led_updated),
        )
        super().__init__(dev_port, 6, self.initial_bytes, self.ctl_bytes, self.notifications, show)

    def filebase(self):
        return 'fake-servo'

    def led_updated(self, offset, _length):
        print('LED', ('off', 'on')[self.ctl_bytes[offset]])
