"""Implements a generic bioloid device."""

import os
from bioloid.bus import Bus
from bioloid.dump_mem import dump_mem
from bioloid.log import log
from bioloid import packet


class ControlTable():
    """Abstracts the control table used in a bioloid device."""

    def __init__(self, params, notifications, filename):
        """Constructor for the control table.

        params is a namedtuple with the following members:
        params.num_persistent_bytes is the number of bytes which are persisted across power cycles.
        params.initial_bytes is a bytearray containing the initial values for the control table.
        params.ctl_bytes is a bytearray containing the control table bytes.
        notifications is a tuple of entries. Each entry contains 3 fields,
          an offset, a length and a function to call when any value in the control
          table between offset to offset+length-1 is modified.
        filename is the name of the file to store the persitent bytes in.
        """
        self.params = params
        self.filename = filename
        self.num_ctl_bytes = len(params.initial_bytes)
        self.bytes = memoryview(params.ctl_bytes)
        self.notifications = sorted(notifications)

        # Reset all of the bytes to their initial values, then possibly
        # overwrite the persisten bytes.
        self.bytes[:] = self.params.initial_bytes
        self.read_from_file()
        self.notify_updates(0, len(self.bytes))

    def get_as_bytes(self, offset, length):
        """Returns a byte array containing register values from the registers
        between offset and offset + len - 1.
        """
        return self.bytes[offset:offset + length]

    def read_from_file(self):
        """Reads the persistent bytes of the control table from the backing file."""
        try:
            with open(self.filename, 'rb') as f:
                persistent_bytes = f.read(self.params.num_persistent_bytes)
                if len(persistent_bytes) == self.params.num_persistent_bytes:
                    self.set_from_bytes(0, persistent_bytes, persist=False)
                    return
                # If the length doesn't match, then that probably means that
                # layout of the control table changed. So we'll ignore the file
                # and revert to initial values.
        except OSError:  # CPython's FileNotFoundError is a subclass of OSError
            # Unable to read the control table.
            pass
        self.write_to_file()

    def reset(self):
        """Resets the control table back to its factory default settings."""
        self.bytes[:] = self.params.initial_bytes
        self.notify_updates(0, len(self.bytes))
        self.write_to_file()

    def set_from_bytes(self, offset, src_bytes, persist=True):
        """Sets the register values in the control table from 'data'."""
        length = len(src_bytes)
        self.bytes[offset:offset + length] = src_bytes
        self.notify_updates(offset, length)
        if persist and offset < self.params.num_persistent_bytes:
            self.write_to_file()

    def notify_updates(self, offset, length):
        """Notifies any refistered notification handlers when indicated bytes are updated."""
        end_offset = offset + length
        for n_offset, n_len, n_fn in self.notifications:
            if n_offset < end_offset and n_offset + n_len > offset:
                update_offset = max(n_offset, offset)
                update_end_offset = min(n_offset + n_len, end_offset)
                n_fn(update_offset, update_end_offset - update_offset)

    def write_to_file(self):
        """Writes the persistent bytes of the control table to the backing file."""
        persistent_bytes = self.get_as_bytes(0,
                                             self.params.num_persistent_bytes)
        with open(self.filename, 'wb') as f:
            f.write(self.bytes[0:len(persistent_bytes)])


