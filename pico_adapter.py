"""Implements a Bioloid IO Adapter running on an Espruino Pico."""

import pyb
import packet
from bus import BusError

from stm_usb_bus import USB_Bus
from stm_uart_bus import UART_Bus

from bus import Bus
from dump_mem import dump_mem
from log import log, log_to_uart

import os
import struct
import sys

RED_LED = pyb.LED(1)
GREEN_LED = pyb.LED(2)

machine = os.uname().machine
if machine.startswith('Espruino Pico'):
    repl_uart_num = 1
    device_uart_num = 2
elif machine.startswith('PYB'):
    repl_uart_num = 4
    device_uart_num = 6
else:
    print("Unrecognized board: '{}'".format(machine))
    sys.exit(1)

repl_uart = pyb.UART(repl_uart_num, 115200)
log_to_uart(repl_uart)
# By putting the REPL on the logging UART, it means that any tracebacks will
# go to the uart.
pyb.repl_uart(repl_uart)

class HeartBeat:

    def __init__(self, led):
        self.led = led
        self.led.off()
        self.last_tick = pyb.millis()
        self.counter = 0

    def process(self):
        if pyb.elapsed_millis(self.last_tick) > 100:
            self.last_tick = pyb.millis()
            if self.counter <= 3:
                self.led.toggle()
            self.counter += 1
            self.counter %= 10

class Activity:

    def __init__(self, led):
        self.led = led
        self.led.off()
        self.led_on = False
        self.on_tick = 0
        self.off_tick = 0

    def process(self):
        if self.led_on and pyb.elapsed_millis(self.on_tick) > 20:
            self.led.off()
            self.led_on = False
            self.on_tick = pyb.millis()

    def kick(self):
        if not self.led_on and pyb.elapsed_millis(self.off_tick) > 20:
            self.led.on()
            self.led_on = True
            self.off_tick = pyb.millis()


class Scanner(object):

    def __init__(self, bus):
        self.bus = bus
        self.ids = []

    def dev_found(self, bus, dev_id):
        # We want to read the model and version, which is at offset 0, 1,
        # and 2 so we do it with a single read.
        try:
            data = bus.read(dev_id, 0, 3)
        except BusError:
            log('Device {} READ timed out'.format(dev_id))
            return
        model, version = struct.unpack('<HB', data)
        log('  ID: {:3d} Model: {:5d} Version: {:5d}'.format(dev_id, model, version))
        self.ids.append(dev_id)

    def scan_range(self, start_id=1, num_ids=32):
        log('Scanning IDs from', start_id, 'to', start_id + num_ids)
        try:
            self.bus.scan(start_id, num_ids, self.dev_found, None)
        except BusError:
            log('Timeout')

    def scan(self):
        self.ids = []
        self.scan_range(0, 32)
        self.scan_range(100, 32)
        if len(self.ids) == 0:
            log('No devices found')
        else:
            log('Scan done')


heartbeat = HeartBeat(RED_LED)
activity = Activity(GREEN_LED)
host_uart = USB_Bus()
device_uart = UART_Bus(device_uart_num, baud=1000000, show_packets=True)

button = pyb.Switch()

pkt = packet.Packet()
rsp = packet.Packet()

log('Pico Adapter - Bioloid Packet Forwarder')
show_packets = False
while True:
    heartbeat.process()
    activity.process()
    byte = host_uart.read_byte()
    if byte is not None:
        rc = pkt.process_byte(byte)
        if rc != packet.ErrorCode.NOT_DONE:
            if show_packets:
                dump_mem(pkt.pkt_bytes, prefix='  H->D', show_ascii=False, log=log)
            activity.kick()
            device_uart.write_packet(pkt.pkt_bytes)

    if device_uart.rx_enabled and device_uart.any():
        byte = device_uart.read_byte()
        rc = rsp.process_byte(byte)
        if rc != packet.ErrorCode.NOT_DONE:
            activity.kick()
            host_uart.write_packet(rsp.pkt_bytes)
            if show_packets:
                dump_mem(rsp.pkt_bytes, prefix='  D->H', show_ascii=False, log=log)

    if repl_uart.any():
        byte = repl_uart.readchar()
        if byte == 3:  # Control-C
            log('Control-C')
            raise KeyboardInterrupt
        elif byte == ord('d'):
            show_packets = not show_packets
            log('Show Packets:', show_packets)
        elif byte == ord('s'):
            Scanner(Bus(device_uart, show_packets)).scan()
    if button():
        log('Control-C via Button')
        raise KeyboardInterrupt
    pyb.wfi()
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        
