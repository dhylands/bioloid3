"""This module implements a serial bus class which talks to bioloid
devices through a serial port.

"""

import serial
from bus import Bus


class SerialBus(Bus):
    """Implements a BioloidBus which sends commands to a bioloid device
    via a BioloidSerialPort.

    """

    def __init__(self, port, baud=1000000, show_packets=False):
        Bus.__init__(self, show_packets)
        self.serial_port = serial.Serial(port=port,
                                         baudrate=baud,
                                         timeout=0.1,
                                         bytesize=serial.EIGHTBITS,
                                         parity=serial.PARITY_NONE,
                                         stopbits=serial.STOPBITS_ONE,
                                         xonxoff=False,
                                         rtscts=False,
                                         dsrdtr=False)

    def read_byte(self):
        """Reads a byte from the bus. This function will return None if
        no character was read within the designated timeout.

        The max Return Delay time is 254 x 2 usec = 508 usec (the
        default is 500 usec). This represents the minimum time between
        receiving a packet and sending a response.

        """
        data = self.serial_port.read()
        if data:
            return data[0]
        return None

    def write_packet(self, packet_data):
        """Function implemented by a derived class which actually writes
        the data to a device.

        """
        self.serial_port.write(packet_data)
