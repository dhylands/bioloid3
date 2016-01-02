# Fake classes for testing stuff on the host

class ADC(object):

    def __init__(self, name):
        self.name = name
        self.value = 0

    def read(self):
        self.value += 256
        self.value %= 4096
        return self.value

    def __str__(self):
        return self.name


class Pin(object):

    IN = 'in'
    OUT_PP = 'out_pp'
    OUT_OD = 'out_od'

    PULL_NONE = 'pull_none'
    PULL_UP   = 'pull_up'
    PULL_DOWN = 'pull_down'

    def __init__(self, name):
        self.name = name
        self.mode = Pin.IN
        self.pull = Pin.PULL_NONE
        self.val = 0

    def init(self, mode, pull):
        self.mode = mode
        self.pull = pull

    def value(self, val=None):
        if val is None:
            return self.val
        self.val = val

    def __str__(self):
        return self.name
