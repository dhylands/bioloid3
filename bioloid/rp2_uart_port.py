"""This module implements the UART_Port class which talks to bioloid
devices using a UART on an RP2040.

"""

from machine import UART, Pin, mem32
import time

from micropython import const

UART0_BASE = const(0x40034000)
UART1_BASE = const(0x40038000)

UART_BASE = (UART0_BASE, UART1_BASE)

UARTDR = const(0x00)                     # Data Register

UARTCR = const(0x30)                     # Control Register
UARTCR_RXE_BIT = const(9)                # Enabe Receiver bit
UARTCR_TXE_BIT = const(8)                # Enable Transmitter bit
UARTCR_RXE = const(1 << UARTCR_RXE_BIT)  # Enable Receiver Mask
UARTCR_TXE = const(1 << UARTCR_TXE_BIT)  # Enable Trnaamister

UARTFR = const(0x18)         # Flag Register
UARTFR_TXFE = const(1 << 7)  # Transmit FIFO Empty
UARTFR_TXFF = const(1 << 5)  # Transmit FIFO Full
UARTFR_BUSY = const(1 << 3)  # Busy transmitting

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

@micropython.asm_thumb
def _write_packet(r0, r1, r2):   # uart(r0) buf(r1) len(r2)

    # Disable the Receiver and enable the transmitter

    ldr(r3, [r0, UARTCR])       # CR = UART.CR
    mov(r4, 1)
    mov(r5, UARTCR_RXE_BIT)
    lsl(r4, r5)
    bic(r3, r4)                 # CR &= ~ RXE
    mov(r4, 1)
    mov(r5, UARTCR_TXE_BIT)
    lsl(r4, r5)
    orr(r3, r4)                 # CR |= TXE
    str(r3, [r0, UARTCR])       # UART.CR = CR

    add(r2, r2, r1)             # buf_end(r2) = &buf(r1)[len(r2)]
    sub(r2, 1)                  # buf_end--

    # Write the packet data

    label(loop)                 # while (buf != buf_end) {
    cmp(r1, r2)                 #
    bne(endloop)                #   branch if buf == buf_end

    # Wait for space in the FIFO

    mov(r4, UARTFR_TXFF)        #   while ((uart[UARTFR] & UARTFRFF) != 0) {
    label(wait_tx_space)        #
    ldr(r3, [r0, UARTFR])       #
    tst(r3, r4)                 #
    bne(wait_tx_space)          #   }

    # Write a byte

    ldrb(r3, [r1, 0])           #   uart[UARTDR] = *buf++;
    str(r3, [r0, UARTDR])       #
    add(r1, 1)                  #

    bl(loop)                    # } // while (buf < buf_end
    label(endloop)

    # Wait for all transmitting to be complete

    mov(r4, UARTFR_BUSY)        # while ((uart[UARTFR] & UARTFR_BUSY) != 0) {
    label(wait_tx_complete)     #
    ldr(r3, [r0, UARTFR])       #
    tst(r3, r4)                 #
    bne(wait_tx_complete)       # }

    # Disable interrupts
    # Write the last byte
    # wait for all transmitting to be complete

    # Disable the transmitter and re-enable the receiver

    ldr(r3, [r0, UARTCR])       # CR = UART.CR
    mov(r4, 1)
    mov(r5, UARTCR_TXE_BIT)
    lsl(r4, r5)
    bic(r3, r4)                 # CR &= ~ TXE
    mov(r4, 1)
    mov(r5, UARTCR_RXE_BIT)
    lsl(r4, r5)
    orr(r3, r4)                 # CR |= RXE
    str(r3, [r0, UARTCR])       # UART.CR = CR

    # Re-enable interrupts

    # cpsie(i)                    # enable_irq


def test():
    uart_port = UART_Port(0, 1000000)
    packet = bytearray([1, 2, 3, 4])
    #uart_port.write_packet(packet)
    _write_packet(UART0_BASE, packet, len(packet))

test()