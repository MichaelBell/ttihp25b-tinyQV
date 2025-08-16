# SPDX-FileCopyrightText: © 2025 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

from tqv import TinyQV

# When submitting your design, change this to 16 + the peripheral number
# in peripherals.v.  e.g. if your design is i_user_simple00, set this to 16.
# The peripheral number is not used by the test harness.
PERIPHERAL_NUM = 25


@cocotb.test()
async def test_project(dut):
    dut._log.info("Start")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")

    cocotb.start_soon(clock.start())

    BIT_CS = 3
    BIT_SD = 2
    BIT_SCK = 1
    BIT_DC = 4

    ADDR_PIXEL = 0
    ADDR_SPI = 1
    ADDR_DC_PRESC = 2
    ADDR_SEL = 8
    ADDR_STATUS = 8

    MODEL = False

    # Interact with your design's registers through this TinyQV class.
    # This will allow the same test to be run when your design is integrated
    # with TinyQV - the implementation of this class will be replaces with a
    # different version that uses Risc-V instructions instead of the SPI
    # interface to read and write the registers.
    tqv = TinyQV(dut, PERIPHERAL_NUM)

    # Reset, always start the test by resetting TinyQV
    await tqv.reset()

    dut._log.info("Waveforms behavior")

    if not MODEL:
        # DC, CS, prescaler (not asserted)
        await tqv.write_reg(ADDR_DC_PRESC, 0b1_0_1100)
        await ClockCycles(dut.clk, 100)
        assert dut.uo_out[BIT_CS].value == 1
        assert dut.uo_out[BIT_DC].value == 0

        await tqv.write_reg(ADDR_DC_PRESC, 0b0_1_1100)
        await ClockCycles(dut.clk, 100)
        assert dut.uo_out[BIT_CS].value == 0
        assert dut.uo_out[BIT_DC].value == 1

        await tqv.write_reg(ADDR_DC_PRESC, 0b1_1_1100)
        await ClockCycles(dut.clk, 100)

        # SPI tunnel, set CS manually
        await tqv.write_reg(ADDR_DC_PRESC, 0b0_1_0010)
        await ClockCycles(dut.clk, 100)
        await tqv.write_reg(ADDR_SPI, 0x51)
        await ClockCycles(dut.clk, 100)
        await tqv.write_reg(ADDR_SPI, 0x15)
        await ClockCycles(dut.clk, 100)
        await tqv.write_reg(ADDR_DC_PRESC, 0b0_1_0010)
        await ClockCycles(dut.clk, 100)

        # Select page
        await tqv.write_reg(ADDR_SEL, 0x0)
        await ClockCycles(dut.clk, 200)

        # read status
        assert await tqv.read_reg(ADDR_STATUS) == 1
        await ClockCycles(dut.clk, 100)

        # clock pixel
        await tqv.write_reg(ADDR_PIXEL, 0xF0)
        await ClockCycles(dut.clk, 1000)

        return

    # set cs low, go to command mode
    await tqv.write_reg(ADDR_DC_PRESC, 0b0_0_0010)

    await tqv.write_reg(ADDR_SPI, 0xD5)
    await ClockCycles(dut.clk, 20)
    await tqv.write_reg(ADDR_SPI, 0xF0)
    await ClockCycles(dut.clk, 20)
    await tqv.write_reg(ADDR_SPI, 0x8D)
    await ClockCycles(dut.clk, 20)
    await tqv.write_reg(ADDR_SPI, 0x14)
    await ClockCycles(dut.clk, 20)
    await tqv.write_reg(ADDR_SPI, 0xA1)
    await ClockCycles(dut.clk, 20)
    await tqv.write_reg(ADDR_SPI, 0xC8)
    await ClockCycles(dut.clk, 20)
    await tqv.write_reg(ADDR_SPI, 0x81)
    await ClockCycles(dut.clk, 20)
    await tqv.write_reg(ADDR_SPI, 0xCF)
    await ClockCycles(dut.clk, 20)
    await tqv.write_reg(ADDR_SPI, 0xD9)
    await ClockCycles(dut.clk, 20)
    await tqv.write_reg(ADDR_SPI, 0xF1)
    await ClockCycles(dut.clk, 20)
    await tqv.write_reg(ADDR_SPI, 0xAF)
    await ClockCycles(dut.clk, 20)
    await tqv.write_reg(ADDR_SPI, 0x10)
    await ClockCycles(dut.clk, 20)
    await tqv.write_reg(ADDR_SPI, 0x02)
    await ClockCycles(dut.clk, 20)

    await tqv.write_reg(ADDR_DC_PRESC, 0b1_1_1_0001)

    # Row 0: low freq, start low
    await tqv.write_reg(ADDR_SEL, 0)
    await ClockCycles(dut.clk, 1000)
    for _ in range(128 // 32):
        await tqv.write_reg(ADDR_PIXEL, 0x00)
        await ClockCycles(dut.clk, 500)
        await tqv.write_reg(ADDR_PIXEL, 0x00)
        await ClockCycles(dut.clk, 500)
        await tqv.write_reg(ADDR_PIXEL, 0xFF)
        await ClockCycles(dut.clk, 500)
        await tqv.write_reg(ADDR_PIXEL, 0xFF)
        await ClockCycles(dut.clk, 500)

    # Row 2: med freq, start high
    await tqv.write_reg(ADDR_SEL, 2)
    await ClockCycles(dut.clk, 1000)
    for _ in range(128 // 16):
        await tqv.write_reg(ADDR_PIXEL, 0x00)
        await ClockCycles(dut.clk, 500)
        await tqv.write_reg(ADDR_PIXEL, 0xFF)
        await ClockCycles(dut.clk, 500)

    # Set header on
    await tqv.write_reg(ADDR_DC_PRESC, 0b1_1_1_1_0001)

    # Row 1/3/7 low
    for r in [1,3,5,7]:
        await tqv.write_reg(ADDR_SEL, r)
        await ClockCycles(dut.clk, 1000)
        for _ in range(128 // 16):
            await tqv.write_reg(ADDR_PIXEL, 0x00)
            await ClockCycles(dut.clk, 500)
            #await tqv.write_reg(ADDR_PIXEL, 0b00110011)
            await tqv.write_reg(ADDR_PIXEL, 0x00)
            await ClockCycles(dut.clk, 500)

    # Row 0/2 rewrite without ground line
    await tqv.write_reg(ADDR_SEL, 0)
    await ClockCycles(dut.clk, 1000)
    for _ in range(128 // 32):
        await tqv.write_reg(ADDR_PIXEL, 0x00)
        await ClockCycles(dut.clk, 500)
        await tqv.write_reg(ADDR_PIXEL, 0x00)
        await ClockCycles(dut.clk, 500)
        await tqv.write_reg(ADDR_PIXEL, 0xFF)
        await ClockCycles(dut.clk, 500)
        await tqv.write_reg(ADDR_PIXEL, 0xFF)
        await ClockCycles(dut.clk, 500)

    # Row 2: med freq, start high
    await tqv.write_reg(ADDR_SEL, 2)
    await ClockCycles(dut.clk, 1000)
    for _ in range(128 // 16):
        await tqv.write_reg(ADDR_PIXEL, 0x00)
        await ClockCycles(dut.clk, 500)
        await tqv.write_reg(ADDR_PIXEL, 0xFF)
        await ClockCycles(dut.clk, 500)

    # Row 4: high freq, start low
    await tqv.write_reg(ADDR_SEL, 4)
    await ClockCycles(dut.clk, 1000)
    for i in range(128 // 8 - 1):
        await tqv.write_reg(ADDR_PIXEL, 0xF0)
        await ClockCycles(dut.clk, 500)

    # Row 6: alternating starting high
    await tqv.write_reg(ADDR_SEL, 6)
    await ClockCycles(dut.clk, 1000)
    for i in range(128 // 8 - 1):
        await tqv.write_reg(ADDR_PIXEL, 0b11001100)
        await ClockCycles(dut.clk, 500)

    for i in range(8):
        await tqv.write_reg(ADDR_SEL, i)
        await ClockCycles(dut.clk, 1000)

    await ClockCycles(dut.clk, 1000)
