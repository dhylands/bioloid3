"""Implements a generic bioloid device."""

import os
import packet
import struct
from dump_mem import dump_mem
from log import log

class Register(object):

    RO = 0
    RW = 1

    SIZE_FMT = (None, 'B', '<H', None, '<I')

    def __init__(self, offset, size, access,
                 min_val=None, max_val=None, init_val=0,
                 update_fn=None):
        self.offset = offset
        self.size = size
        self.access = access
        self.min_val = min_val
        self.max_val = max_val
        self.init_val = init_val
        self.update_fn = update_fn
        self.val = self.init_val

    def __repr__(self):
        return 'Register (r) offset = {}'.format(self.offset)

    def __str__(self):
        return 'Register (s) offset = {}'.format(self.offset)

    def validate(self, test_val):
        return test_val >= self.min_val and test_val <= self.max_val

    def get_as_bytes(self):
        """Returns the register value as bytes."""
        # TODO: Implement struct.pack_into
        return struct.pack(Register.SIZE_FMT[self.size], self.val)

    def set_from_bytes(self, bytes):
        """Sets the value from a bytes object."""
        # TODO: Implement struct.unpack_from
        self.val = struct.unpack(Register.SIZE_FMT[self.size], bytes)[0]
        if not self.update_fn is None:
            self.update_fn(self)

    def validate_from_bytes(self, bytes):
        """Validates a value from a bytes object."""
        # TODO: Implement struct.unpack_from
        val = struct.unpack(Register.SIZE_FMT[self.size], bytes)[0]
        if ((not self.min_val is None and val < self.min_val) or
            (not self.max_val is None and val > self.max_val)):
            return packet.ErrorCode.RANGE
        if self.access != Register.RW:
            return packet.ErrorCode.RANGE
        # Removed validate_fn support since it wasn't being used
        #if not self.validate_fn is None:
        #    return self.validate_fn(val)
        return packet.ErrorCode.NONE


class ControlTable(object):

    def __init__(self, num_persistent_bytes, num_ctl_bytes, iniial_bytes, notifications, filename):
        self.num_persistent_bytes = num_persistent_bytes
        self.filename = filename
        self.num_ctl_bytes = num_ctl_bytes
        self.bytes = memoryview(bytearray(self.num_ctl_bytes))
        self.initail_bytes = initial_bytes
        self.notifications = sorted(notifications)

        self.read_from_file()

    def get_as_bytes(self, offset, length):
        """Returns a byte array containing register values from the registers
           between offset and offset + len - 1.
        """
        return self.bytes[offset:offest + length]

    def read_from_file(self):
        try:
            with open(self.filename, 'rb') as f:
                persistent_bytes = f.read(self.num_persistent_bytes)
                self.set_from_bytes(0, persistent_bytes, persist=False)
        except OSError: # CPython's FileNotFoundError is a subclass of OSError
            # Unable to read the control table. Lets write one using the
            # initial values
            self.write_to_file()

    def reset(self):
        self.bytes[:] = self.initial_bytes
        self.write_to_file()

    def set_from_bytes(self, offset, bytes, persist=True):
        """Sets the register values in the control table from 'data'."""
        self.bytes[offset:offset + length] = bytes
        if persist and offset < self.num_persistent_bytes:
            self.write_to_file()

    def write_to_file(self):
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

    def __init__(self, dev_port, reg_list, num_persistent_bytes, show_packets=False):
        self.dev_port = dev_port

        self.num_persistent_bytes = num_persistent_bytes
        self.pkt = None
        self.deffered_offset = 0
        self.deferred_length = 0
        self.deferred_params = None
        self.status = 0
        self.show_packets = show_packets

        # Since model and version are device specific, the derived class
        # should provide the registers for these.
        self.dev_id  = Register(Device.DEV_ID_OFFSET, 1, Register.RW, 0, 254,   1)
        self.baud    = Register(Device.BAUD_OFFSET,   1, Register.RW, 0, 254,   1, self.baud_updated)
        self.rdt     = Register(Device.RDT_OFFSET,    1, Register.RW, 0, 254, 250)

        regs = [self.dev_id, self.baud, self.rdt] + reg_list

        ctl_filename = self.filebase() + '.ctl'
        if os.uname().sysname == 'pyboard':
            ctl_filename = '/flash/' + ctl_filename

        print("Number of registers =", len(regs))
        self.control_table = ControlTable(regs, num_persistent_bytes, ctl_filename)

    def baud_updated(self, reg):
        baud = 2000000 // (reg.val + 1)
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
            if dev_id == self.dev_id.val:
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
        if pkt.dev_id != self.dev_id.val and pkt.dev_id != packet.Id.BROADCAST:
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
        pkt_bytes[2] = self.dev_id.val
        pkt_bytes[3] = 2       # for len and status
        pkt_bytes[4] = self.status | status
        if not params is None:
            pkt_bytes[3] += len(params)
            pkt_bytes[5:packet_len - 1] = params
        pkt_bytes[-1] = ~sum(pkt_bytes[2:-1]) & 0xff
        if self.show_packets:
            dump_mem(pkt_bytes, prefix='  W', show_ascii=False)
        self.dev_port.write_packet(pkt_bytes)

