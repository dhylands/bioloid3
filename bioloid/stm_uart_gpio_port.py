"""This module implements the UART_Port class which talks to bioloid
devices using a UART on the pyboard.

"""

import stm
from pyb import UART

class UART_GPIO_Port:
    """Implements a port which can send or receive commands with a bioloid
    device using the pyboard UART class. This class assumes that there is
    an active HIGH GPIO line used to indicate transmitting (i.e. connected
    to something like an external 74AHCT1G126)
    """

    def __init__(self, uart_num, baud, control_pin, rx_buf_len=64):
        self.uart = UART(uart_num)
        self.control_pin = control_pin
        self.baud = 0
        self.rx_buf_len = 0
        self.set_parameters(baud, rx_buf_len)
        base_str = 'USART{}'.format(uart_num)
        if not hasattr(stm, base_str):
            base_str = 'UART{}'.format(uart_num)
        self.uart_base = getattr(stm, base_str)

    def any(self):
        return self.uart.any()

    def read_byte(self):
        """Reads a byte from the bus.

        This function will return None if no character was read within the
        designated timeout (set when we call self.uart.init).
        """
        byte = self.uart.readchar()
        if byte >= 0:
            return byte

    def set_parameters(self, baud, rx_buf_len):
        """Sets the baud rate and the read buffer length.

        Note, the pyb.UART class doesn't have a method for setting the baud
        rate, so we need to reinitialize the uart object.
        """
        if baud != self.baud or rx_buf_len != self.rx_buf_len:
            self.baud = baud
            self.rx_buf_len = rx_buf_len
            # The max Return Delay Time is 254 * 2 usec = 508 usec. The default
            # is 500 usec. So using a timeout of 2 ensures that we wait for
            # at least 1 msec before considering a timeout.
            self.uart.init(baudrate=baud, timeout=2, read_buf_len=rx_buf_len)

    def write_packet(self, packet_data):
        """Writes an entire packet to the serial port."""
        _write_packet(self.uart_base, packet_data, len(packet_data), self.control_pin.gpio() & 0x7fffffff, self.control_pin.pin())


TXE_MASK = const(1 << 7)
TC_MASK = const(1 << 6)

@micropython.asm_thumb
def disable_irq():
    cpsid(i)

@micropython.asm_thumb
def enable_irq():
    cpsie(i)

@micropython.viper
def _write_packet(uart_base: int, data: ptr8, data_len: int, gpio_base: int, pin: int):
    pin_mask = int(1 << pin)

    # Enable the external transmit buffer by setting the GPIO line high
    gpio_BSRR = ptr16(gpio_base + stm.GPIO_BSRR)
    gpio_BSRR[0] = pin_mask

    uart_SR = ptr16(uart_base + stm.USART_SR)
    uart_DR = ptr16(uart_base + stm.USART_DR)

    # Send the data
    for idx in range(data_len):
        # Wait for the Transmit Data Register to be Empty
        while uart_SR[0] & TXE_MASK == 0:
            pass
        if idx == data_len - 1:
            # We disable interrupts from the beginning of the last character
            # until we drop the GPIO line (i.e. about 1 character time) in
            # order to assure that the GPIO gets lowered as soon as possible
            # after the last character gets sent.
            disable_irq()
        uart_DR[0] = data[idx]

    # Wait for Transmit Complete (i.e the last bit of transmitted data has
    # left the shift register)
    while uart_SR[0] & TC_MASK == 0:
        pass

    # Disable the external transmit buffer by setting the GPIO line low
    # The time from the end of the stop bit to the falling edge of the
    # GPIO is about 0.25 usec
    gpio_BSRR[1] = pin_mask
    enable_irq()
