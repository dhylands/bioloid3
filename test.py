#!/usr/bin/env python3
"""This is a test program for testing the code out on the host."""

import os
import struct
import sys
import time
from bioloid.bus import Bus

LED_OFFSET = 0x19


class Scanner(object):

    def __init__(self, bus, start_id=1, num_ids=32):
        self.scan_idx = 0
        self.scan_spin = "-\\|/"
        self.ids = []
        bus.scan(start_id, num_ids, self.dev_found, None)

    def dev_found(self, bus, dev_id):
        # We want to read the model and version, which is at offset 0, 1,
        # and 2 so we do it with a single read.
        data = bus.read(dev_id, 0, 3)
        model, version = struct.unpack('<HB', data)
        print('ID: {:3d} Model: {:5d} Version: {:5d}'.format(
            dev_id, model, version))
        if model == 12:
            self.ids.append(dev_id)


def test(bus):
    # Scan the bus (tests PING and READ)

    print('Scan the bus (tests PING and READ)')
    scanner = Scanner(bus)
    if len(scanner.ids) == 0:
        print('No bioloid servos detected')
        sys.exit()

    print('Cycle through the LEDs (tests WRITE)')
    for i in range(4):
        for dev_id in scanner.ids:
            bus.write(dev_id, LED_OFFSET, bytearray((1, )))
            time.sleep(0.25)
            bus.write(dev_id, LED_OFFSET, bytearray((0, )))
            time.sleep(0.25)

    time.sleep(1)

    print(
        'Turn all LEDs on and off simultaneously (tests REG_WRITE and ACTION)')
    for i in range(4):
        for dev_id in scanner.ids:
            bus.write(dev_id, LED_OFFSET, bytearray((1, )), deferred=True)
        bus.action()
        time.sleep(0.25)
        for dev_id in scanner.ids:
            bus.write(dev_id, LED_OFFSET, bytearray((0, )), deferred=True)
        bus.action()
        time.sleep(0.25)

    time.sleep(1)

    print('Turn all LEDs on and off simultaneously (tests SYNC_WRITE)')
    for i in range(4):
        bus.sync_write(scanner.ids, LED_OFFSET, [bytearray(
            (1, ))] * len(scanner.ids))
        time.sleep(0.25)
        bus.sync_write(scanner.ids, LED_OFFSET, [bytearray(
            (0, ))] * len(scanner.ids))
        time.sleep(0.25)


def pyboard_main():
    from bioloid.stm_uart_port import UART_Port
    serial_port = UART_Port(6, 1000000)
    bus = Bus(serial_port, show_packets=False)
    test(bus)


def linux_main():
    import argparse

    default_baud = 1000000
    default_port = os.getenv("BIOLOID_PORT") or '/dev/ttyUSB0'
    parser = argparse.ArgumentParser(
        prog="test",
        usage="%(prog)s [options] [command]",
        description="Send commands to bioloid devices",
        epilog=("You can specify the default serial port using the " +
                "BIOLOID_PORT environment variable."))
    parser.add_argument("-b",
                        "--baud",
                        dest="baud",
                        action="store",
                        type=int,
                        help="Set the baudrate used (default = %d)" %
                        default_baud,
                        default=default_baud)
    default_port_help = ""
    if default_port:
        default_port_help = " (default '%s')" % default_port
    parser.add_argument("-p",
                        "--port",
                        dest="port",
                        help="Set the serial port to use" + default_port_help,
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
    args = parser.parse_args(sys.argv[1:])

    if args.verbose:
        show = Bus.SHOW_PACKETS
    else:
        show = Bus.SHOW_NONE
    if args.dummy:
        from dummy_port import DummyPort
        dev_port = DummyPort()
        show = Bus.SHOW_PACKETS
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
            print("Unable to open port '{}'".format(port))
            sys.exit()
    bus = Bus(dev_port, show=show)
    test(bus)


def main():
    sysname = os.uname().sysname
    if sysname == 'Linux' or sysname == 'Darwin':
        linux_main()
    elif sysname == 'pyboard':
        pyboard_main()
    else:
        print("Unrecognized sysname: {}".format(sysname))
        sys.exit()


main()
