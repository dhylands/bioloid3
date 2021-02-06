"""This module implements the SocketServerPort, which basically implements
   a serial like interface using a socket server.
"""

import select


class SocketPort(object):

    def __init__(self, skt):
        self.socket = skt
        self.baud = 0
        self.rx_buf_len = 0

    def read_byte(self, block=False):
        """Reads a byte from the bus. This function will return None if
        no character was read within the designated timeout.

        The max Return Delay time is 254 x 2 usec = 508 usec (the
        default is 500 usec). This represents the minimum time between
        receiving a packet and sending a response.

        """
        if block:
            readable = True
        else:
            readable, _, _ = select.select([self.socket.fileno()], [], [], 0.1)
        if readable:
            data = self.socket.recv(1)
            if data:
                return data[0]

    def set_parameters(self, baud, rx_buf_len):
        """Sets the baud rate and the read buffer length.
           Note that for a network socket this is essentially
           a no-op.
        """
        self.baud = baud
        self.rx_buf_len = rx_buf_len

    def write_packet(self, packet_data):
        """Function implemented by a derived class which actually writes
        the data to a device.

        """
        self.socket.send(packet_data)
