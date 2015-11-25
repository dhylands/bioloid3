Bioloid3
========

My first major python program was [Bioloid ](https://github.com/dhylands/Bioloid)
which was written for python2.

Since I've been working with [MicroPython](http://micropython.org), which is
based on Python3, I decided that this would be a good opportunity to rewrite
the Bioloid functionality in Python3, and also make it a bit more usable on
embedded platforms like MicroPython.

# Bioloid devices

Dynamixel (aka Bioloid) devices are smart actuators made by [Robotis](http://en.robotis.com/index/product.php?cate_code=101010)
The communicate with the controlling computer using a packet based protocol.
The devices all communicate using a packet based protocol. The smaller
devices use a half-duplex serial interface, typically configured at 1 Mbit/sec.
The larger devices use an RS-485 interface.

This code should work with either, although I've only tested it with the AX series.

# PC Interface

You can use a device like the USB2Dynamixel. I created an adapter using an FTDI
chip along with a 74LVC2G241 buffer chip.

# MicroPython Interface

The pyboard can be connected directly to the signal line on the bioloid bus
utilizing just a UART TX line and ground. A special half-duplex mode on the STM32F4
processor is utilized to allow bi-directional communications.

# Overview of files

## test.py

test.py is a test program which will exercise all of the various commands,
except for reset. 

It will perform the following:

* scan the bus looking for devices. It will print out the model and version
of each device. This tests PING and READ.

* turn on and off the led of each device a total of 4 times (one device and a
time). This tests WRITE.

* tun on and off all LEDs simultaneously, 4 times. This tests the REG_WRITE and
ACTION commands (REG_WRITE is a deferred write).

* turn on and off all LEDs simultaneously, 4 times This tests the SYNC_WRITE
command.

## packet.py

This file contains numerous constants used for communicating with the bioloid
devices, along with a packet parser.

### packet.Packet

An instance of this class is returned for each response packet received from
a bioloid device.

#### packet.param_byte(index)

If the response includes parameter data, then this will retrieve byte given
by `idx` of the response.

#### packet.params()

Returns a bytearray containing all of the bytes of the parmeters in the response.

#### packet.param_len()

Returns the number of parameter bytes in the packet.

#### packet.error_code()

Returns the error code returned in the repsonse packet.

#### packet.error_code_str()

Returns a string representation of the error code.

#### packet.process_byte(byte)

Called to parse each byte received on the bus. Returns packet.ErrorCode.NOT_DONE
if the packet is incomplete, packet.ErrorCode.NONE if the packet was
received successfully, and packet.ErrorCode.CHECKSUM is a checksum error was
detected.

Once a packet is parsed successfully, then the other functions can be called
to retrieve data from the packet.

## bus.py

This file contains the Bus class which is an abstract class for interfacing
with the bioloid devices. The Bus class knows how to format all of the various
command packets that can be sent to the bioloid devices and parses the response
packets which are recieved back.

It is expected that this class will be derived, and that he derived class will
provide the read_byte and write_packet routines which actuall send and receive
the bytes.

### Device Commands

#### Bus.action()

Broadcasts an ACTION command. This instructs all of the device to perform
their deferred writes. This function returns no data, and raises no exceptions.

#### Bus.ping(dev_id)

Sends a PING request to the device with an ID of `dev_id`. Returns True if the
device responds successfully, False if a timeout occurs (typicall no device).
If the response contains any errors, then a Bus.BusError will be raised.
Note that ping will return False rather than raise a BusError with an
error code of packet.ErrorCode.Timeout.

#### Bus.read(dev_id, offset, num_bytes)

Sends a READ request to the device with an ID of `dev_id` and returns any data read.
The data is read starting at an address of `offset` for a length of `num_bytes`.
If the response was successful, then a bytearray containing the data read is returned.
If the response contains any errors, then a Bus.BusError will be raised.

#### Bus.reset(dev_id)

Sends a RESET command to the device with an ID of `dev_id`, which causes it
to reset the control table to factory defaults. Note that this will change
the ID to 1. If the response contains any errors, then a Bus.BusError will
be raised.

#### Bus.scan(start_id=0, num_ids=32, dev_found=None, dev_missing=None)

Sends a ping to all of the devices between start_id and start_id + num_ids - 1.
If dev_found is not None, and the ping returns True then dev_found(bus, dev_id) will be called.
If dev_missing is not None, and the ping return False, then dev_missing(bus, dev_id) will be called.
This function will return True if one or more devices were found, False otherwise.
If a response contains any errors, then a Bus.BusError will be raised.

#### Bus.sync_write(dev_ids, offset, values)

Broadcasts a SYNC_WRITE command. `dev_ids` should be a list of device ids.
`values` should be a list of bytearrays. len(values) should be identical to
len(dev_ids). Each bytearray should be of the same length and contains the
data to be written to each device.
`offset` contains the offset where the data will be written, and is the same
for each device.
This function will raise a ValueError if the lengths of the arrays are not
consistent.

#### Bus.write(dev_id, offset, data, deferred=False)

Sends a WRITE commaned to the device with an ID of `dev_id`. The data will be
written to the device start at an address of `offset`. `data` should be a
bytearray containing the data to be written.
If the response contains any errors, then a Bus.BusError will be raised.

### Async Commands

The send_ping, send_read, send_reset, and send_write functions do the same
thing as the versions without the send_ prefix, but don't wait for any
response packet.
These functions return nothing and raise no exceptions.

### Low Level Functions

#### Bus.fill_and_write_packet(dev_id, cmd, data)

Allocates and files a packet using `dev_id`, `cmd`, and `data`. `data`
should be a bytearray.

#### Bus.read_status_packet()

Waits for a reponse packet from the device. If a packet is successfully
parsed, then a packet.Packet instance will be returned, otherwise a
Bus.BusError will be raised.

### Functions which the derived class need to implement

#### Bus.readbyte()

The derived bus class should return the next character received, or None
if a timeout occurs. The maximum Return Delay Time is 254 * 2 usec = 508 usec,
so this function should have a fairly short timeout.

#### Bus.write_packet(packet_data)

Writes `packet_data`, which will be a byte array to the bus. This function
returns nothing and raises no exceptions.

## stm_uart_bus.py

Implements a derived Bus class called UART_Bus uses MicroPython's pyb.UART class to
read and write the data.

The UART_Bus constructor looks like UART_Bus(uart_num, baud, show_packets=False)
where `uart_num` and `baud` are passed to `pyb.UART`. If `show_packets` is True
then the packet contents and responses will be printed (sometimes useful for
debugging).

This class uses a special half-duplex mode which is available on the STM32F4 MCUs.

## serial_bus.py

Implements a derived class called SerialBus which uses pyserial to read and
write the data.

The SerialBus constructor looks like SerialBus(port, baud, show_packets=False)
where `port` and `baud` are passed to `serial.Serial` constructor.
If `show_packets` is True then the packet contents and responses will be
printed (sometimes useful for debugging).

## dump_mem.py

Is a general purpose routine for printing hex-dumps.

