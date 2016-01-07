"""This module implements the UART_Port class which talks to bioloid
devices using a UART on the pyboard.

"""

import stm
from pyb import UART

class UART_Port:
    """Implements a port which can send or receive commands with a bioloid
    device using the pyboard UART class. This particular class takes
    advantage of some features which are only available on the STM32F4xx processors.
    """

    def __init__(self, uart_num, baud):
        self.uart = UART(uart_num)
        self.baud = 0
        self.set_baud(baud)
        base_str = 'USART{}'.format(uart_num)
        if not hasattr(stm, base_str):
            base_str = 'UART{}'.format(uart_num)
        self.uart_base = getattr(stm, base_str)

        # Set HDSEL (bit 3) in CR3 - which puts the UART in half-duplex
        # mode. This connects Rx to Tx internally, and only enables the
        # transmitter when there is data to send.
        stm.mem16[self.uart_base + stm.USART_CR3] |= (1 << 3)

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

    def set_baud(self, baud):
        """Sets the baud rate.

        Note, the pyb.UART class doesn't have a method for setting the baud
        rate, so we need to reinitialize the uart object.
        """
        if self.baud != baud:
            self.baud = baud
            # The max Return Delay Time is 254 * 2 usec = 508 usec. The default
            # is 500 usec. So using a timeout of 2 ensures that we wait for
            # at least 1 msec before considering a timeout.
            self.uart.init(baudrate=baud, timeout=2)

    def write_packet(self, packet_data):
        """Writes an entire packet to the serial port."""
        _write_packet(self.uart_base, packet_data, len(packet_data))

@micropython.asm_thumb
def _write_packet(r0, r1, r2):   # uart(r0) buf(r1) len(r2)

    # Due to micropython's handling of small ints, bit 31 will always be
    # equal to bit 30, so we need to mask away the high bit for peripheral
    # addresses

    movw(r3, 0xffff)                # uart(r0) &= 0x7fffffff
    movt(r3, 0x7fff)                #
    and_(r0, r3)                    #

    # Disable the Receiver

    ldr(r3, [r0, stm.USART_CR1])    # uart->CR1 &= ~USART_CR1_RE
    mov(r4, 0x04)                   #
    bic(r3, r4)                     #
    str(r3, [r0, stm.USART_CR1])    #

    add(r2, r2, r1)                 # buf_end(r2) = &buf(r1)[len(r2)]
    sub(r2, 1)                      # buf_end--

# loop
    label(loop)
    cmp(r1, r2)
    bhi(endloop)                    # branch if buf > buf_end
    
    # Wait for the Transmit Data Register to be Empty

    mov(r4, 0x80)                   # while ((uart->SR & USART_SR_TXE) == 0) {
# wait_txe                          #   ;
    label(wait_txe)                 #
    ldr(r3, [r0, stm.USART_SR])     #
    tst(r3, r4)                     #
    beq(wait_txe)                   # }

    # Disable interrupts from the time that we write the last character
    # until the tx complete bit is set. This ensures that we re-enable
    # the Rx as soon as possible after the last character has left
    cmp(r1, r2)
    bne(write_dr)                   # if buf ==  buf_end
    cpsid(i)                        #   disable_irq
# write_dr
    label(write_dr)

    # Write one byte to the UART

    ldrb(r3, [r1, 0])               # uart->DR = *buf++
    add(r1, 1)                      #
    str(r3, [r0, stm.USART_DR])     #

    b(loop)
# endloop
    label(endloop)

    # Wait for Transmit Complete (i.e the last bit of transmitted data has left the shift register)

    mov(r4, 0x40)                   # while ((uart->SR & USART_SR_TC) == 0) {
# wait_tx_complete                  #   ;
    label(wait_tx_complete)         #
    ldr(r3, [r0, stm.USART_SR])     #
    tst(r3, r4)                     #
    beq(wait_tx_complete)           # }

    # Re-enable the receiver

    ldr(r3, [r0, stm.USART_CR1])    # uart->CR1 |= USART_CR1_RE
    mov(r4, 0x04)                   #
    orr(r3, r4)                     #
    str(r3, [r0, stm.USART_CR1])    #

    cpsie(i)                        # enable_irq
