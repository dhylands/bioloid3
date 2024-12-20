"""Implements a Bioloid IO Adapter running on an Espruino Pico."""

import pyb

import packet
from io_adapter import IO_Adapter
from stm_usb_port import USB_Port
from stm_uart_port import UART_Port
from bus import Bus
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


class LedSequence:

    def __init__(self, led, sequence, continuous=True):
        self.led = led
        self.last_toggle = 0
        self.sequence = sequence
        self.continuous = continuous
        self.seq_idx = -1
        self.led.off()
        if self.continuous:
            self.kick()

    def process(self):
        if self.seq_idx >= 0 and pyb.elapsed_millis(
                self.last_toggle) > self.sequence[self.seq_idx]:
            if self.seq_idx & 1 == 1:
                self.led.on()
            else:
                self.led.off()
            self.last_toggle = pyb.millis()
            self.seq_idx += 1
            if self.seq_idx >= len(self.sequence):
                if self.continuous:
                    self.seq_idx = 0
                else:
                    self.seq_idx = -1
                    self.led.off()  # Just in case we got an odd length

    def kick(self):
        if self.seq_idx < 0:
            self.seq_idx = 0
            self.led.on()
            self.last_toggle = pyb.millis()


class HeartBeat(LedSequence):

    def __init__(self, led):
        super().__init__(led, (20, 180, 20, 780), continuous=True)


class Activity(LedSequence):

    def __init__(self, led):
        super().__init__(led, (20, 20), continuous=False)


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
        log('  ID: {:3d} Model: {:5d} Version: {:5d}'.format(
            dev_id, model, version))
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


host_uart = USB_Port()
device_uart = UART_Port(device_uart_num, baud=1000000)

show = Bus.SHOW_NONE
dev = IO_Adapter(host_uart, show=show)

button = pyb.Switch()
rsp = packet.Packet()

log('Pico IO Adapter - Bioloid Packet Forwarder')
log('Control-C - Quit')
log('s - Scan Bus')
log('d - Debug - Show Packets')

last_update = 0

heartbeat = HeartBeat(RED_LED)
activity = Activity(GREEN_LED)
while True:
    heartbeat.process()
    activity.process()
    byte = host_uart.read_byte()
    if byte is not None:
        if dev.process_byte(byte) == packet.ErrorCode.NONE:
            # We've received a packet. See if it should be forwarded along
            pkt = dev.pkt
            if pkt.dev_id != dev.dev_id(
            ) or pkt.cmd == packet.Command.SYNC_WRITE:
                activity.kick()
                device_uart.write_packet(pkt.pkt_bytes)
                if show & Bus.SHOW_PACKETS:
                    dump_mem(pkt.pkt_bytes,
                             prefix='  H->D',
                             show_ascii=False,
                             log=log)

    if device_uart.any():
        byte = device_uart.read_byte()
        if rsp.process_byte(byte) == packet.ErrorCode.NONE:
            activity.kick()
            host_uart.write_packet(rsp.pkt_bytes)
            if show & Bus.SHOW_PACKETS:
                dump_mem(rsp.pkt_bytes,
                         prefix='  D->H',
                         show_ascii=False,
                         log=log)

    if repl_uart.any():
        byte = repl_uart.readchar()
        if byte == 3:  # Control-C
            log('Control-C')
            raise KeyboardInterrupt
        if byte == ord('d'):
            show = (show + 1) % 4
            if show & Bus.SHOW_COMMANDS:
                if show & Bus.SHOW_PACKETS:
                    log('Enabled Show Commands & Packets')
                else:
                    log('Enabled Show Commands')
            elif show & Bus.SHOW_PACKETS:
                log('Enabled Show Packets')
            else:
                log('Show None')
            dev.show = show
        elif byte == ord('s'):
            Scanner(Bus(device_uart, show=show)).scan()
    if button():
        log('Control-C via Button')
        raise KeyboardInterrupt
    if pyb.elapsed_millis(last_update) > 10:
        dev.update_gpios()
        dev.update_adcs()
        last_update = pyb.millis()
    pyb.wfi()
