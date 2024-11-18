#!/usr/bin/env python3
"""
This module implements a class which is used for testing the bus class.
"""

import binascii
import unittest

from typing import Union

from bioloid.bus import Bus, BusError
from bioloid import log
from bioloid import packet


def make_packet_bytes(pkt_str) -> bytes:
    """Converts ASCII hex into bytes"""
    return binascii.unhexlify(pkt_str.replace(' ', ''))


class FakePort:
    """Implements a port for testing the Bus class."""

    def __init__(self, test) -> None:
        self.test = test
        self.cmd_queue = []
        self.rsp_queue = []
        self.rsp_pkt = None
        self.rsp_idx = 0

    def is_byte_available(self) -> bool:
        """Returns true if any queued response bytes are still available."""
        return self.rsp_pkt is not None

    def read_byte(self) -> Union[int, None]:
        """Returns a byte from any queded response packets"""
        if self.rsp_pkt is None:
            return None
        byte = self.rsp_pkt[self.rsp_idx]
        self.rsp_idx += 1
        if self.rsp_idx >= len(self.rsp_pkt):
            self.rsp_pkt = None
            self.next_response()
        return byte

    def write_packet(self, packet_data) -> None:
        """
        Verifies that the packet being written matches the queued
        command packer.
        """
        if len(self.cmd_queue) > 0:
            expected_pkt = self.cmd_queue.pop(0)
        else:
            expected_pkt = bytearray(0)
        self.test.assertEqual(expected_pkt, packet_data)

    def queue_command(self, cmd_pkt_str: Union[list, str]) -> None:
        """Queus up a command packet. The write packet routine will verify
           that the packet being written matches up with the queued packet.
        """
        if cmd_pkt_str:
            if isinstance(cmd_pkt_str, list):
                for cmd in cmd_pkt_str:
                    self.queue_command(cmd)
            else:
                cmd_pkt = make_packet_bytes(cmd_pkt_str)
                self.cmd_queue.append(cmd_pkt)

    def queue_response(self, rsp_pkt_str: Union[list, str, None]) -> None:
        """Queues up a response packet. The read_byte routine will return
           the next byte from the queued packet.
        """
        if rsp_pkt_str:
            if isinstance(rsp_pkt_str, list):
                for rsp in rsp_pkt_str:
                    self.queue_response(rsp)
            else:
                rsp_pkt = make_packet_bytes(rsp_pkt_str)
                self.rsp_queue.append(rsp_pkt)
                self.next_response()

    def next_response(self) -> None:
        """Retrieves the next packet from the response queue and sets it up
           to be received.
        """
        if self.rsp_pkt is None:
            if len(self.rsp_queue) > 0:
                self.rsp_pkt = self.rsp_queue.pop(0)
                self.rsp_idx = 0


# pylint: disable=too-many-public-methods


