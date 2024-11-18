# type: ignore          - disabble PyLance for this file.
# pylint: skip-file     - duisable pylint for this file.
"""Stub classes for the pyb module."""


class ADC():
    """Stub class for ADC."""

    def __init__(self, name: str) -> None:
        """Constructor."""
        self.name = name
        self.value = 0

    def read(self) -> int:
        """Reads an ADC valie."""
        self.value += 256
        self.value %= 4096
        return self.value

    def __str__(self) -> str:
        """Returns a string representation of the ADC."""
        return self.name


class Pin():
    """Stub definitions for the Pin class."""

    IN = 'in'
    OUT_PP = 'out_pp'
    OUT_OD = 'out_od'

    PULL_NONE = 'pull_none'
    PULL_UP = 'pull_up'
    PULL_DOWN = 'pull_down'

    def __init__(self, name: str) -> None:
        self.name = name
        self.mode = Pin.IN
        self.pull = Pin.PULL_NONE
        self.val = 0

    def init(self, mode: str, pull: str):
        """Initializes the pin for use"""
        self.mode = mode
        self.pull = pull

    def value(self, val: int = None) -> Union[int, None]:
        """Returns the value of the pin"""
        if val is None:
            return 1
        self.val = val
        return None

    def __str__(self) -> str:
        """Returns a string representation of the pin"""
        return self.name


class UART:
    """Stub class for UART"""

    def __init__(self,
                 uart_num: int,
                 baudrate: int = 9600,
                 bits: int = 8,
                 parity=None,
                 stop: int = 1,
                 timeout: int = 0,
                 flow: int = 0,
                 timeout_char: int = 0,
                 read_buf_len: int = 64):
        """Constructor"""
        self.uart_num = uart_num
        self.baudrate = baudrate
        self.bits = bits
        self.parity = parity
        self.stop = stop
        self.timeout = timeout
        self.flow = flow
        self.timeout_char = timeout_char
        self.read_buf_len = read_buf_len

    def init(self,
             baudrate: int,
             bits: int = 8,
             parity=None,
             stop: int = 1,
             timeout: int = 0,
             flow: int = 0,
             timeout_char: int = 0,
             read_buf_len: int = 64) -> None:
        """Initializes the UART"""
        self.baudrate = baudrate
        self.bits = bits
        self.parity = parity
        self.stop = stop
        self.timeout = timeout
        self.flow = flow
        self.timeout_char = timeout_char
        self.read_buf_len = read_buf_len

    def any(self) -> int:
        """Returns the number 0f bytes waiting to be read."""
        return 1

    def readchar(self) -> int:
        """Reads a character from the UART."""
        return 0
