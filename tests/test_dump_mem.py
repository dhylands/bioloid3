#!/usr/bin/env python3
"""
This file tests the dump_mem module.
"""

import unittest

from bioloid.dump_mem import dump_mem

PREFIX = '    Prefix'


class TestDumpMem(unittest.TestCase):
    """Tests for the dump_mem.py file"""

    def __init__(self) -> None:
        super().__init__()
        self.clear_log()

    def clear_log(self) -> None:
        """Clears any log lines that have accumulated"""
        self.log_lines = []

    def log(self, s: str) -> None:
        """Appends the string to the accumulated log"""
        self.log_lines.append(s)
        #print(str)

    def test_empty_buffer(self) -> None:
        """Tests passing in an empty buffer"""
        self.clear_log()
        dump_mem(b'', prefix=PREFIX, log=self.log)
        self.assertEqual(self.log_lines, ['    Prefix:No data'])

    def test_less_than_one_line(self) -> None:
        """Tests less than a full lines worth of data."""
        self.clear_log()
        dump_mem(b'0123', prefix=PREFIX, log=self.log)
        self.assertEqual(self.log_lines, [
            '    Prefix: 0000: 30 31 32 33                                     0123'
        ])

    def test_less_than_one_line_no_ascii(self) -> None:
        """Tests less than a ffull lines worth of data with show_ascii turned off"""
        self.clear_log()
        dump_mem(b'0123', prefix=PREFIX, show_ascii=False, log=self.log)
        self.assertEqual(self.log_lines, ['    Prefix: 0000: 30 31 32 33'])

    def test_exactly_one_line(self) -> None:
        """Tests exactly one line of output"""
        self.clear_log()
        dump_mem(b'0123456789ABCDEF', prefix=PREFIX, log=self.log)
        self.assertEqual(self.log_lines, [
            '    Prefix: 0000: 30 31 32 33 34 35 36 37 38 39 41 42 43 44 45 46 0123456789ABCDEF'
        ])

    def test_exactly_one_line_no_ascii(self) -> None:
        """Tests exactly one line of output with show_ascii turned off"""
        self.clear_log()
        dump_mem(b'0123456789ABCDEF',
                 prefix=PREFIX,
                 show_ascii=False,
                 log=self.log)
        self.assertEqual(self.log_lines, [
            '    Prefix: 0000: 30 31 32 33 34 35 36 37 38 39 41 42 43 44 45 46'
        ])

    def test_a_bit_more_than_a_line(self) -> None:
        """Tests a line and a byte"""
        self.clear_log()
        dump_mem(b'0123456789ABCDEFG', prefix=PREFIX, log=self.log)
        self.assertEqual(self.log_lines, [
            '    Prefix: 0000: 30 31 32 33 34 35 36 37 38 39 41 42 43 44 45 46 0123456789ABCDEF',
            '    Prefix: 0010: 47                                              G'
        ])

    def test_a_bit_more_than_a_line_no_ascii(self) -> None:
        """Tests a line and a byte with show_ascii turned off"""
        self.clear_log()
        dump_mem(b'0123456789ABCDEFG',
                 prefix=PREFIX,
                 show_ascii=False,
                 log=self.log)
        self.assertEqual(self.log_lines, [
            '    Prefix: 0000: 30 31 32 33 34 35 36 37 38 39 41 42 43 44 45 46',
            '    Prefix: 0010: 47'
        ])

    def test_no_prefix(self) -> None:
        """Tests with no prefix"""
        self.clear_log()
        dump_mem(b'0123456789ABCDEFG', log=self.log)
        self.assertEqual(self.log_lines, [
            '0000: 30 31 32 33 34 35 36 37 38 39 41 42 43 44 45 46 0123456789ABCDEF',
            '0010: 47                                              G'
        ])

    def test_no_prefix_no_addr(self) -> None:
        """Tests with no prefix and no address"""
        self.clear_log()
        dump_mem(b'0123456789ABCDEFG', show_addr=False, log=self.log)
        self.assertEqual(self.log_lines, [
            '30 31 32 33 34 35 36 37 38 39 41 42 43 44 45 46 0123456789ABCDEF',
            '47                                              G'
        ])

    def test_no_prefix_no_addr_no_ascii(self) -> None:
        """Tests with no prefix, no address, and show_ascii turned off"""
        self.clear_log()
        dump_mem(b'0123456789ABCDEFG',
                 show_addr=False,
                 show_ascii=False,
                 log=self.log)
        self.assertEqual(
            self.log_lines,
            ['30 31 32 33 34 35 36 37 38 39 41 42 43 44 45 46', '47'])

    def test_addr(self) -> None:
        """Tests a non-zero address"""
        self.clear_log()
        dump_mem(b'0123456789ABCDEFG', addr=0x1234, log=self.log)
        self.assertEqual(self.log_lines, [
            '1234: 30 31 32 33 34 35 36 37 38 39 41 42 43 44 45 46 0123456789ABCDEF',
            '1244: 47                                              G'
        ])

    def test_addr_line_width(self) -> None:
        """Tests a non-zero adddress with a custom ine width"""
        self.clear_log()
        dump_mem(b'0123456789ABCDEFG', addr=0x1234, line_width=8, log=self.log)
        self.assertEqual(self.log_lines, [
            '1234: 30 31 32 33 34 35 36 37 01234567',
            '123c: 38 39 41 42 43 44 45 46 89ABCDEF',
            '1244: 47                      G'
        ])

    def test_non_printable(self) -> None:
        """Tests non-printable ASCII characters"""
        self.clear_log()
        dump_mem(b'012\x00\x01\x1e\x1f456', log=self.log)
        self.assertEqual(self.log_lines, [
            '0000: 30 31 32 00 01 1e 1f 34 35 36                   012....456',
        ])

    def test_neg_line_width(self) -> None:
        """Tests a negative line width"""
        self.clear_log()
        dump_mem(b'0123456789ABCDEFG',
                 prefix=PREFIX,
                 line_width=-6,
                 log=self.log)
        self.assertEqual(self.log_lines, [
            '    Prefix: 0000: 30 31 32 33 34 35 36 37 38 39 41 42 43 44 45 46 0123456789ABCDEF',
            '    Prefix: 0010: 47                                              G'
        ])


if __name__ == '__main__':
    unittest.main()
