"""Implements a generic bioloid device."""

import os
import packet
import struct
from dump_mem import dump_mem
from log import log


class ControlTable(object):

    def __init__(self, num_persistent_bytes, initial_bytes, ctl_bytes, notifications, filename):
        """Constructor for the control table.

        num_persistent_bytes is the number of bytes which are persisted across power cycles.
        initial_bytes is a bytearray containing the initial values for the control table.
        ctl_bytes is a bytearray containing the control table bytes.
        notifications is a tuple of entries. Each entry contains 3 fields,
          and offset, a length and a function to call when any value in the control
          table between offset to offset+length-1 is modified.
        filename is the name of the file to store the persitent bytes in.
        """
        self.num_persistent_bytes = num_persistent_bytes
        self.filename = filename
        self.num_ctl_bytes = len(initial_bytes)
        self.bytes = memoryview(ctl_bytes)
        self.initial_bytes = initial_bytes
        self.notifications = sorted(notifications)

        # Reset all of the bytes to their initial values, then possibly
        # overwrite the persisten bytes.
        self.bytes[:] = self.initial_bytes
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
                persistent_bytes = f.read(self.num_persistent_bytes)
                if len(persistent_bytes) == self.num_persistent_bytes:
                    self.set_from_bytes(0, persistent_bytes, persist=False)
                    return
                # If the length doesn't match, then that probably means that
                # layout of the control table changed. So we'll ignore the file
                # and revert to initial values.
        except OSError: # CPython's FileNotFoundError is a subclass of OSError
            # Unable to read the control table.
            pass
        self.write_to_file()

    def reset(self):
        """Resets the control table back to its factory default settings."""
        self.bytes[:] = self.initial_bytes
        self.notify_update(0, len(self.bytes))
        self.write_to_file()

    def set_from_bytes(self, offset, bytes, persist=True):
        """Sets the register values in the control table from 'data'."""
        length = len(bytes)
        self.bytes[offset:offset + length] = bytes
        self.notify_updates(offset, length)
        if persist and offset < self.num_persistent_bytes:
            self.write_to_file()

    def notify_updates(self, offset, length):
        end_offset = offset + length
        for n_offset, n_len, n_fn in self.notifications:
            if n_offset < end_offset and n_offset + n_len > offset:
                update_offset = max(n_offset, offset)
                update_end_offset = min(n_offset + n_len, end_offset)
                n_fn(update_offset, update_end_offset - update_offset)

    def write_to_file(self):
        """Writes the persistent bytes of the control table to the backing file."""
        persistent_bytes = self.get_as_bytes(0, self.num_persistent_bytes)
        with open(self.filename, 'wb') as f:
            f.write(self.bytes[0:persistent_bytes])


