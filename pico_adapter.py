"""Implements a Bioloid IO Adapter running on an Espruino Pico."""

import pyb
import packet

from stm_usb_bus import USB_Bus
from stm_uart_bus import UART_Bus

from dump_mem import dump_mem
from log import log, log_to_uart

import os
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

heartbeat = HeartBeat(RED_LED)
host_uart = USB_Bus()
device_uart = UART_Bus(device_uart_num, baud=1000000, show_packets=True)

pkt = packet.Packet()
rsp = packet.Packet()
while True:
    heartbeat.process()
    byte = host_uart.read_byte()
    if byte is not None:
        rc = pkt.process_byte(byte)
        if rc != packet.ErrorCode.NOT_DONE:
            #dump_mem(pkt.pkt_bytes, prefix='  H->D', show_ascii=False, log=log)
            device_uart.write_packet(pkt.pkt_bytes)

    if device_uart.rx_enabled and device_uart.any():
        byte = device_uart.read_byte()
        rc = rsp.process_byte(byte)
        if rc != packet.ErrorCode.NOT_DONE:
            host_uart.write_packet(rsp.pkt_bytes)
            #dump_mem(rsp.pkt_bytes, prefix='  D->H', show_ascii=False, log=log)

    if repl_uart.any():
        byte = repl_uart.readchar()
        if byte == 3:  # Control-C
            log('Control-C')
            raise KeyboardInterrupt
    pyb.wfi()
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        
