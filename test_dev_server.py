#!/usr/bin/env python3

"""
This program starts a socket and emulates the indicated device(s). Received packets will be sent
to the device the same as when they're sitting on a serial bus and the replies will be sent back
to the other end of the socket.
"""

import argparse
import socket
import sys

from bioloid.bus import Bus
from bioloid.device import Device
from bioloid.socket_port import SocketPort

from fake_servo import FakeServo
from fake_io_adapter import Fake_IO_Adapter

IP_ADDR = '127.0.0.1'
IP_PORT = 8888
SHOW = Bus.SHOW_NONE

FAKE_SERVO_ID = 1
IO_ADAPTER_ID = 1

def main():
    parser = argparse.ArgumentParser(
        #prog="test_dev_server.py",
        #usage="%(prog)s [options] [command]",
        description="Simulate Bioloid devices over a network socket",
    )
    parser.add_argument(
        "-v", "--verbose",
        dest="verbose",
        action="store_true",
        help="Turn on verbose messages",
        default=False
    )
    parser.add_argument(
        "--servo",
        dest="servo",
        action="store_true",
        help="Simulate a Servo device",
        default=False
    )
    parser.add_argument(
        "--io-adapter",
        dest="io_adapter",
        action="store_true",
        help="Simulate an IO_Adapter device",
        default=False
    )

    args = parser.parse_args(sys.argv[1:])

    if args.verbose:
        global SHOW
        SHOW = Bus.SHOW_PACKETS | Bus.SHOW_COMMANDS

    if args.servo:
        print('Instantiating a FakeServo on device', FAKE_SERVO_ID)
        dev = FakeServo(FAKE_SERVO_ID, None, show=SHOW)
    elif args.io_adapter:
        print('Instantiating an I/O Adapter on device', IO_ADAPTER_ID)
        dev = Fake_IO_Adapter(IO_ADAPTER_ID, None, show=SHOW)
    else:
        print('Need to specify a device to simulate')
        return

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((IP_ADDR, IP_PORT))

    while True:
        print("Waiting for connection")
        s.listen(1)

        conn, addr = s.accept()
        print('Connection from:', addr)

        socket_port = SocketPort(conn)

        dev.set_port(socket_port)
        while True:
            data = socket_port.read_byte(block=True)
            if not data is None:
                dev.process_byte(data)
            else:
                break
        print('Remote disconnected')
        print('')
        conn.close()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt as exc:
        print('Quitting due to Control-C')
