"""Provides the dump_mem function, which dumps memory in hex/ASCII."""

from log import log

def dump_mem(buf, prefix="", address=0, line_width=16, show_ascii=True,
             show_addr=True):
    """Dumps out a hex/ASCII representation of the given buffer."""
    if line_width < 0:
        line_width = 16
    if len(prefix) > 0:
        prefix += ': '
    if len(buf) == 0:
        log(prefix + 'No data')
        return
    buf_len = len(buf)
    for offset in range(0, buf_len, line_width):
        line_hex = ''
        line_ascii = ''
        for line_offset in range(0, line_width):
            ch_offset = offset + line_offset
            if ch_offset < buf_len:
                char = buf[offset + line_offset]
                line_hex += '{:02x} '.format(char)
                if char < 0x20 or char > 0x7e:
                    line_ascii += '.'
                else:
                    line_ascii += chr(char)
            else:
                if show_ascii:
                    line_hex += '   '
                else:
                    break
        out_line = prefix
        if show_addr:
            out_line += '{:04x}: '.format(address)
        out_line += line_hex
        if show_ascii:
            out_line += line_ascii
        else:
            # Remove the trailing space after the last hex
            out_line = out_line[0:-1]
        log(out_line)
        address += line_width

