#!/usr/bin/env python3

"""This is a test program for testing the code out on the host."""

import array
import os
import struct
import sys
import time
from commander_rx import CommanderRx

sysname = os.uname().sysname
if sysname == 'Linux' or sysname == 'Darwin':
    import serial
    from serial_port import SerialPort
    from serial_bus import SerialBus
    port = '/dev/ttyUSB0'
    try:
        port = SerialPort(port, 38400)
    except serial.serialutil.SerialException:
        print("Unable to open port '{}'".format(port))
        sys.exit()

elif sysname == 'pyboard':
    from stm_uart_port import UART_Port
    port = UART_Port(6, 38400)
else:
    print("Unrecognized sysname: {}".format(sysname))
    sys.exit()

crx = CommanderRx()

while True:
    byte = port.read_byte()
    if not byte is None:
        #print('Byte =', byte)
        if crx.process_byte(byte) == CommanderRx.SUCCESS:
            print('Walk: {:4d}h {:4d}v Look: {:4d}h {:4d}v {:08b}'.format(crx.walkh, crx.walkv, crx.lookh, crx.lookv, crx.button))