class TestBus(unittest.TestCase):
    """Test the Bus class"""

    def __init__(self) -> None:
        super().__init__()
        self.clear_log()

    def clear_log(self) -> None:
        """Clears any accumulated log lines."""
        self.log_lines = []

    def log(self, args) -> None:
        """Accumulates a log line"""
        self.log_lines.append(' '.join([str(arg) for arg in args]))
        # print(*args)

    def setup_bus(self, cmd: Union[list, str], rsp: Union[str, None]) -> Bus:
        """Sets up a bus for use by the tests"""
        self.clear_log()
        log.log_to_fn(self.log)
        port = FakePort(self)
        port.queue_command(cmd)
        port.queue_response(rsp)
        bus = Bus(port, show=Bus.SHOW_COMMANDS | Bus.SHOW_PACKETS)
        return bus

    # Command Packet Format:
    #
    #   ff ff ID Length Instruction Param1 ... ParamN Checksum
    #
    #       Length is number of parameters + 2
    #
    # Response Packet Format
    #
    #   ff ff ID Length Error Param1 ... ParamN Checksum
    #
    #       Length is number of parameters + 2
    #       Error is not included in the checksum

    def test_action(self) -> None:
        """Broadcast an action command (no response)"""
        bus = self.setup_bus('ff ff fe 02 05 fa', None)
        bus.action()
        self.assertEqual(self.log_lines, [
            'Broadcasting ACTION',
            '  W: 0000: ff ff fe 02 05 fa                               ......'
        ])

    def test_ping(self) -> None:
        """
        Send ping to device ID 1
        Ping response - no errors
        """
        bus = self.setup_bus('ff ff 01 02 01 fb', 'ff ff 01 02 00 fc')
        self.assertEqual(True, bus.ping(1))
        self.assertEqual(self.log_lines, [
            'Sending PING to ID 1',
            '  W: 0000: ff ff 01 02 01 fb                               ......',
            'Rcvd Status: None from ID: 1',
            '  R: 0000: ff ff 01 02 00 fc                               ......'
        ])

    def test_ping_timeout(self) -> None:
        """Send ping to device ID 1"""
        bus = self.setup_bus('ff ff 01 02 01 fb', None)
        self.assertEqual(False, bus.ping(1))
        self.assertEqual(self.log_lines, [
            'Sending PING to ID 1',
            '  W: 0000: ff ff 01 02 01 fb                               ......',
            'TIMEOUT', '  R:No data'
        ])

    def test_ping_error(self) -> None:
        """Send ping to device ID 1"""
        bus = self.setup_bus('ff ff 01 02 01 fb', 'ff ff 01 02 00 00')
        self.assertRaises(BusError, bus.ping, 1)
        self.assertEqual(self.log_lines, [
            'Sending PING to ID 1',
            '  W: 0000: ff ff 01 02 01 fb                               ......',
            'Rcvd Status: Checksum',
            '  R: 0000: ff ff 01 02 00 00                               ......'
        ])

    def test_ping_overheat(self) -> None:
        """Send ping to device ID 1"""
        bus = self.setup_bus('ff ff 01 02 01 fb', 'ff ff 01 02 04 fc')
        self.assertRaises(BusError, bus.ping, 1)
        self.assertEqual(self.log_lines, [
            'Sending PING to ID 1',
            '  W: 0000: ff ff 01 02 01 fb                               ......',
            'Rcvd Status: OverHeating from ID: 1',
            '  R: 0000: ff ff 01 02 04 fc                               ......'
        ])

    def test_read(self) -> None:
        """
        Read the internal temperature (offset 0x2b) of the Dynamixel actuator with an ID of 1
        Return 0x20 (32 C)
        """
        bus = self.setup_bus('ff ff 01 04 02 2b 01 cc', 'ff ff 01 03 00 20 db')
        params = bus.read(1, 0x2b, 1)
        self.assertEqual(bytearray([32]), params)
        self.assertEqual(self.log_lines, [
            'Sending READ to ID 1 offset 0x2b len 1',
            '  W: 0000: ff ff 01 04 02 2b 01 cc                         .....+..',
            'Rcvd Status: None from ID: 1',
            '  R: 0000: ff ff 01 03 00 20 db                            ..... .'
        ])

    def test_read2(self) -> None:
        """Read Model and ID from Device 01"""
        bus = self.setup_bus('ff ff 01 04 02 00 03 f5',
                             'ff ff 01 05 00 0c 00 01 ec')
        params = bus.read(1, 0x00, 3)
        self.assertEqual(bytearray([0x0c, 0x00, 0x01]), params)
        self.assertEqual(self.log_lines, [
            'Sending READ to ID 1 offset 0x00 len 3',
            '  W: 0000: ff ff 01 04 02 00 03 f5                         ........',
            'Rcvd Status: None from ID: 1',
            '  R: 0000: ff ff 01 05 00 0c 00 01 ec                      .........'
        ])

    def test_reset_broadcast(self) -> None:
        """Broadcast a reset command (no response)"""
        bus = self.setup_bus('ff ff fe 02 06 f9', None)
        bus.reset(packet.Id.BROADCAST)
        self.assertEqual(self.log_lines, [
            'Broadcasting RESET',
            '  W: 0000: ff ff fe 02 06 f9                               ......'
        ])

    def test_reset_one(self) -> None:
        """
        Send reset to device ID 1
        Status response - no errors
        """
        bus = self.setup_bus('ff ff 01 02 06 f6', 'ff ff 01 02 00 fc')
        self.assertEqual(packet.ErrorCode.NONE, bus.reset(1))
        self.assertEqual(self.log_lines, [
            'Sending RESET to ID 1',
            '  W: 0000: ff ff 01 02 06 f6                               ......',
            'Rcvd Status: None from ID: 1',
            '  R: 0000: ff ff 01 02 00 fc                               ......'
        ])

    def test_scan_one(self) -> None:
        """A scan is basically a series of pings"""
        bus = self.setup_bus('ff ff 01 02 01 fb', 'ff ff 01 02 00 fc')
        self.assertEqual(True, bus.scan(start_id=1, num_ids=1))
        self.assertEqual(self.log_lines, [
            'Sending PING to ID 1',
            '  W: 0000: ff ff 01 02 01 fb                               ......',
            'Rcvd Status: None from ID: 1',
            '  R: 0000: ff ff 01 02 00 fc                               ......'
        ])

    def test_scan_none(self) -> None:
        """Scan devices with none detected"""
        bus = self.setup_bus('ff ff 01 02 01 fb', None)
        self.assertEqual(False, bus.scan(start_id=1, num_ids=1))
        self.assertEqual(self.log_lines, [
            'Sending PING to ID 1',
            '  W: 0000: ff ff 01 02 01 fb                               ......',
            'TIMEOUT', '  R:No data'
        ])

    def dev_found(self, _bus, dev_id) -> None:
        """Callback called when a device is found"""
        log.log(f'dev_found: {dev_id}')

    def dev_missing(self, _bus, dev_id) -> None:
        """Callback called when a devices is missing"""
        log.log(f'dev_missing: {dev_id}')

    def test_scan_missing(self) -> None:
        """Test a scan with a missing device."""
        bus = self.setup_bus(['ff ff 01 02 01 fb', 'ff ff 02 02 01 fa'],
                             'ff ff 01 02 00 fc')
        self.assertEqual(
            True,
            bus.scan(start_id=1,
                     num_ids=2,
                     dev_found=self.dev_found,
                     dev_missing=self.dev_missing))
        self.assertEqual(self.log_lines, [
            'Sending PING to ID 1',
            '  W: 0000: ff ff 01 02 01 fb                               ......',
            'Rcvd Status: None from ID: 1',
            '  R: 0000: ff ff 01 02 00 fc                               ......',
            'dev_found: 1',
            'Sending PING to ID 2',
            '  W: 0000: ff ff 02 02 01 fa                               ......',
            'TIMEOUT',
            '  R:No data',
            'dev_missing: 2',
        ])

    def test_scan_broadcast(self) -> None:
        """Tests that scanning a a broadcast times out"""
        bus = self.setup_bus('ff ff fd 02 01 ff', None)
        self.assertEqual(False, bus.scan(start_id=253, num_ids=2))
        self.assertEqual(self.log_lines, [
            'Sending PING to ID 253',
            '  W: 0000: ff ff fd 02 01 ff                               ......',
            'TIMEOUT', '  R:No data'
        ])

    def test_write(self) -> None:
        """Turn the LED (offset 0x11) on for the Dynamixel actuator with an ID of 1"""
        bus = self.setup_bus('ff ff 01 04 03 11 01 e5', 'ff ff 01 03 00 20 db')
        bus.write(1, 0x11, b'\x01')
        self.assertEqual(self.log_lines, [
            'Sending WRITE to ID 1 offset 0x11 len 1',
            '  W: 0000: ff ff 01 04 03 11 01 e5                         ........',
            'Rcvd Status: None from ID: 1',
            '  R: 0000: ff ff 01 03 00 20 db                            ..... .'
        ])

    def test_write_brodcast(self) -> None:
        """Turn the LED (offset 0x11) on for the Dynamixel actuator with an ID of 1"""
        bus = self.setup_bus('ff ff fe 04 03 11 01 e8', None)
        bus.write(packet.Id.BROADCAST, 0x11, b'\x01')
        self.assertEqual(self.log_lines, [
            'Broadcasting WRITE offset 0x11 len 1',
            '  W: 0000: ff ff fe 04 03 11 01 e8                         ........'
        ])

    def test_deferred_write(self) -> None:
        """Turn the LED (offset 0x11) on for the Dynamixel actuator with an ID of 1"""
        bus = self.setup_bus('ff ff 01 04 04 11 01 e4', 'ff ff 01 03 00 20 db')
        bus.write(1, 0x11, b'\x01', deferred=True)
        self.assertEqual(self.log_lines, [
            'Sending REG_WRITE to ID 1 offset 0x11 len 1',
            '  W: 0000: ff ff 01 04 04 11 01 e4                         ........',
            'Rcvd Status: None from ID: 1',
            '  R: 0000: ff ff 01 03 00 20 db                            ..... .'
        ])

    def test_sync_write(self) -> None:
        """Turn the LED (offset 0x11) on for the Dynamixel actuator with IDs of 1 and 2"""
        bus = self.setup_bus('ff ff fe 08 83 11 01 01 01 02 01 5f', None)
        bus.sync_write([1, 2], 0x11, [b'\x01', b'\x01'])
        self.assertEqual(self.log_lines, [
            'Sending SYNC_WRITE to IDs 1, 2 offset 0x11 len 1',
            '  W: 0000: ff ff fe 08 83 11 01 01 01 02 01 5f             ..........._'
        ])

    def test_sync_write_error(self) -> None:
        """Turn the LED (offset 0x11) on for the Dynamixel actuator with IDs of 1 and 2"""
        bus = self.setup_bus('ff ff fe 08 83 11 01 01 01 02 01 5f', None)
        self.assertRaises(ValueError, bus.sync_write, [1, 2], 0x11, [b'\x01'])
        self.assertEqual(self.log_lines,
                         ['Sending SYNC_WRITE to IDs 1, 2 offset 0x11 len 1'])

    def test_sync_write_error2(self) -> None:
        """Turn the LED (offset 0x11) on for the Dynamixel actuator with IDs of 1 and 2"""
        bus = self.setup_bus('ff ff fe 08 83 11 01 01 01 02 01 5f', None)
        self.assertRaises(ValueError, bus.sync_write, [1, 2], 0x11,
                          [b'\x01', b'\x01\x02'])
        self.assertEqual(self.log_lines,
                         ['Sending SYNC_WRITE to IDs 1, 2 offset 0x11 len 1'])


if __name__ == '__main__':
    unittest.main()
