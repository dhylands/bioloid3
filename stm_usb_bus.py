"""This module implements a USB Serial bus class which allows bioloid
devices to be implemented on a MicroPython board.

"""

import stm
from pyb import USB_VCP
from bus import Bus

class USB_Bus(Bus):
    """Implements a Bus which sends commands to a bioloid device using the
       UART class on a pyboard. This particular class takes advantage of some
       features which are only available on the STM32F4xx processors.
    """

    def __init__(self, show_packets=False):
        self.serial = USB_VCP()
        self.recv_buf = bytearray(1)
        self.baud = 0
        super().__init__(self.serial, show_packets)
        # Disable Control-C on the USB serail port in case one comes in the 
        # data.
        self.serial.setinterrupt(-1)

    def read_byte(self):
        """Reads a byte from the bus. This function will return None if
        no character was read within the designated timeout.

        The max Return Delay time is 254 x 2 usec = 508 usec (the
        default is 500 usec). This represents the minimum time between
        receiving a packet and sending a response.

        """
        bytes_read = self.serial.recv(self.recv_buf, timeout=2)
        if bytes_read > 0:
            return self.recv_buf[0]

    def set_baud(self, baud):
        self.baud = baud
        if self.show_packets:
            log('Baud set to: {}'.format(baud))

    def write_byte(self, byte):
        """Writes a single byte back to the host."""
        self.serial.write(bytearray(byte))

    def write_packet(self, packet_data):
        """Function implemented by a derived class which actually writes
        the data to a device.

        """
        self.serial.write(packet_data)

