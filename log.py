"""Implements a simple logger abstraction that can allow data to be directed
   someplace other than stdout.

   Currently we can't redirecty sys.stdout on MicroPython which means that
   print always goes to USB, even if we don't want it to.
"""

def log(*args):
    """Make log call log_fn so that other modules can use:

       from log import log

       and then call log_to_xxx and have the changes take effect.
    """
    log_fn(args)

def log_to_print():
    global log_fn
    def log_fn(args):
        print(*args)

def log_to_file(file):
    global log_fn
    def log_fn(args):
        file.write(' '.join([str(arg) for arg in args]))
        file.write('\n')

def log_to_uart(uart):
    global log_fn
    def log_fn(args):
        uart.write(' '.join([str(arg) for arg in args]))
        uart.write('\r\n')

log_to_print()
