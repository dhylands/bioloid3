# Register layout for io_adapter.

MAX_ADCS        = 0x10
MAX_GPIOS       = 0x11

# Starting at offset 0x20 are 16 x 1 byte entries
ADC_PIN         = 0x20  # Upper nibble is the port number, lower nibble is the pin number
                        # 0 = unconfigured, 1 = Port A, 2 = Port B, ...
                        # Pin number (0-15)

# Starting at offset 0x30 are 32 x 1 byte entries.
GPIO_PIN        = 0x30  # Upper nibble is the port number, lower nibble is the pin number
                        # 0 = unconfigured, 1 = Port A, 2 = PortB, ...
                        # Pin number (0-15)

# Starting at offset 0x50 are 32 x 1 byte entries.
GPIO_CFG        = 0x50  # 8 bits per GPIO. 
GPIO_CFG_DIR        = 0x01  # 1 = input, 0 = output
GPIO_CFG_PU         = 0x02  # 1 = pullup enabled, 0 = pullup disabled
GPIO_CFG_PD         = 0x04  # 1 = pulldown enabled, 0 = pulldown disabled
GPIO_CFG_OD         = 0x08  # 1 = open-drain enabled, 0 = push-pull

# GPIO_PIN and GPIO_CFG repeat 32 times

# 0x70 to 0x7F are reserved for future use.

PERSISTENT_BYTES    = 0x80

ADC_VALUE       = 0x80  # 16 x 2-byted entries

GPIO_SET        = 0xB0  # 32 bits - set to 1 to set a bit
GPIO_CLEAR      = 0xB4  # 32 bits - set to 1 to clear a bit
GPIO_ODR        = 0xB8  # 32 bits - output values for each bit
GPIO_IDR        = 0xBC  # 32 bits - input values for each bit

GPIO_VALUE      = 0xC0  # 32 1 byte entries
