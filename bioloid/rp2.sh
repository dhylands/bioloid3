#!/bin/bash

set -e

arm-none-eabi-gcc -mcpu=cortex-m0plus -mthumb -Os -c rp2.c -o rp2.o
arm-none-eabi-objdump --disassemble rp2.o
