import io_adapter_cfg as cfg

class DeviceTypeWriter:

    def __init__(self, fname):
        self.f = open(fname, 'w')

    def write(self, str, offset=None, idx=None):
        if offset is None:
            self.f.write(str)
        elif idx is None:
            self.f.write(str.format(offset))
        else:
            self.f.write(str.format(offset, idx))
        self.f.write('\n')

    def generate(self):
        self.write('DeviceType: io-adapter')
        self.write('Register: 0x00  model                   2 ro')
        self.write('Register: 0x02  version                 1 ro')
        self.write('Register: 0x03  id                      1 rw  0  253')
        self.write('Register: 0x04  baud-rate               1 rw  0  254 BaudRate')
        self.write('Register: 0x05  return-delay-time       1 rw  0  254 RDT')

        self.write('Register: {:#04x}	num-adcs		1 rw  0  254', cfg.NUM_ADCS_OFFSET)
        self.write('Register: {:#04x}	num-gpios		1 rw  0  254', cfg.NUM_GPIOS_OFFSET)

        for idx in range(cfg.NUM_ADCS):
            self.write('Register: {:#04x}	adc-pin-{}		1 rw  0  254 Pin', cfg.ADC_PIN + idx, idx)

        for idx in range(cfg.NUM_GPIOS):
            self.write('Register: {:#04x}  gpio-pin-{}		1 rw  0  254 Pin', cfg.GPIO_PIN + idx, idx)

        for idx in range(cfg.NUM_GPIOS):
            self.write('Register: {:#04x}  gpio-cfg-{}		1 rw  0  254 GpioCfg', cfg.GPIO_CFG + idx, idx)

        for idx in range(cfg.NUM_ADCS):
            self.write('Register: {:#04x}	adc-value-{}		2 ro  0 4095', cfg.ADC_VALUE + idx, idx)

        self.write('Register: {:#04x}  gpio-set		4 rw  0 0xffffffff', cfg.GPIO_SET)
        self.write('Register: {:#04x}  gpio-clear		4 rw  0 0xffffffff', cfg.GPIO_CLEAR)
        self.write('Register: {:#04x}  gpio-odr		4 rw  0 0xffffffff', cfg.GPIO_ODR)
        self.write('Register: {:#04x}  gpio-idr		4 rw  0 0xffffffff', cfg.GPIO_IDR)

        self.write('EndDeviceType')

dtw = DeviceTypeWriter('reg-io-adapter-cfg.bld')
dtw.generate()
