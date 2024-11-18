# type: ignore          - disabble PyLance for this file.
# pylint: skip-file     - duisable pylint for this file.
"""
This module implements the USB_Port class which allows the pyboard to
implement bioloid devices using the pyboard's USB Serial.
"""

from pyb import USB_VCP


class UsbPort:
    """Implements a port which can be used to receive bioloid device commands
    from a host.
    """

    def __init__(self):
        self.usb_serial = USB_VCP()
        self.baud = 0
        self.rx_buf_len = 0
        self.recv_buf = bytearray(1)
        # Disable Control-C on the USB serial port in case one comes in the
        # data.
        self.usb_serial.setinterrupt(-1)

    def any(self):
        """Returns a truthy value if characters are available to be read."""
        return self.usb_serial.any()

    def read_byte(self):
        """Reads a byte from the usb serial device.

        This function will return None if no character was read within the
        designated timeout.

        The max Return Delay time is 254 x 2 usec = 508 usec (the
        default is 500 usec). This represents the minimum time between
        receiving a packet and sending a response.
        """
        bytes_read = self.usb_serial.recv(self.recv_buf, timeout=2)
        if bytes_read > 0:
            return self.recv_buf[0]

    def set_parameters(self, baud, rx_buf_len):
        """Sets the baud rate and the read buffer length.
           Note that for USB Serial, this is essentially
           a no-op.
        """
        self.baud = baud
        self.rx_buf_len = rx_buf_len

    def write_packet(self, packet_data):
        """Writes an entire packet to the serial port."""
        self.usb_serial.write(packet_data)
