from device import Register, Device

class FakeServo(Device):

    def __init__(self, dev_id, dev_port, show_packets=True):

        self.model   = Register(0,    2, Register.RO, init_val=12)
        self.version = Register(2,    1, Register.RO, init_val=1)
        self.led     = Register(0x19, 1, Register.RW, 0, 1, 0, self.led_updated)
        regs = (self.led,)
        super().__init__(dev_port, regs, 24, show_packets)
        self.dev_id.val = dev_id

    def filebase(self):
        return 'fake-servo'

    def led_updated(self, reg):
        print('LED', ('off', 'on')[reg.val])