class Device(object):
    """Common code for implementing a Bioloid Device."""

    MODEL_OFFSET    = 0
    VERSION_OFFSET  = 2
    DEV_ID_OFFSET   = 3
    BAUD_OFFSET     = 4
    RDT_OFFSET      = 5

    INITIAL_DEV_ID  = 0
    INITIAL_BAUD    = 1     # Corresponds to 1 MBit
    INITIAL_RDT     = 250   # Corresponds to 500 uSec

    def __init__(self, dev_port, num_persistent_bytes, initial_bytes, ctl_bytes, notifications, show_packets=False):
        self.dev_port = dev_port
        self.show_packets = show_packets

        self.pkt = None
        self.deffered_offset = 0
        self.deferred_length = 0
        self.deferred_params = None
        self.status = 0

        notifications = ((Device.BAUD_OFFSET, 1, self.baud_updated),) + notifications

        ctl_filename = self.filebase() + '.ctl'
        # The unix version of micropython hasn't implemented uname yet
        if hasattr(os, 'uname') and os.uname().sysname == 'pyboard':
            ctl_filename = '/flash/' + ctl_filename

        self.ctl_bytes = memoryview(ctl_bytes)

        self.control_table = ControlTable(num_persistent_bytes, initial_bytes,
                                          ctl_bytes, notifications, ctl_filename)

    def baud(self):
        return self.ctl_bytes[Device.BAUD_OFFSET]

    def dev_id(self):
        return self.ctl_bytes[Device.DEV_ID_OFFSET]

    def baud_updated(self, offset, length):
        baud = 2000000 // (self.baud() + 1)
        if self.dev_port.baud != baud:
            self.dev_port.set_baud(baud)

    def command_action(self, pkt):
        """Called when an ACTION command is received."""
        if self.deferred_params:
            # No status packet sent for ACTION
            self.control_table.set_from_bytes(self.deferred_offset, self.deferred_params)
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
        """Called when a REG_WRITE (aka deferred WRITE) command is received."""
        offset = pkt.param_byte(0)
        length = pkt.length - 3
        params = pkt.params()[1:]
        status = self.control_table.validate_from_bytes(offset, params)
        if pkt.dev_id != packet.Id.BROADCAST:
            self.write_status_packet(status)
        if status == packet.ErrorCode.NONE:
            self.deferred_offset = offset
            self.deferred_params = params

    def command_reset(self, pkt):
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
                id_params = params[idx+1:idx+1+length]
                status = self.control_table.validate_from_bytes(offset, id_params)
                if status == packet.ErrorCode.NONE:
                    self.control_table.set_from_bytes(offset, id_params)
                break
            idx += length + 1

    def command_write(self, pkt):
        """Called when a WRITE command is received."""
        offset = pkt.param_byte(0)
        params = pkt.params()[1:]
        status = self.control_table.validate_from_bytes(offset, params)
        if pkt.dev_id != packet.Id.BROADCAST:
            self.write_status_packet(status)
        if status == packet.ErrorCode.NONE:
            self.control_table.set_from_bytes(offset, params)

    def command_unknown(self, pkt):
        """Called when an unknown command is received. If the derived
           class doesn't override this function, then we'll generate a status
           packet with an INSTRUCTION error.
        """
        self.write_status_packet(packet.ErrorCode.INSTRUCTION)

    def filebase(self):
        return 'device'

    def packet_received(self, pkt):
        """Called when a valid packet has been received."""
        if pkt.dev_id != self.dev_id() and pkt.dev_id != packet.Id.BROADCAST:
            # Not a packet for us
            return
        if self.show_packets:
            log('Rcvd packet for ID: {} Cmd: {}'.format(pkt.dev_id, packet.Command(pkt.cmd)))
            dump_mem(pkt.pkt_bytes, prefix='  R', show_ascii=False)
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
        if err == packet.ErrorCode.NOT_DONE:
            return
        if err == packet.ErrorCode.NONE:
            self.packet_received(self.pkt)
            return

        # Since we got this far, this means that there must have been a
        # checksum error. If it looks like the packet was addressed to us
        # then generate an error packet.
        self.write_status_packet(packet.ErrorCode.CHECKSUM)

    def write_status_packet(self, status, params=None):
        """Allocates and fills a packet. param should be a bytearray of data
           to include in the packet, or None if no data should be included.
        """
        packet_len = 6
        if not params is None:
            packet_len += len(params)
        pkt_bytes = bytearray(packet_len)
        pkt_bytes[0] = 0xff
        pkt_bytes[1] = 0xff
        pkt_bytes[2] = self.dev_id()
        pkt_bytes[3] = 2       # for len and status
        pkt_bytes[4] = self.status | status
        if not params is None:
            pkt_bytes[3] += len(params)
            pkt_bytes[5:packet_len - 1] = params
        pkt_bytes[-1] = ~sum(pkt_bytes[2:-1]) & 0xff
        if self.show_packets:
            dump_mem(pkt_bytes, prefix='  W', show_ascii=False)
        self.dev_port.write_packet(pkt_bytes)

