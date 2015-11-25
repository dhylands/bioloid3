#!/usr/bin/python3

from dump_mem import dump_mem

PREFIX = '    Prefix'
print('Empty Buffer')
dump_mem(b'', prefix=PREFIX)

print
print('Less than line')
dump_mem(b'0123', prefix=PREFIX)

print
print('Exactly one line')
dump_mem(b'0123456789ABCDEF', prefix=PREFIX)

print
print('A bit more than a line')
dump_mem(b'0123456789ABCDEFGHI', prefix=PREFIX)

print
print('Set a prefix')
dump_mem(b'0123', prefix='    Something')

print
print('Set an address and a line_width')
dump_mem(b'0123456789ABCDEFGHI', address=0x2000, line_width=8,
         prefix=PREFIX)

DATA = bytearray([0x30, 0x31, 0x32, 0x33, 0, 0x80, 0xFF])
print
print('Check out some non-printable characters')
dump_mem(DATA, prefix=PREFIX)

print
print('With no prefix')
dump_mem(b'0123')