# pylint: disable=too-many-instance-attributes
class Device():
    """Common code for implementing a Bioloid Device."""

    MODEL_OFFSET = 0
    VERSION_OFFSET = 2
    DEV_ID_OFFSET = 3
    BAUD_OFFSET = 4
    RDT_OFFSET = 5
    LED = 0x19

    INITIAL_DEV_ID = 0
    INITIAL_BAUD = 1  # Corresponds to 1 MBit
    INITIAL_RDT = 250  # Corresponds to 500 uSec

    def __init__(self, dev_port, params, notifications, show=Bus.SHOW_NONE):
        self.dev_port = dev_port
        self.show = show

        self.pkt = None
        self.deferred_offset = 0
        self.deferred_length = 0
        self.deferred_params = None
        self.status = 0

        notifications = (
            (Device.BAUD_OFFSET, 1, self.baud_updated), ) + notifications

        ctl_filename = self.filebase() + '.ctl'
        # The unix version of micropython hasn't implemented uname yet
        if hasattr(os, 'uname') and os.uname().sysname == 'pyboard':
            ctl_filename = '/flash/' + ctl_filename

        self.ctl_bytes = memoryview(params.ctl_bytes)

        self.control_table = ControlTable(params, notifications, ctl_filename)

    def set_port(self, dev_port):
        """Allows the port to be specified after creating the device."""
        self.dev_port = dev_port

    def baud(self):
        """Returns the baud byte from the control table."""
        return self.ctl_bytes[Device.BAUD_OFFSET]

    def dev_id(self):
        """Returns the device id from the control table."""
        return self.ctl_bytes[Device.DEV_ID_OFFSET]

    def baud_updated(self, _offset, _length):
        """Called whenever the baud rate is updated."""
        if self.dev_port is None:
            return
        baud = 2000000 // (self.baud() + 1)
        if self.dev_port.baud != baud:
            self.dev_port.set_parameters(baud, self.dev_port.rx_buf_len)

    def command_action(self, _pkt):
        """Called when an ACTION command is received."""
        if self.deferred_params:
            # No status packet sent for ACTION
            self.control_table.set_from_bytes(self.deferred_offset,
                                              self.deferred_params)
        self.deferred_offset = 0
        self.deferred_params = None

    def command_ping(self, pkt):
        """Called when a PING command is received."""
        if pkt.dev_id == packet.Id.BROADCAST:
            # A broadcast ping is essentially a no-op
            return
        self.write_status_packet(packet.ErrorCode.NONE)

    def command_read(self, pkt):
        """Called when a READ command is received."""
        if pkt.dev_id == packet.Id.BROADCAST:
            # A broadcast read is essentially a no-op
            return
        offset = pkt.param_byte(0)
        length = pkt.param_byte(1)
        if offset + length > self.control_table.num_ctl_bytes:
            self.write_status_packet(packet.ErrorCode.RANGE)
        params = self.control_table.get_as_bytes(offset, length)
        self.write_status_packet(packet.ErrorCode.NONE, params)

    def command_reg_write(self, pkt):
        """Called when a REG_WRITE (aka deferred WRITE) cmmand is received."""
        offset = pkt.param_byte(0)
        params = pkt.params()[1:]
        if pkt.dev_id != packet.Id.BROADCAST:
            self.write_status_packet(packet.ErrorCode.NONE)
        self.deferred_offset = offset
        self.deferred_params = params

    def command_reset(self, _pkt):
        """Called when a RESET command is received."""
        self.write_status_packet(packet.ErrorCode.NONE)
        self.control_table.reset()

    def command_sync_write(self, pkt):
        """Called when a SYNC_WRITE command is received."""
        offset = pkt.param_byte(0)
        length = pkt.param_byte(1)
        idx = 2
        params = pkt.params()
        while idx < len(params):
            dev_id = params[idx]
            if dev_id == self.dev_id():
                id_params = params[idx + 1:idx + 1 + length]
                self.control_table.set_from_bytes(offset, id_params)
                break
            idx += length + 1

    def command_write(self, pkt):
        """Called when a WRITE command is received."""
        offset = pkt.param_byte(0)
        params = pkt.params()[1:]
        if pkt.dev_id != packet.Id.BROADCAST:
            self.write_status_packet(packet.ErrorCode.NONE)
        self.control_table.set_from_bytes(offset, params)

    def command_unknown(self, _pkt):
        """Called when an unknown command is received. If the derived
           class doesn't override this function, then we'll generate a status
           packet with an INSTRUCTION error.
        """
        self.write_status_packet(packet.ErrorCode.INSTRUCTION)

    def filebase(self):
        """Default filebase. Derived classes should override this."""
        return 'device'

    def packet_received(self, pkt):
        """Called when a valid packet has been received."""
        if pkt.dev_id != self.dev_id() and pkt.dev_id != packet.Id.BROADCAST:
            # Not a packet for us
            return
        if self.show & Bus.SHOW_COMMANDS:
            log(f'Rcvd packet for ID: {pkt.dev_id} Cmd: {packet.Command(pkt.cmd)}'
                )
        if self.show & Bus.SHOW_PACKETS:
            dump_mem(pkt.pkt_bytes, prefix='  R', show_ascii=False, log=log)
        if pkt.cmd == packet.Command.PING:
            self.command_ping(pkt)
        elif pkt.cmd == packet.Command.READ:
            self.command_read(pkt)
        elif pkt.cmd == packet.Command.WRITE:
            self.command_write(pkt)
        elif pkt.cmd == packet.Command.REG_WRITE:
            self.command_reg_write(pkt)
        elif pkt.cmd == packet.Command.ACTION:
            self.command_action(pkt)
        elif pkt.cmd == packet.Command.RESET:
            self.command_reset(pkt)
        elif pkt.cmd == packet.Command.SYNC_WRITE:
            self.command_sync_write(pkt)
        else:
            self.command_unknown(pkt)

    def process_byte(self, byte):
        """Runs a single byte through the packet parser."""
        if self.pkt is None:
            self.pkt = packet.Packet()
        err = self.pkt.process_byte(byte)
        if err == packet.ErrorCode.NONE:
            self.packet_received(self.pkt)
        elif err != packet.ErrorCode.NOT_DONE:
            # Since we got this far, this means that there must have been a
            # checksum error. If it looks like the packet was addressed to us
            # then generate an error packet.
            if self.pkt.dev_id == self.dev_id():
                self.write_status_packet(err)
        return err

    def write_status_packet(self, status, params=None):
        """Allocates and fills a packet. param should be a bytearray of data
           to include in the packet, or None if no data should be included.
        """
        packet_len = 6
        params_len = 0
        if not params is None:
            params_len = len(params)
        packet_len += params_len
        pkt_bytes = bytearray(packet_len)
        pkt_bytes[0] = 0xff
        pkt_bytes[1] = 0xff
        pkt_bytes[2] = self.dev_id()
        pkt_bytes[3] = 2 + params_len  # for len and status
        pkt_bytes[4] = self.status | status
        check_sum = pkt_bytes[2] + pkt_bytes[3] + pkt_bytes[4]
        if not params is None:
            pkt_bytes[5:packet_len - 1] = params
            check_sum += sum(pkt_bytes[5:packet_len - 1])
        pkt_bytes[-1] = ~check_sum & 0xff
        if self.show & Bus.SHOW_PACKETS:
            dump_mem(pkt_bytes, prefix='  W', show_ascii=False, log=log)
        self.dev_port.write_packet(pkt_bytes)
