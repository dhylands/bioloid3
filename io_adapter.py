"""This module implements a Bioloid device which serves as a bioloid adapter,
   converting USB serial to bioloid serial. It also acts as a bioloid I/O
   devices giving access to analog and digital I/O.
"""

from device import Register, Device
from log import log
import io_adapter_cfg as cfg
import pyb

class IO_Adapter(Device):

    def __init__(self, dev_port, show_packets=False):

        self.model      = Register(Device.MODEL_OFFSET,   2, Register.RO, init_val=123)
        self.version    = Register(Device.VERSION_OFFSET, 1, Register.RO, init_val=1)
        self.max_adcs   = Register(cfg.MAX_ADCS,          1, Register.RO, init_val=9)
        self.max_gpios  = Register(cfg.MAX_GPIOS,         1, Register.RO, init_val=22)

        self.adc_pin = [None] * self.max_adcs.val
        self.adc_value = [None] * self.max_adcs.val
        self.adc = [None] * self.max_adcs.val
        for i in range(self.max_adcs.val):
            self.adc_pin[i] = Register(cfg.ADC_PIN + i,   1, Register.RW, init_val=0, update_fn=self.adc_pin_updated)
            self.adc_value[i] = Register(cfg.ADC_VALUE + i, 2, Register.RW, init_val=0)

        self.gpio_pin = [None] * self.max_gpios.val
        self.gpio_cfg = [None] * self.max_gpios.val
        self.gpio_value = [None] * self.max_gpios.val
        self.gpio = [None] * self.max_gpios.val
        for i in range(self.max_gpios.val):
            self.gpio_pin[i] = Register(cfg.GPIO_PIN + i, 1, Register.RW, init_val=0, update_fn=self.gpio_pin_updated)
            self.gpio_cfg[i] = Register(cfg.GPIO_CFG + i, 1, Register.RW, init_val=cfg.GPIO_CFG_DIR, update_fn=self.gpio_cfg_updated)
            self.gpio_value[i] = Register(cfg.GPIO_VALUE + i, 1, Register.RW, init_val=0, update_fn=self.gpio_value_updated)

        self.gpio_set   = Register(cfg.GPIO_SET,   4, Register.RW, init_val=0, update_fn=self.gpio_set_updated)
        self.gpio_clear = Register(cfg.GPIO_CLEAR, 4, Register.RW, init_val=0, update_fn=self.gpio_clear_updated)
        self.gpio_odr   = Register(cfg.GPIO_ODR,   4, Register.RW, init_val=0, update_fn=self.gpio_odr_updated)
        self.gpio_idr   = Register(cfg.GPIO_IDR,   4, Register.RW, init_val=0)

        regs = [self.model, self.version, self.max_adcs, self.max_gpios]
        regs += self.adc_pin
        regs += self.adc_value
        regs += self.gpio_pin
        regs += self.gpio_cfg
        regs += [self.gpio_set, self.gpio_clear, self.gpio_odr, self.gpio_idr]
        regs += self.gpio_value

        super().__init__(dev_port, regs, cfg.PERSISTENT_BYTES, show_packets)

    def pin_to_str(self, pin_byte):
        """Converts a pin raw value into its string equivalent."""
        port_num = (pin_byte >> 4) & 0x0f
        if port_num > 0:
            return '{:c}{:d}'.format(0x40 + port_num, pin_byte & 0x0f)

    def adc_pin_updated(self, reg):
        """Called when an adc pin is configurd/unconfigured."""
        pin_idx = reg.offset - cfg.ADC_PIN
        pin_str = self.pin_to_str(reg.val)
        if pin_str:
            self.adc[pin_idx] = pyb.ADC(pin_str)
        else:
            self.adc[pin_idx] = None
        if self.show_packets:
            log('Set adc[%d] to %s' % (pin_idx, self.adc[pin_idx]))

    def filebase(self):
        """Returns the base portion of the filename used to store the
           persistent bytes from the control table in.
        """
        return 'io-adapter'

    def gpio_pin_updated(self, reg):
        """Called when an gpio pin is configurd/unconfigured."""
        pin_idx = reg.offset - cfg.GPIO_PIN
        pin_str = self.pin_to_str(reg.val)
        if pin_str:
            self.gpio[pin_idx] = pyb.Pin(pin_str)
            self.gpio_cfg_updated(self.gpio_cfg[pin_idx])
        else:
            self.gpio[pin_idx] = None
        if self.show_packets:
            log('Set gpio[%d] to %s' % (pin_idx, self.gpio[pin_idx]))

    def gpio_cfg_updated(self, reg):
        """Called when a gpio configuration changed."""
        pin_idx = reg.offset - cfg.GPIO_CFG
        gpio_cfg = reg.val
        if self.gpio[pin_idx]:
            if gpio_cfg & cfg.GPIO_CFG_DIR:
                mode = pyb.Pin.IN
            elif gpio_cfg & cfg.GPIO_CFG_OD:
                mode = pyb.Pin.OUT_OD
            else:
                mode = pyb.Pin.OUT_PP
            if gpio_cfg & cfg.GPIO_CFG_PU:
                pull = pyb.Pin.PULL_UPd
            elif gpio_cfg & cfg.GPIO_CFG_PD:
                pull = pyb.Pin.PULL_DOWN
            else:
                pull = pyb.Pin.PULL_NONE
            self.gpio[pin_idx].init(mode, pull)
            if self.show_packets:
                log('Configured gpio[%d] to %s' % (pin_idx, self.gpio[pin_idx]))

    def gpio_set_updated(self, reg):
        """Called when the GPIO_SET register is written."""
        for gpio, pin_idx in self.valid_gpios(reg.val):
            gpio.value(1)
            if self.show_packets:
                log('Set gpio[%d] %s to 1' % (pin_idx, self.gpio[pin_idx]))


    def gpio_clear_updated(self, reg):
        """Called when the GPIO_CLEAR register is written."""
        for gpio, pin_idx in self.valid_gpios(reg.val):
            gpio.value(0)
            if self.show_packets:
                log('Set gpio[%d] %s to 0' % (pin_idx, gpio))

    def gpio_odr_updated(self, reg):
        """Called when the GPIO_ODR register is written."""
        for gpio, pin_idx in self.valid_gpios():
            val = (reg.val >> pin_idx) & 1
            gpio.value(val)
            if self.show_packets:
                log('Set gpio[%d] %s to %d' % (pin_idx, gpio, val))

    def gpio_value_updated(self, reg):
        pin_idx = reg.offset - cfg.GPIO_VALUE
        val = self.gpio_value[pin_idx].val
        if (self.gpio_cfg[pin_idx].val & cfg.GPIO_CFG_DIR) == 0:
            gpio = self.gpio[pin_idx]
            gpio.value(val)
            if self.show_packets:
                log('Set gpio[%d] %s to %d' % (pin_idx, gpio, val))

    def update_adcs(self):
        """Called to update the ADC values (in case they are read)."""
        for adc, idx in self.valid_adcs():
            self.adc_value[idx].val = adc.read()

    def update_gpios(self):
        """Called to update the GPIO values (in case they are read)."""
        idr = 0
        for gpio, pin_idx in self.valid_gpios():
            val = gpio.value()
            if val:
                idr |= (1 << pin_idx)
            if (self.gpio_cfg[pin_idx].val & cfg.GPIO_CFG_DIR) == 1:
                self.gpio_value[pin_idx].value = val
        self.gpio_idr.val = idr

    def valid_adcs(self):
        """A generator that returns valid adc's and their index."""
        for idx in range(self.max_adcs.val):
            adc = self.adc[idx]
            if adc:
                yield adc, idx

    def valid_gpios(self, mask=0xffffffff):
        """A generator that returns valid gpio's and their index."""
        for idx in range(self.max_gpios.val):
            gpio = self.gpio[idx]
            if gpio and (mask & (1 << idx)):
                yield gpio, idx
