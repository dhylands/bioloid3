"""This module defines Packet class used to send packets to and from the
devices on the bioloid bus.

"""

from .dump_mem import dump_mem


class Id:
    """Constants for reserved IDs."""

    BROADCAST = 0xFE
    INVALID = 0xFF

    idStr = {
        BROADCAST:  "BROADCAST",
        INVALID:    "INVALID"
    }

    def __init__(self, dev_id):
        self.dev_id = dev_id

    def __repr__(self):
        """Return a python parsable representation of ourselves."""
        return "Id(0x%02x)" % self.dev_id

    def __str__(self):
        """Return a human readable representation of ourselves."""
        if self.dev_id in Id.idStr:
            return Id.idStr[self.dev_id]
        return "0x%02x" % self.dev_id

    def get_dev_id(self):
        """Returns the device Id that this object represents."""
        return self.dev_id


class Command:
    """Constants for the commands sent in a packet."""

    PING = 0x01         # Used to obatin a status packet
    READ = 0x02         # Read values from the control table
    WRITE = 0x03        # Write values to control table
    REG_WRITE = 0x04    # Prime values to write when ACTION sent
    ACTION = 0x05       # Triggers REG_WRITE
    RESET = 0x06        # Changes control values back to factory defaults
    SYNC_WRITE = 0x83   # Writes values to many devices

    cmd_str = {
        PING:        "PING",
        READ:        "READ",
        WRITE:       "WRITE",
        REG_WRITE:   "REG_WRITE",
        ACTION:      "ACTION",
        RESET:       "RESET",
        SYNC_WRITE:  "SYNC_WRITE"
    }
    cmd_id = None

    def __init__(self, cmd):
        self.cmd = cmd

    def __repr__(self):
        """Return a python parsable representation of ourselves."""
        return 'Command(0x%02x)'.format(self.cmd)

    def __str__(self):
        """Return a human readable representation of ourselves."""
        if self.cmd in Command.cmd_str:
            return Command.cmd_str[self.cmd]
        return '0x%02x'.format(self.cmd)

    @staticmethod
    def parse(string):
        """Parses a string to convert it ito a command."""
        if Command.cmd_id is None:
            Command.cmd_id = {}
            for cmd_id in Command.cmd_str:
                cmd_str = Command.cmd_str[cmd_id].lower()
                Command.cmd_id[cmd_str] = cmd_id
        string = string.lower()
        if string in Command.cmd_id:
            return Command.cmd_id[string]
        raise ValueError("Unrecognized command: '{}'".format(string))


class ErrorCode:
    """Constants for the error codes used in response packets."""

    RESERVED = 0x80         # Reserved - set to zero
    INSTRUCTION = 0x40      # Undefined instruction
    OVERLOAD = 0x20         # Max torque can't control applied load
    CHECKSUM = 0x10         # Checksum of instruction packet incorrect
    RANGE = 0x08            # Instruction is out of range
    OVERHEATING = 0x04      # Internal temperature is too high
    ANGLE_LIMIT = 0x02      # Goal position is outside of limit range
    INPUT_VOLTAGE = 0x01    # Input voltage out of range
    NONE = 0x00             # No Error

    NOT_DONE = 0x100        # Special error code used by packet::ProcessChar
    TIMEOUT = 0x101         # Indicates that a timeout occurred while waiting
                            # for a reply
    TOO_MUCH_DATA = 0x102   # Packet storage isn't big enough

    lookup = ["InputVoltage", "AngleLimit", "OverHeating", "Range",
              "Checksum", "Overload", "Instruction", "Reserved"]
    lookupLower = None

    def __init__(self, error_code):
        self.error_code = error_code

    def __repr__(self):
        """Return a python parsable representation of ourselves."""
        return "ErrorCode(0x%02x)" % self.error_code

    def __str__(self):
        """Return a human readable representation of ourselves."""
        if self.error_code == ErrorCode.NONE:
            return "None"
        if self.error_code == ErrorCode.NOT_DONE:
            return "NotDone"
        if self.error_code == ErrorCode.TIMEOUT:
            return "Timeout"
        if self.error_code == ErrorCode.TOO_MUCH_DATA:
            return "TooMuchData"
        if self.error_code == 0x7f:
            return "All"
        result = []
        for i in range(len(ErrorCode.lookup)):
            if self.error_code & (1 << i):
                result.append(ErrorCode.lookup[i])
        return ",".join(result)

    @staticmethod
    def parse(error_str):
        """Parses a comma separated list of error strings to produce
        the corresponding mask or value.

        """
        if error_str.lower() == "none":
            return 0
        if error_str.lower() == "all":
            return 0x7f
        if ErrorCode.lookupLower is None:
            ErrorCode.lookupLower = [s.lower() for s in ErrorCode.lookup]
        result = 0
        for word in error_str.split(','):
            word = word.strip().lower()
            if word not in ErrorCode.lookupLower:
                raise ValueError("Invalid mask string '%s'" % word)
            result |= (1 << ErrorCode.lookupLower.index(word))
        return result


