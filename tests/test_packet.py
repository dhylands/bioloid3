#!/usr/bin/env python3

# This file tests the packet parser

import unittest
import binascii

from bioloid import packet

class TestPacket(unittest.TestCase):

    def parse_packet(self, data_str, expected_err=packet.ErrorCode.NONE, status_packet=False):
        data = binascii.unhexlify(data_str.replace(' ', ''))
        pkt = packet.Packet(status_packet=status_packet)
        for i in range(len(data)):
            byte = data[i]
            err = pkt.process_byte(byte)
            if i + 1 == len(data):
                self.assertEqual(err, expected_err)
            else:
                self.assertEqual(err, packet.ErrorCode.NOT_DONE)
        return pkt

    def test_cmd_bad_checksum(self):
        self.parse_packet('ff ff fe 04 03 03 01 f5', packet.ErrorCode.CHECKSUM)

    def test_cmd_set_id(self):
        pkt = self.parse_packet('ff ff fe 04 03 03 01 f6')
        self.assertEqual(pkt.dev_id, 0xfe)
        self.assertEqual(pkt.cmd, packet.Command.WRITE)
        self.assertEqual(pkt.param_len(), 2)
        self.assertEqual(pkt.params(), bytearray([0x03, 0x01]))

    def test_ping_cmd(self):
        pkt = self.parse_packet('ff ff 01 02 01 fb')
        self.assertEqual(pkt.dev_id, 0x01)
        self.assertEqual(pkt.cmd, packet.Command.PING)
        self.assertEqual(pkt.param_len(), 0)

    def test_ping_rsp(self):
        pkt = self.parse_packet('ff ff 01 02 00 fc', status_packet=True)
        self.assertEqual(pkt.dev_id, 0x01)
        self.assertEqual(pkt.error_code(), packet.ErrorCode.NONE)
        self.assertEqual(pkt.param_len(), 0)

    # Error code shouldn't be included in the chuecksum
    def test_ping_error_rsp(self):
        pkt = self.parse_packet('ff ff 01 02 04 fc', status_packet=True)
        self.assertEqual(pkt.dev_id, 0x01)
        self.assertEqual(pkt.error_code(), packet.ErrorCode.OVERHEATING)
        self.assertEqual(pkt.param_len(), 0)

if __name__ == '__main__':
    unittest.main()
