"""Test Program to test the rp2_uart_port.py file

    This particular test assumes that UART 0 is on GPIO 12 & 13
    and that UART 1 is in GPIO 8 & 9, and that all 4 of those GPIOs
    are jumpered together.
"""

import machine
import select
import sys
import time

from bioloid import packet

from bioloid.bus import Bus
from bioloid.bus import BusError

from bioloid.dump_mem import dump_mem
from bioloid.log import log, log_to_uart

from bioloid.rp2_uart_port import UART_Port


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
        if self.seq_idx >= 0 and time.ticks_diff(
                time.ticks_ms(),
                self.last_toggle) > self.sequence[self.seq_idx]:
            self.led.toggle()
            self.last_toggle = time.ticks_ms()
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
            self.last_toggle = time.ticks_ms()


class HeartBeat(LedSequence):

    def __init__(self, led):
        super().__init__(led, (20, 180, 20, 780), continuous=True)


LED = machine.Pin('LED', machine.Pin.OUT)

heartbeat = HeartBeat(LED)

# Open the UARTs so that we assign the correct pins.
uart0 = machine.UART(0,
                     baudrate=1000000,
                     tx=machine.Pin(12),
                     rx=machine.Pin(13))
uart1 = machine.UART(1, baudrate=1000000, tx=machine.Pin(8), rx=machine.Pin(9))

uart0_port = UART_Port(0, baud=1000000)
uart1_port = UART_Port(1, baud=1000000)

show = Bus.SHOW_PACKETS
bus0 = Bus(uart0_port, show=show)
bus1 = Bus(uart1_port, show=show)

rsp0 = packet.Packet()
pkt1 = packet.Packet()

log('rp2_uart_port Test Program')


def process_stdin() -> bool:
    ch = sys.stdin.read(1)
    print('Got', ch)
    if ch == 'q':
        print('Quitting')
        return False
    if ch == 'd':
        bus0.show ^= Bus.SHOW_PACKETS
        bus1.show ^= Bus.SHOW_PACKETS
        log('Show Packets:', bool(bus0.show & Bus.SHOW_PACKETS))
        return True
    if ch == 'p':
        bus0.send_ping(0x20)
        return True
    return True


def process_bus0(byte):
    """We receive responses on bus0"""
    rc = rsp0.process_byte(byte)
    if rc == packet.ErrorCode.NOT_DONE:
        return
    if bus0.show & Bus.SHOW_PACKETS:
        dump_mem(rsp0.pkt_bytes, prefix='0 R', show_ascii=False, log=log)
    err_code = rsp0.cmd
    if err_code == packet.ErrorCode.NONE:
        log('0 Got RSP')


def process_bus1(byte):
    """We receive commands on bus1"""
    rc = pkt1.process_byte(byte)
    if rc == packet.ErrorCode.NOT_DONE:
        return
    if bus1.show & Bus.SHOW_PACKETS:
        dump_mem(pkt1.pkt_bytes, prefix='1 R', show_ascii=False, log=log)
    if pkt1.cmd == packet.Command.PING:
        log('1 Got PING')
        pkt_bytes = bytearray(6)
        pkt_bytes[0] = 0xff
        pkt_bytes[1] = 0xff
        pkt_bytes[2] = pkt1.dev_id
        pkt_bytes[3] = 2  # for len and status
        pkt_bytes[4] = packet.ErrorCode.NONE
        check_sum = pkt_bytes[2] + pkt_bytes[3]
        pkt_bytes[5] = ~check_sum & 0xff
        if bus1.show & Bus.SHOW_PACKETS:
            dump_mem(pkt_bytes, prefix='1 W', show_ascii=False, log=log)
        bus1.serial_port.write_packet(pkt_bytes)


poll = select.poll()
poll.register(sys.stdin, select.POLLIN)
poll.register(bus0.serial_port.uart, select.POLLIN)
poll.register(bus1.serial_port.uart, select.POLLIN)

done = False
while not done:
    heartbeat.process()
    for event in poll.ipoll(10):
        if event[0] == sys.stdin:
            done = not process_stdin()
        elif event[0] == bus0.serial_port.uart:
            byte = bus0.serial_port.read_byte()
            process_bus0(byte)
        elif event[0] == bus1.serial_port.uart:
            byte = bus1.serial_port.read_byte()
            process_bus1(byte)
