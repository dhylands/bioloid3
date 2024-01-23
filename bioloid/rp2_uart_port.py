"""This module implements the UART_Port class which talks to bioloid
devices using a UART on an RP2040.

"""

from machine import UART, Pin, mem32
import time

from micropython import const

UART0_BASE = const(0x40034000)
UART1_BASE = const(0x40038000)

UART_BASE = (UART0_BASE, UART1_BASE)

UARTCR = const(0x30)
UARTCR_RXE = const(1 << 9)
UARTCR_TXE = const(1 << 8)

UARTFR = const(0x18)
UARTFR_TXFE = const(1 << 7)
UARTFR_BUSY = const(1 << 3)

UARTFR_DONE_MASK = const(UARTFR_TXFE | UARTFR_BUSY)
UARTFR_DONE = const(UARTFR_TXFE)


class UART_Port:
    """Implements a port which can send or receive commands with a bioloid
    device using the rp2040 UART class.
    """

    def __init__(self, uart_num, baud, rx_buf_len=64):
        self.uart = UART(uart_num)
        self.baud = 0
        self.rx_buf_len = 0
        self.set_parameters(baud, rx_buf_len)
        self.uart_base = UART_BASE[uart_num]

        self.uartcr_addr = self.uart_base + UARTCR
        self.uartfr_addr = self.uart_base + UARTFR
        org_uartcr = mem32[self.uartcr_addr]

        # Enable RX and disable Tx
        new_uartcr = (org_uartcr | UARTCR_RXE) & ~UARTCR_TXE
        mem32[self.uartcr_addr] = new_uartcr

        # Remove any characters which might be sitting in the Rx buffer
        while self.uart.any():
            self.uart.read(1)


    def any(self):
        return self.uart.any()

    def read_byte(self):
        """Reads a byte from the bus.

        This function will return None if no character was read within the
        designated timeout (set when we call self.uart.init).
        """
        byte = self.uart.read(1)[0]
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
            self.uart.init(baudrate=baud, timeout=2, rxbuf=rx_buf_len)

    def write_packet(self, packet_data):
        """Writes an entire packet to the serial port."""
        # Disable Rx and enable Tx
        org_uartcr = mem32[self.uartcr_addr]
        new_uartcr = (org_uartcr | UARTCR_TXE) & ~UARTCR_RXE
        mem32[self.uartcr_addr] = new_uartcr

        self.uart.write(packet_data)

        # Wait for the data to be sent
        while mem32[self.uartfr_addr] & UARTFR_DONE_MASK != UARTFR_DONE:
            continue

        # Turn off the Tx and restore Rx
        mem32[self.uartcr_addr] = org_uartcr
