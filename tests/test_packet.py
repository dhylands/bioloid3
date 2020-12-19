#!/usr/bin/env python3

# This file tests the packet parser

import unittest
import binascii

from bioloid.packet import Command, ErrorCode, Id, Packet

class TestId(unittest.TestCase):

    def test_id(self):
        id = Id(1)
        self.assertEqual(id.get_dev_id(), 1)
        self.assertEqual(repr(id), 'Id(0x01)')
        self.assertEqual(str(id), '0x01')

        id = Id(Id.BROADCAST)
        self.assertEqual(id.get_dev_id(), 254)
        self.assertEqual(repr(id), 'Id(0xfe)')
        self.assertEqual(str(id), 'BROADCAST')

        id = Id(Id.INVALID)
        self.assertEqual(id.get_dev_id(), 255)
        self.assertEqual(repr(id), 'Id(0xff)')
        self.assertEqual(str(id), 'INVALID')


class TestComand(unittest.TestCase):

    def test_command(self):
        cmd = Command(Command.PING)
        self.assertEqual('Command(0x01)', repr(cmd))
        self.assertEqual('PING', str(cmd))

        cmd = Command(0x10)
        self.assertEqual('Command(0x10)', repr(cmd))
        self.assertEqual('0x10', str(cmd))

        self.assertEqual(Command.PING, Command.parse('PING'))
        self.assertRaises(ValueError, Command.parse, 'xxx')

class TestErrorCode(unittest.TestCase):

    def test_error_code(self):
        err = ErrorCode(ErrorCode.RESERVED)
        self.assertEqual('ErrorCode(0x80)', repr(err))
        self.assertEqual('Reserved', str(err))

        err = ErrorCode(ErrorCode.INSTRUCTION)
        self.assertEqual('ErrorCode(0x40)', repr(err))
        self.assertEqual('Instruction', str(err))

        err = ErrorCode(ErrorCode.NONE)
        self.assertEqual('ErrorCode(0x00)', repr(err))
        self.assertEqual('None', str(err))

        err = ErrorCode(ErrorCode.NOT_DONE)
        self.assertEqual('ErrorCode(0x100)', repr(err))
        self.assertEqual('NotDone', str(err))

        err = ErrorCode(ErrorCode.TIMEOUT)
        self.assertEqual('ErrorCode(0x101)', repr(err))
        self.assertEqual('Timeout', str(err))

        err = ErrorCode(ErrorCode.TOO_MUCH_DATA)
        self.assertEqual('ErrorCode(0x102)', repr(err))
        self.assertEqual('TooMuchData', str(err))

        err = ErrorCode(0x7f)
        self.assertEqual('ErrorCode(0x7f)', repr(err))
        self.assertEqual('All', str(err))

        err = ErrorCode(ErrorCode.OVERLOAD | ErrorCode.RANGE)
        self.assertEqual('ErrorCode(0x28)', repr(err))
        self.assertEqual('Range,Overload', str(err))

        self.assertEqual(ErrorCode.NONE, ErrorCode.parse('none'))
        self.assertEqual(0x7f, ErrorCode.parse('ALL'))
        self.assertEqual(ErrorCode.CHECKSUM, ErrorCode.parse('CheckSum'))
        self.assertRaises(ValueError, ErrorCode.parse, 'xxx')

class TestPacket(unittest.TestCase):

    def parse_packet(self, data_str, expected_err=ErrorCode.NONE, status_packet=False):
        data = binascii.unhexlify(data_str.replace(' ', ''))
        pkt = Packet(status_packet=status_packet)
        for i in range(len(data)):
            byte = data[i]
            err = pkt.process_byte(byte)
            if i + 1 == len(data):
                self.assertEqual(err, expected_err)
            else:
                self.assertEqual(err, ErrorCode.NOT_DONE)
        return pkt

    def test_cmd_bad_checksum(self):
        self.parse_packet('ff ff fe 04 03 03 01 f5', ErrorCode.CHECKSUM)

    def test_cmd_set_id(self):
        pkt = self.parse_packet('ff ff fe 04 03 03 01 f6')
        self.assertEqual(pkt.dev_id, 0xfe)
        self.assertEqual(pkt.cmd, Command.WRITE)
        self.assertEqual(pkt.param_len(), 2)
        self.assertEqual(pkt.params(), bytearray([0x03, 0x01]))
        self.assertEqual(0x03, pkt.param_byte(0))
        self.assertEqual(0x01, pkt.param_byte(1))

    def test_ping_cmd(self):
        pkt = self.parse_packet('ff ff 01 02 01 fb')
        self.assertEqual(pkt.dev_id, 0x01)
        self.assertEqual(pkt.cmd, Command.PING)
        self.assertEqual(pkt.param_len(), 0)

    def test_ping_cmd_checksum(self):
        pkt = self.parse_packet('ff ff 01 02 01 ff', expected_err=ErrorCode.CHECKSUM)

    def test_ping_rsp(self):
        pkt = self.parse_packet('ff ff 01 02 00 fc', status_packet=True)
        self.assertEqual(pkt.dev_id, 0x01)
        self.assertEqual(pkt.error_code(), ErrorCode.NONE)
        self.assertEqual(pkt.param_len(), 0)

    # Error code shouldn't be included in the chuecksum
    def test_ping_error_rsp(self):
        pkt = self.parse_packet('ff ff 01 02 04 fc', status_packet=True)
        self.assertEqual(pkt.dev_id, 0x01)
        self.assertEqual(pkt.error_code(), ErrorCode.OVERHEATING)
        self.assertEqual(pkt.param_len(), 0)
        self.assertEqual(pkt.error_code_str(), 'OverHeating')

    def test_ping_cmd_noise(self):
        pkt = self.parse_packet('00 ff ff 01 02 01 fb')
        self.assertEqual(pkt.dev_id, 0x01)
        self.assertEqual(pkt.cmd, Command.PING)
        self.assertEqual(pkt.param_len(), 0)

        pkt = self.parse_packet('00 ff 00 ff ff 01 02 01 fb')
        self.assertEqual(pkt.dev_id, 0x01)
        self.assertEqual(pkt.cmd, Command.PING)
        self.assertEqual(pkt.param_len(), 0)

        pkt = self.parse_packet('ff 00 ff ff ff 01 02 01 fb')
        self.assertEqual(pkt.dev_id, 0x01)
        self.assertEqual(pkt.cmd, Command.PING)
        self.assertEqual(pkt.param_len(), 0)


if __name__ == '__main__':
    unittest.main()
