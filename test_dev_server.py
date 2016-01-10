#!/usr/bin/env python3

import argparse
import socket
import sys

from device import Device
from socket_port import SocketPort

IP_ADDR = '127.0.0.1'
IP_PORT = 8888

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

    show_packets = args.verbose

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((IP_ADDR, IP_PORT))

    while True:
        print("Waiting for connection")
        s.listen(1)

        conn, addr = s.accept()
        print('Connection from:', addr)
        print('type of conn', type(conn))
        print('type of addr', type(addr))

        socket_port = SocketPort(conn)
        if args.servo:
            from fake_servo import FakeServo
            dev = FakeServo(1, socket_port, show_packets=show_packets)
        elif args.io_adapter:
            from fake_io_adapter import Fake_IO_Adapter
            dev = Fake_IO_Adapter(1, socket_port, show_packets=show_packets)
        else:
            print('Need to specify a device to simulate')
            break
        while True:
            data = socket_port.read_byte(block=True)
            if not data is None:
                dev.process_byte(data)
        conn.close()

main()
