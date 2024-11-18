"""Implements a simple logger abstraction that can allow data to be directed
   someplace other than stdout.

   Currently we can't redirecty sys.stdout on MicroPython which means that
   print always goes to USB, even if we don't want it to.
"""

import os
if os.uname().sysname == 'Linux':
    from typing import Callable


def log_to_none_fn(_args) -> None:
    """Logs to the bitbucket"""


log_fn = log_to_none_fn


def log(*args) -> None:
    """Make log call log_fn so that other modules can use:

       from log import log, log_to_xxx

       and then call log_to_xxx and have the changes take effect.
    """
    log_fn(args)


def log_to_fn(fn: Callable[..., None]) -> None:
    global log_fn  # pylint: disable=global-statement
    log_fn = fn


def log_to_none() -> None:
    """Sets up logging to log to the bitbucket"""
    log_to_fn(log_to_none_fn)


def log_to_print() -> None:
    """Sets up logging to use print"""

    def log_to_print_fn(args) -> None:
        print(*args)

    log_to_fn(log_to_print_fn)


def log_to_file(file) -> None:
    """Sets up logging to log to a file"""

    def log_to_file_fn(args):
        """Log output by writing to a file"""
        file.write(' '.join([str(arg) for arg in args]))
        file.write('\n')

    log_to_fn(log_to_file_fn)


def log_to_uart(uart) -> None:
    """Sets up logging to log"""

    def log_to_uart_fn(args):
        """Logs output by writing to a UART"""
        uart.write(' '.join([str(arg) for arg in args]))
        uart.write('\r\n')

    log_to_fn(log_to_uart_fn)


log_to_print()
