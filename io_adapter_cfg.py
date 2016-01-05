# Register layout for io_adapter.

NUM_ADCS        = 9
NUM_GPIOS       = 22

# Upper nibble is the port number, lower nibble is the pin number
# 0 = unconfigured, 1 = Port A, 2 = Port B, ...
# Pin number (0-15)
ADC_PIN         = 0x06

# Upper nibble is the port number, lower nibble is the pin number
# 0 = unconfigured, 1 = Port A, 2 = Port B, ...
# Pin number (0-15)
GPIO_PIN        = ADC_PIN + NUM_ADCS

GPIO_CFG        = GPIO_PIN + NUM_GPIOS
GPIO_CFG_DIR        = 0x01  # 1 = input, 0 = output
GPIO_CFG_PU         = 0x02  # 1 = pullup enabled, 0 = pullup disabled
GPIO_CFG_PD         = 0x04  # 1 = pulldown enabled, 0 = pulldown disabled
GPIO_CFG_OD         = 0x08  # 1 = open-drain enabled, 0 = push-pull

PERSISTENT_BYTES    = GPIO_CFG + NUM_GPIOS

# ADC_VALUE is an array of UINT16's
ADC_VALUE       = GPIO_CFG + NUM_GPIOS

GPIO_SET        = ADC_VALUE + (NUM_ADCS * 2)    # 32 bits - set to 1 to set a bit
GPIO_CLEAR      = GPIO_SET + 4                  # 32 bits - set to 1 to clear a bit
GPIO_ODR        = GPIO_CLEAR + 4                # 32 bits - output values for each bit
GPIO_IDR        = GPIO_ODR + 4                  # 32 bits - input values for each bit

