"""This module implements a Bioloid device which serves as a bioloid adapter,
   converting USB serial to bioloid serial. It also acts as a bioloid I/O
   devices giving access to analog and digital I/O.
"""

from bioloid.device import Device
from bioloid.bus import Bus
from bioloid.log import log
import io_adapter_cfg as cfg
import pyb
import ctypes

class IO_Adapter(Device):

    def __init__(self, dev_port, show=Bus.SHOW_NONE):

        # yapf: disable
        desc = {
            'model':        ctypes.UINT16 | 0,
            'version':      ctypes.UINT8 | 2,
            'dev_id':       ctypes.UINT8 | 3,
            'baud_rate':    ctypes.UINT8 | 4,
            'rdt':          ctypes.UINT8 | 5,
            'num_adcs':     ctypes.UINT8 | cfg.NUM_ADCS_OFFSET,
            'num_gpios':    ctypes.UINT8 | cfg.NUM_GPIOS_OFFSET,
            'adc_pin':      (ctypes.ARRAY | cfg.ADC_PIN, cfg.NUM_ADCS, {
                'port':         ctypes.BFUINT8 | 0 | 4 << ctypes.BF_POS | 4 << ctypes.BF_LEN,
                'pin':          ctypes.BFUINT8 | 0 | 0 << ctypes.BF_POS | 4 << ctypes.BF_LEN,
            }),
            'gpio_pin':     (ctypes.ARRAY | cfg.GPIO_PIN, cfg.NUM_GPIOS, {
                'port':         ctypes.BFUINT8 | 0 | 4 << ctypes.BF_POS | 4 << ctypes.BF_LEN,
                'pin':          ctypes.BFUINT8 | 0 | 0 << ctypes.BF_POS | 4 << ctypes.BF_LEN,
            }),
            'gpio_cfg':     (ctypes.ARRAY | cfg.GPIO_CFG, cfg.NUM_GPIOS, {
                'dir':          ctypes.BFUINT8 | 0 | 0 << ctypes.BF_POS | 1 << ctypes.BF_LEN,
                'pu':           ctypes.BFUINT8 | 0 | 1 << ctypes.BF_POS | 1 << ctypes.BF_LEN,
                'pd':           ctypes.BFUINT8 | 0 | 2 << ctypes.BF_POS | 1 << ctypes.BF_LEN,
                'od':           ctypes.BFUINT8 | 0 | 3 << ctypes.BF_POS | 1 << ctypes.BF_LEN,
            }),

            # End of persistent values
            'adc_value':    (ctypes.ARRAY | cfg.ADC_VALUE, ctypes.UINT16 | cfg.NUM_ADCS),
            'gpio_set':     ctypes.UINT32 | cfg.GPIO_SET,
            'gpio_clear':   ctypes.UINT32 | cfg.GPIO_CLEAR,
            'gpio_odr':     ctypes.UINT32 | cfg.GPIO_ODR,
            'gpio_idr':     ctypes.UINT32 | cfg.GPIO_IDR,
        }
        # yapf: enable

        initial_bytes = bytearray(cfg.NUM_CTL_BYTES)
        init = ctypes.struct(ctypes.addressof(initial_bytes), desc,
                             ctypes.LITTLE_ENDIAN)
        init.model = 123
        init.version = 1
        init.dev_id = Device.INITIAL_DEV_ID
        init.baud_rate = Device.INITIAL_BAUD
        init.rdt = Device.INITIAL_RDT
        for idx in range(cfg.NUM_GPIOS):
            init.gpio_cfg[idx].dir = 1

        ctl_bytes = bytearray(cfg.NUM_CTL_BYTES)
        self.ctl = ctypes.struct(ctypes.addressof(ctl_bytes), desc,
                                 ctypes.LITTLE_ENDIAN)

        notifications = (
            (Device.LED, 1, self.led_updated),
            (cfg.ADC_PIN, cfg.NUM_ADCS, self.adc_pin_updated),
            (cfg.GPIO_PIN, cfg.NUM_GPIOS, self.gpio_pin_updated),
            (cfg.GPIO_CFG, cfg.NUM_GPIOS, self.gpio_cfg_updated),
            (cfg.GPIO_SET, 4, self.gpio_set_updated),
            (cfg.GPIO_CLEAR, 4, self.gpio_clear_updated),
            (cfg.GPIO_ODR, 4, self.gpio_odr_updated),
        )

        self.adc = [None] * cfg.NUM_ADCS
        self.gpio = [None] * cfg.NUM_GPIOS

        super().__init__(dev_port, cfg.PERSISTENT_BYTES, initial_bytes,
                         ctl_bytes, notifications, show)

    def pin_to_str(self, pin):
        """Converts a pin raw value into its string equivalent."""
        if pin.port > 0:
            return '{:c}{:d}'.format(0x40 + pin.port, pin.pin)

    def led_updated(self, offset, _length):
        if self.show & Bus.SHOW_COMMANDS:
            log('LED', ('off', 'on')[self.ctl_bytes[offset]])

    def adc_pin_updated(self, offset, length):
        """Called when an adc pin is configurd/unconfigured."""
        for ofs in range(offset, offset + length):
            pin_idx = ofs - cfg.ADC_PIN
            pin_str = self.pin_to_str(self.ctl.adc_pin[pin_idx])
            if pin_str:
                self.adc[pin_idx] = pyb.ADC(pin_str)
            else:
                self.adc[pin_idx] = None
            if self.show & Bus.SHOW_COMMANDS:
                log('Set adc[%d] to %s' % (pin_idx, self.adc[pin_idx]))

    def filebase(self):
        """Returns the base portion of the filename used to store the
           persistent bytes from the control table in.
        """
        return 'io-adapter'

    def gpio_pin_updated(self, offset, length):
        """Called when an gpio pin is configurd/unconfigured."""
        for ofs in range(offset, offset + length):
            pin_idx = ofs - cfg.GPIO_PIN
            pin_str = self.pin_to_str(self.ctl.gpio_pin[pin_idx])
            if pin_str:
                self.gpio[pin_idx] = pyb.Pin(pin_str)
                self.gpio_cfg_updated(cfg.GPIO_CFG + pin_idx, 1)
            else:
                self.gpio[pin_idx] = None
            if self.show & Bus.SHOW_COMMANDS:
                log('Set gpio[%d] to %s' % (pin_idx, self.gpio[pin_idx]))

    def gpio_cfg_updated(self, offset, length):
        """Called when a gpio configuration changed."""
        for ofs in range(offset, offset + length):
            pin_idx = ofs - cfg.GPIO_CFG
            gpio_cfg = self.ctl.gpio_cfg[pin_idx]
            if self.gpio[pin_idx]:
                if gpio_cfg.dir:
                    mode = pyb.Pin.IN
                elif gpio_cfg.od:
                    mode = pyb.Pin.OUT_OD
                else:
                    mode = pyb.Pin.OUT_PP
                if gpio_cfg.pu:
                    pull = pyb.Pin.PULL_UP
                elif gpio_cfg.pd:
                    pull = pyb.Pin.PULL_DOWN
                else:
                    pull = pyb.Pin.PULL_NONE
                self.gpio[pin_idx].init(mode, pull)
                if self.show & Bus.SHOW_COMMANDS:
                    log('Configured gpio[%d] to %s' %
                        (pin_idx, self.gpio[pin_idx]))

    def gpio_set_updated(self, offset, length):
        """Called when the GPIO_SET register is written."""
        for gpio, pin_idx in self.valid_gpios(self.ctl.gpio_set):
            gpio.value(1)
            if self.show & Bus.SHOW_COMMANDS:
                log('Set gpio[%d] %s to 1' % (pin_idx, self.gpio[pin_idx]))

    def gpio_clear_updated(self, offset, length):
        """Called when the GPIO_CLEAR register is written."""
        for gpio, pin_idx in self.valid_gpios(self.ctl.gpio_clear):
            gpio.value(0)
            if self.show & Bus.SHOW_COMMANDS:
                log('Set gpio[%d] %s to 0' % (pin_idx, gpio))

    def gpio_odr_updated(self, offset, length):
        """Called when the GPIO_ODR register is written."""
        for gpio, pin_idx in self.valid_gpios():
            val = (self.ctl.gpio_odr >> pin_idx) & 1
            gpio.value(val)
            if self.show & Bus.SHOW_COMMANDS:
                log('Set gpio[%d] %s to %d' % (pin_idx, gpio, val))

    def update_adcs(self):
        """Called to update the ADC values (in case they are read)."""
        for adc, idx in self.valid_adcs():
            self.ctl.adc_value[idx] = adc.read()

    def update_gpios(self):
        """Called to update the GPIO values (in case they are read)."""
        idr = 0
        for gpio, pin_idx in self.valid_gpios():
            val = gpio.value()
            if val:
                idr |= (1 << pin_idx)
        self.ctl.gpio_idr = idr

    def valid_adcs(self):
        """A generator that returns valid adc's and their index."""
        for idx in range(cfg.NUM_ADCS):
            adc = self.adc[idx]
            if adc:
                yield adc, idx

    def valid_gpios(self, mask=0xffffffff):
        """A generator that returns valid gpio's and their index."""
        for idx in range(cfg.NUM_GPIOS):
            gpio = self.gpio[idx]
            if gpio and (mask & (1 << idx)):
                yield gpio, idx
