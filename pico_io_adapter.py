"""Implements a Bioloid IO Adapter running on an Espruino Pico."""

import pyb

from io_adapter import IO_Adapter
from stm_usb_bus import USB_Bus
from log import log, log_to_uart
import os
import sys

RED_LED = pyb.LED(1)
GREEN_LED = pyb.LED(2)

machine = os.uname().machine
if machine.startswith('Espruino Pico'):
    uart_num = 1
elif machine.startswith('PYB'):
    uart_num = 4
else:
    print("Unrecognized board: '{}'".format(machine))
    sys.exit(1)

uart = pyb.UART(uart_num, 115200)
log_to_uart(uart)
# By putting the REPL on the logging UART, it means that any tracebacks will
# go to the uart.
pyb.repl_uart(uart)

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
serial = USB_Bus()
dev = IO_Adapter(serial, show_packets=True)

last_update = 0
while True:
    heartbeat.process()
    byte = serial.read_byte()
    if not byte is None:
        dev.process_byte(byte)
    if uart.any():
        byte = uart.readchar()
        if byte == 3:  # Control-C
            log('Control-C')
            raise KeyboardInterrupt
    if pyb.elapsed_millis(last_update) > 10:
        dev.update_gpios()
        dev.update_adcs()
        last_update = pyb.millis()
    pyb.wfi()

