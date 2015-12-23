#!/usr/bin/env python3

import socket

from device import Device
from socket_port import SocketPort
from fake_servo import FakeServo

IP_ADDR = '127.0.0.1'
IP_PORT = 8888

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((IP_ADDR, IP_PORT))

while True:
    print("Waiting for connection")
    s.listen(1)

    conn, addr = s.accept()
    print('Connection from:', addr)

    socket_port = SocketPort(conn)
    #dev = Device(1, socket_port, show_packets=True)
    dev = FakeServo(1, socket_port, show_packets=True)
    while True:
        data = socket_port.read_byte(block=True)
        if not data is None:
            dev.process_byte(data)
    conn.close()
