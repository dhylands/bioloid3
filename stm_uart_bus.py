"""This module implements a UART bus class which talks to bioloid
devices using a UART on the pyboard.

"""

import stm
from pyb import UART
from bus import Bus

class UART_Bus(Bus):
    """Implements a Bus which sends commands to a bioloid device using the
       UART class on a pyboard. This particular class takes advantage of some
       features which are only available on the STM32F4xx processors.
    """

    def __init__(self, uart_num, baud, show_packets=False):
        # The max Return Delay Time is 254 * 2 usec = 508 usec. The default
        # is 500 usec. So using a timeout of 2 ensures that we wait for
        # at least 1 msec before considering a timeout.
        self.uart = UART(uart_num, baud, timeout=20)
        self.uart_base = getattr(stm, 'USART{}'.format(uart_num))
        self.cr1_addr = self.uart_base + stm.USART_CR1
        self.rx_enabled = True

        # Set the HDSEL bit (3) in CR3 - which puts the UART in half-duplex
        # mode. This connects Rx to Tx internally, and only enables the
        # transmitter when there is data to send.
        stm.mem16[self.uart_base + stm.USART_CR3] |= 0x08

        Bus.__init__(self, self.uart, show_packets)

    def any(self):
        return self.uart.any()

    def read_byte(self):
        """Reads a byte from the bus. This function will return None if
        no character was read within the designated timeout.

        The max Return Delay time is 254 x 2 usec = 508 usec (the
        default is 500 usec). This represents the minimum time between
        receiving a packet and sending a response.

        """
        byte = self.uart.readchar()
        if byte >= 0:
            return byte

    def disable_rx(self):
        stm.mem16[self.cr1_addr] &= ~0x04
        self.rx_enabled = False

    def enable_rx(self):
        stm.mem16[self.cr1_addr] |= 0x04
        self.rx_enabled = True

    def write_byte(self, byte):
        if self.rx_enabled:
            self.disable_rx()
        self.uart.writechar(byte)

    def write_packet(self, packet_data):
        """Function implemented by a derived class which actually writes
        the data to a device.

        """
        #self.disable_rx()
        #self.uart.write(packet_data)
        #self.enable_rx()
        m16 = stm.mem16
        uw = self.uart.write
        ca = self.cr1_addr
        m16[ca] &= ~0x04
        uw(packet_data)
        m16[ca] |= 0x04

