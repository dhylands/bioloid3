#!/usr/bin/env python3
"""This is a test program for testing the code out on the host."""

import os
import struct
import sys
from bioloid.bus import Bus, BusError
from bioloid.log import log


class Scanner(object):
    """Class for scanning for devices."""

    def __init__(self, bus):
        self.bus = bus
        self.ids = []

    def dev_found(self, bus, dev_id):
        """Called when a device ie discovered."""
        # We want to read the model and version, which is at offset 0, 1,
        # and 2 so we do it with a single read.
        try:
            data = bus.read(dev_id, 0, 3)
        except BusError:
            log(f'Device {dev_id} READ timed out')
            return
        model, version = struct.unpack('<HB', data)
        log(f'  ID: {dev_id:3d} Model: {model:5d} Version: {version:5d}')
        self.ids.append(dev_id)

    def scan_range(self, start_id=1, num_ids=32):
        """Scans for devices in a range of device ids."""
        log('Scanning IDs from', start_id, 'to', start_id + num_ids)
        try:
            self.bus.scan(start_id, num_ids, self.dev_found, None)
        except BusError:
            log('Timeout')

    def scan(self):
        """Scans for devices in the entire ramge."""
        self.ids = []
        self.scan_range(0, 32)
        self.scan_range(100, 32)
        if len(self.ids) == 0:
            log('No devices found')
        else:
            log('Scan done')


def scan(bus):
    """Scans the bus looking for devices."""
    scanner = Scanner(bus)
    scanner.scan()


def pyboard_main():
    """main function called when running on a pyboard."""
    from stm_uart_port import UartPort
    serial = UartPort(2, 1000000)
    bus = Bus(serial, show=Bus.SHOW_NONE)
    scan(bus)


def linux_main():
    """main function called when running under linux."""
    import argparse

    default_baud = 1000000
    default_port = os.getenv("BIOLOID_PORT") or '/dev/ttyUSB0'
    parser = argparse.ArgumentParser(
        prog="test",
        usage="%(prog)s [options] [command]",
        description="Send commands to bioloid devices",
        epilog=("You can specify the default serial port using the " +
                "BIOLOID_PORT environment variable."))
    parser.add_argument(
        "-b",
        "--baud",
        dest="baud",
        action="store",
        type=int,
        help=f"Set the baudrate used (default = {default_baud})",
        default=default_baud)
    default_port_help = ""
    if default_port:
        default_port_help = f" (default '{default_port}')"
    parser.add_argument("-p",
                        "--port",
                        dest="port",
                        help=f"Set the serial port to use{default_port_help}",
                        default=default_port)
    parser.add_argument("-n",
                        "--net",
                        dest="net",
                        action="store_true",
                        help="Connect to a device using TCP/IP",
                        default=False)
    parser.add_argument("-v",
                        "--verbose",
                        dest="verbose",
                        action="store_true",
                        help="Turn on verbose messages",
                        default=False)
    parser.add_argument("--dummy",
                        dest="dummy",
                        action="store_true",
                        help="Uses DummyPort",
                        default=False)
    parser.add_argument("--show-commands",
                        dest="show_commands",
                        action="store_true",
                        help="Show commands being sent/received",
                        default=False)
    parser.add_argument("--show-packets",
                        dest="show_packets",
                        action="store_true",
                        help="Show packets being sent/received",
                        default=False)
    args = parser.parse_args(sys.argv[1:])

    show = Bus.SHOW_NONE
    if args.show_commands:
        show |= Bus.SHOW_COMMANDS
    if args.show_packets:
        show |= Bus.SHOW_PACKETS

    if args.dummy:
        from dummy_port import DummyPort
        dev_port = DummyPort()
        show = Bus.SHOW_COMMANDS | Bus.SHOW_PACKETS
    elif args.net:
        import socket
        from bioloid.socket_port import SocketPort

        IP_ADDR = '127.0.0.1'
        IP_PORT = 8888
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((IP_ADDR, IP_PORT))
        dev_port = SocketPort(s)
    else:
        import serial
        from bioloid.serial_port import SerialPort
        try:
            dev_port = SerialPort(args.port, args.baud)
        except serial.serialutil.SerialException:
            print(f"Unable to open port '{args.port}'")
            sys.exit()
    bus = Bus(dev_port, show=show)
    scan(bus)


def main():
    sysname = os.uname().sysname
    if sysname == 'Linux' or sysname == 'Darwin':
        linux_main()
    elif sysname == 'pyboard':
        pyboard_main()
    else:
        print(f"Unrecognized sysname: {sysname}")
        sys.exit()


main()