class Packet:
    """Encapsulates the packets sent to and from the bioloid device."""

    def __init__(self, status_packet=False):
        """Constructs a packet from a buffer, if provided."""
        self.cmd = None
        self.dev_id = None
        self.checksum = 0
        self.param = None
        self.length = None
        self.pkt_bytes = None
        self.byte_index = 0
        self.status_packet = status_packet

    def param_byte(self, idx):
        """Returns the idx'th parameter byte."""
        return self.pkt_bytes[5 + idx]

    def params(self):
        """Returns all of the parameter bytes."""
        return self.pkt_bytes[5:5 + self.length - 2]

    def param_len(self):
        """Returns the length of the parameter bytes."""
        return self.length - 2

    def error_code(self):
        """Returns the error code, from a response packet, which
        occupies the same position as the command.

        """
        return self.cmd

    def error_code_str(self):
        """Returns a string representation of the error code."""
        return str(ErrorCode(self.cmd))

    def process_byte(self, byte):
        """Runs a single byte through the packet parsing state
        machine.

        Returns ErrorCode.NOT_DONE if the packet is incomplete,
        ErrorCode.NONE if the packet was received successfully, and
        ErrorCode.CHECKSUM if a checksum error is detected.
        """
        if self.byte_index == 0:    # 0xFF
            if byte != 0xff:
                return ErrorCode.NOT_DONE
        elif self.byte_index == 1:  # 0xFF
            if byte != 0xff:
                # reset length so we go back to looking for 2 0xff's in a row
                self.byte_index = 0
                return ErrorCode.NOT_DONE
        elif self.byte_index == 2:  # Device ID
            if byte == 0xff:
                # Leave the length alone
                return ErrorCode.NOT_DONE
            self.dev_id = byte
            self.checksum = 0
        elif self.byte_index == 3:  # Length
            self.length = byte
            # the length includes the length byte and the command, but
            # does not include the initial 2 0xff's, the device_id or checksum
            self.pkt_bytes = bytearray(self.length + 4)
            self.pkt_bytes[0] = 0xff
            self.pkt_bytes[1] = 0xff
            self.pkt_bytes[2] = self.dev_id
            self.pkt_bytes[3] = self.length
        elif self.byte_index == 4:  # Cmd
            self.cmd = byte
            self.pkt_bytes[4] = byte
        elif (self.byte_index + 1) < len(self.pkt_bytes):
            self.pkt_bytes[self.byte_index] = byte
        else:
            self.pkt_bytes[self.byte_index] = byte
            self.byte_index = 0
            self.checksum = ~self.checksum & 0xff
            if self.checksum == byte:
                return ErrorCode.NONE
            return ErrorCode.CHECKSUM
        if self.byte_index != 4 or not self.status_packet:
            self.checksum += byte
        self.byte_index += 1
        return ErrorCode.NOT_DONE
