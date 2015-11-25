#!/usr/bin/env python3

"""This is a test program for testing the code out on the host."""

import array
import os
import struct
import sys
import time

LED_OFFSET = 0x19

class Scanner(object):

    def __init__(self, bus, start_id=0, num_ids=32):
        self.scan_idx = 0
        self.scan_spin = "-\\|/"
        self.ids = []
        bus.scan(start_id, num_ids, self.dev_found, None)

    def dev_found(self, bus, dev_id):
        # We want to read the model and version, which is at offset 0, 1,
        # and 2 so we do it with a single read.
        data = bus.read(dev_id, 0, 3)
        model, version = struct.unpack('<HB', data)
        print('ID: {:3d} Model: {:5d} Version: {:5d}'.format(dev_id, model, version))
        if model == 12:
            self.ids.append(dev_id)


sysname = os.uname().sysname
if sysname == 'Linux':
    import serial
    from serial_bus import SerialBus
    port = '/dev/ttyUSB0'
    try:
        bus = SerialBus(port, 1000000, show_packets=False)
    except serial.serialutil.SerialException:
        print("Unable to open port '{}'".format(port))
        sys.exit()

elif sysname == 'pyboard':
    from stm_uart_bus import UART_Bus
    bus = UART_Bus(6, 1000000, show_packets=False)
else:
    print("Unrecognized sysname: {}".format(sysname))
    sys.exit()

# Scan the bus (tests PING and READ)

print('Scan the bus (tests PING and READ)')
scanner = Scanner(bus)
if len(scanner.ids) == 0:
    print('No bioloid servos detected')
    sys.exit()

print('Cycle through the LEDs (tests WRITE)')
for i in range(4):
    for dev_id in scanner.ids:
        bus.write(dev_id, LED_OFFSET, bytearray((1,)))
        time.sleep(0.25)
        bus.write(dev_id, LED_OFFSET, bytearray((0,)))
        time.sleep(0.25)

time.sleep(1)

print('Turn all LEDs on and off simultaneously (tests REG_WRITE and ACTION)')
for i in range(4):
    for dev_id in scanner.ids:
        bus.write(dev_id, LED_OFFSET, bytearray((1,)), deferred=True)
    bus.action()
    time.sleep(0.25)
    for dev_id in scanner.ids:
        bus.write(dev_id, LED_OFFSET, bytearray((0,)), deferred=True)
    bus.action()
    time.sleep(0.25)

time.sleep(1)

print('Turn all LEDs on and off simultaneously (tests SYNC_WRITE)')
for i in range(4):
    bus.sync_write(scanner.ids, LED_OFFSET, [bytearray((1,))] * len(scanner.ids))
    time.sleep(0.25)
    bus.sync_write(scanner.ids, LED_OFFSET, [bytearray((0,))] * len(scanner.ids))
    time.sleep(0.25)

