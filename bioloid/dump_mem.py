"""Provides the dump_mem function, which dumps memory in hex/ASCII."""

import sys
if sys.implementation.name == 'micropython':    # pragma: no cover
    import binascii

    def hexlify(buf):
        """Converts a binary string into its hex string representation
           with a space between each byte.
        """
        return binascii.hexlify(buf, ' ')
else:
    def hexlify(buf):
        """CPython's hexlify doesn't have the notion of a seperator character
           so we just do this the old fashioned way.
        """
        return bytes(' '.join(['{:02x}'.format(b) for b in buf]), 'ascii')

# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
# pylint: disable=too-many-branches


def dump_mem(buf, prefix='', addr=0, line_width=16, show_ascii=True,
             show_addr=True, log=print):
    """Dumps out a hex/ASCII representation of the given buffer."""
    if line_width < 0:
        line_width = 16
    if len(prefix) > 0:
        prefix += ':'
    if len(buf) == 0:
        log(prefix + 'No data')
        return
    buf_len = len(buf)
    # Use a memoryview to prevent unnecessary allocations
    buf_mv = memoryview(buf)
    line_ascii = ''
    ascii_offset = 0

    prefix_bytes = bytes(prefix, 'utf-8')
    prefix_len = len(prefix_bytes)
    if prefix_len > 0:
        prefix_len += 1     # For space between prefix and addr
    max_len = prefix_len
    if show_addr:
        max_len += 6
    hex_offset = max_len
    max_len += line_width * 3 - 1
    if show_ascii:
        ascii_offset = max_len + 1
        max_len += line_width + 1
    out_line = memoryview(bytearray(max_len))
    if prefix_len > 0:
        out_line[0:prefix_len-1] = prefix_bytes
        out_line[prefix_len-1:prefix_len] = b' '

    line_hex = out_line[hex_offset:hex_offset + (line_width * 3)]
    if show_ascii:
        # space between hex and ascii
        out_line[ascii_offset-1:ascii_offset] = b' '
        line_ascii = out_line[ascii_offset:ascii_offset + line_width]

    for offset in range(0, buf_len, line_width):
        if show_addr:
            out_line[prefix_len:prefix_len + 6] \
                = bytes('{:04x}: '.format(addr), 'ascii')
        line_bytes = min(buf_len - offset, line_width)
        line_hex[0:(line_bytes * 3)-1] \
            = hexlify(buf_mv[offset:offset+line_bytes])
        out_len = hex_offset + line_bytes * 3 - 1
        if show_ascii:
            if line_bytes < line_width:
                for i in range(line_bytes * 3 - 1, line_width * 3):
                    line_hex[i:i+1] = b' '
            line_ascii[0:line_bytes] = buf_mv[offset:offset + line_bytes]
            for i in range(line_bytes):
                char = line_ascii[i]
                if char < 0x20 or char > 0x7e:
                    line_ascii[i] = ord('.')
            out_len = ascii_offset + line_bytes
        log(bytes(out_line[0:out_len]).decode('utf-8'))
        addr += line_width
