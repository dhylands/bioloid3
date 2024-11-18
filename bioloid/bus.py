"""This module provides the Bus class which knows how to talk to Bioloid
   devices, and the BusError exception which is raised when an error is
   enountered.

"""
import os

from bioloid import packet
from bioloid.dump_mem import dump_mem
from bioloid.log import log

if os.uname().sysname == 'Linux':
    from typing import Callable, List, Union
    # Self isn't in typing until 3.11
    from typing_extensions import Self

    def const(x: int) -> int:
        """const implementation for linux"""
        return x
else:
    # It turns out that the unix variannt of micropython doesn't have os.uname() by default
    from micropython import const


class BusError(Exception):
    """Exception which is raised when a non-successful status packet is received."""

    def __init__(self, error_code: int, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.error_code = error_code

    def get_error_code(self) -> int:
        """Retrieves the error code associated with the exception."""
        return self.error_code

    def __str__(self) -> str:
        return "Rcvd Status: " + str(packet.ErrorCode(self.error_code))


class Bus:
    """The Bus class knows the commands used to talk to bioloid devices."""

    SHOW_NONE = const(0)
    SHOW_COMMANDS = const(1 << 0)
    SHOW_PACKETS = const(1 << 1)

    def __init__(self, serial_port, show: int = SHOW_NONE) -> None:
        self.serial_port = serial_port
        self.show = show

    def action(self) -> None:
        """Broadcasts an action packet to all of the devices on the bus.
        This causes all of the devices to perform their deferred writes
        at the same time.

        """
        if self.show & Bus.SHOW_COMMANDS:
            log('Broadcasting ACTION')
        self.fill_and_write_packet(packet.Id.BROADCAST, packet.Command.ACTION)

    def fill_and_write_packet(self, dev_id: int, cmd: int, data=None) -> None:
        """Allocates and fills a packet. data should be a bytearray of data
           to include in the packet, or None if no data should be included.
        """
        packet_len = 6
        if data is not None:
            packet_len += len(data)
        pkt_bytes = bytearray(packet_len)
        pkt_bytes[0] = 0xff
        pkt_bytes[1] = 0xff
        pkt_bytes[2] = dev_id
        pkt_bytes[3] = 2  # for len and cmd
        pkt_bytes[4] = cmd
        if data is not None:
            pkt_bytes[3] += len(data)
            pkt_bytes[5:packet_len - 1] = data
        pkt_bytes[-1] = ~sum(pkt_bytes[2:-1]) & 0xff
        if self.show & Bus.SHOW_PACKETS:
            dump_mem(pkt_bytes, prefix='  W', show_ascii=True, log=log)
        self.serial_port.write_packet(pkt_bytes)

    def ping(self, dev_id: int) -> bool:
        """Sends a PING request to a device.

           Returns true if the device responds successfully, false if a timeout
           occurs, and raises a bus.Error for any other failures.

           raises a BusError for any other failures.
        """
        self.send_ping(dev_id)
        try:
            self.read_status_packet()
        except BusError as ex:
            if ex.get_error_code() == packet.ErrorCode.TIMEOUT:
                return False
            raise ex
        return True

    def read(self, dev_id: int, offset: int, num_bytes: int) -> bytearray:
        """Sends a READ request and returns data read.

           Raises a bus.Error if any errors occur.
        """
        self.send_read(dev_id, offset, num_bytes)
        pkt = self.read_status_packet()
        return pkt.params()

    def read_status_packet(self) -> packet.Packet:
        """Reads a status packet and returns it.

        Rasises a bioloid.bus.BusError if an error occurs.

        """
        pkt = packet.Packet(status_packet=True)
        while True:
            byte = self.serial_port.read_byte()
            if byte is None:
                if self.show & Bus.SHOW_COMMANDS:
                    log('TIMEOUT')
                if self.show & Bus.SHOW_PACKETS:
                    dump_mem(pkt.pkt_bytes,
                             prefix='  R',
                             show_ascii=True,
                             log=log)
                raise BusError(packet.ErrorCode.TIMEOUT)
            err = pkt.process_byte(byte)
            if err != packet.ErrorCode.NOT_DONE:
                break
        if err != packet.ErrorCode.NONE:
            err_ex = BusError(err)
            if self.show & Bus.SHOW_COMMANDS:
                log(err_ex)
            if self.show & Bus.SHOW_PACKETS:
                dump_mem(pkt.pkt_bytes, prefix='  R', show_ascii=True, log=log)
            raise err_ex
        err = pkt.error_code()
        if self.show & Bus.SHOW_COMMANDS:
            log(f'Rcvd Status: {packet.ErrorCode(err)} from ID: {pkt.dev_id}')
        if self.show & Bus.SHOW_PACKETS:
            dump_mem(pkt.pkt_bytes, prefix='  R', show_ascii=True, log=log)
        if err != packet.ErrorCode.NONE:
            raise BusError(err)
        return pkt

    def reset(self, dev_id: int) -> int:
        """Sends a RESET request.

           Raises a bus.Error if any errors occur.
        """
        self.send_reset(dev_id)
        if dev_id == packet.Id.BROADCAST:
            return packet.ErrorCode.NONE
        pkt = self.read_status_packet()
        return pkt.error_code()

    def scan(self,
             start_id: int = 0,
             num_ids: int = 32,
             dev_found: Union[Callable[[Self, int], None], None] = None,
             dev_missing=None) -> bool:
        """Scans the bus, calling devFound(self, dev) for each device
        which responds, and dev_missing(self, dev) for each device
        which doesn't.

        Returns true if any devices were found.
        """
        end_id = start_id + num_ids - 1
        if end_id >= packet.Id.BROADCAST:
            end_id = packet.Id.BROADCAST - 1
        some_dev_found = False
        for dev_id in range(start_id, end_id + 1):
            if self.ping(dev_id):
                some_dev_found = True
                if dev_found:
                    dev_found(self, dev_id)
            else:
                if dev_missing:
                    dev_missing(self, dev_id)
        return some_dev_found

    def send_ping(self, dev_id):
        """Sends a ping to a device."""
        if self.show & Bus.SHOW_COMMANDS:
            log(f'Sending PING to ID {dev_id}')
        self.fill_and_write_packet(dev_id, packet.Command.PING)

    def send_read(self, dev_id, offset, num_bytes):
        """Sends a READ request to read data from the device's control
        table.
        """
        if self.show & Bus.SHOW_COMMANDS:
            log(f'Sending READ to ID {dev_id} offset 0x{offset:02x} len {num_bytes}'
                )
        self.fill_and_write_packet(dev_id, packet.Command.READ,
                                   bytearray((offset, num_bytes)))

    def send_reset(self, dev_id):
        """Sends a RESET command to the device, which causes it to reset the
           control table to factory defaults.
        """
        if self.show & Bus.SHOW_COMMANDS:
            if dev_id == packet.Id.BROADCAST:
                log('Broadcasting RESET')
            else:
                log(f'Sending RESET to ID {dev_id}')
        self.fill_and_write_packet(dev_id, packet.Command.RESET)

    def send_write(self,
                   dev_id: int,
                   offset: int,
                   data: Union[bytearray, bytes],
                   deferred: bool = False) -> None:
        """Sends a WRITE request if deferred is False, or REG_WRITE
        request if deferred is True to write data into the device's
        control table.

        data should be an array of ints, or a bytearray.

        Deferred writes will occur when and ACTION command is broadcast.
        """
        if self.show & Bus.SHOW_COMMANDS:
            cmd_str = 'REG_WRITE' if deferred else 'WRITE'
            if dev_id == packet.Id.BROADCAST:
                log(f'Broadcasting {cmd_str} offset 0x{offset:02x} len {len(data)}'
                    )
            else:
                log(f'Sending {cmd_str} to ID {dev_id} offset 0x{offset:02x} len {len(data)}'
                    )
        cmd = packet.Command.REG_WRITE if deferred else packet.Command.WRITE
        pkt_data = bytearray(len(data))
        pkt_data[0] = offset
        pkt_data[1:] = data
        self.fill_and_write_packet(dev_id, cmd, pkt_data)

    def sync_write(self, dev_ids: List[int], offset: int,
                   values: List[Union[bytearray, bytes]]) -> None:
        """Sets up a synchroous write command.

        dev_ids should be an array of device ids.

        offset should be the offset that the data will be written to.

        values should be an array of bytearrays. There should be one bytearray
        for each dev_id, and each bytearray should be of the same length.

        raises ValueError if the dimensionality of values is incorrect.
        """
        if self.show & Bus.SHOW_COMMANDS:
            ids = ', '.join([f'{id}' for id in dev_ids])
            log(f'Sending SYNC_WRITE to IDs {ids} offset 0x{offset:02x} len {len(values[0])}'
                )
        num_ids = len(dev_ids)
        if num_ids != len(values):
            raise ValueError(
                'len(dev_ids) = {num_ids} must match len(values) = {len(values)}'
            )
        bytes_per_id = len(values[0])
        param_len = num_ids * (bytes_per_id + 1) + 2
        data = bytearray(param_len)
        data[0] = offset
        data[1] = bytes_per_id
        data_idx = 2
        for id_idx in range(num_ids):
            if len(values[id_idx]) != bytes_per_id:
                raise ValueError(
                    f'len(values[{id_idx}]) not equal {bytes_per_id}')
            data[data_idx] = dev_ids[id_idx]
            data_idx += 1
            data[data_idx:data_idx + bytes_per_id] = values[id_idx]
            data_idx += bytes_per_id

        self.fill_and_write_packet(packet.Id.BROADCAST,
                                   packet.Command.SYNC_WRITE, data)

    def write(self,
              dev_id: int,
              offset: int,
              data: Union[bytearray, bytes],
              deferred: bool = False) -> int:
        """Sends a WRITE request if deferred is False, or a REG_WRITE
        request if deferred is True. Deferred writes will occur when
        and ACTION command is broadcast.

        data should be a bytes object or a bytearray.

        Raises a bus.Error if any errors occur.
        """
        self.send_write(dev_id, offset, data, deferred)
        if dev_id == packet.Id.BROADCAST:
            return packet.ErrorCode.NONE
        pkt = self.read_status_packet()
        return pkt.error_code()
