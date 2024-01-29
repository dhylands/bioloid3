#include <inttypes.h>
#include <stddef.h>

#define UART0_BASE 0x40034000

#define UARTCR 0x30
#define UARTCR_RXE (1 << 9)
#define UARTCR_TXE (1 << 8)

#define UARTFR  0x18
#define UARTFR_TXFE (1 << 7)
#define UARTFR_TXFF (1 << 5)
#define UARTFR_BUSY (1 << 3)

void write_packet(volatile uint32_t* base, uint8_t* buf, size_t len) {
    uint32_t cr = base[UARTCR / 4];
    cr |= UARTCR_RXE;
    cr &= ~UARTCR_TXE;
    base[UARTCR / 4] = cr;

    asm("nop");

    while (1) {
        uint32_t fr = base[UARTFR / 4];
        if ((fr & UARTFR_TXFF) == 0) {
            break;
        }
    }

    asm("nop");

    cr = base[UARTCR / 4];
    cr |= UARTCR_TXE;
    cr &= ~UARTCR_RXE;
    base[UARTCR / 4] = cr;
}