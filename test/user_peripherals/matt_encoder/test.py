# SPDX-FileCopyrightText: © 2025 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from encoder import Encoder

from tqv import TinyQV

PERIPHERAL_NUM = 16
REGISTER_DELAY = 100

@cocotb.test()
async def test_project(dut):
    dut._log.info("Start")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())


    # set to at least width of debounce shift register * debounce cycles
    clocks_per_phase = 600 
    encoder0 = Encoder(dut.clk, dut.ui_in[0], dut.ui_in[1], clocks_per_phase = clocks_per_phase, noise_cycles = clocks_per_phase / 8)
    encoder1 = Encoder(dut.clk, dut.ui_in[2], dut.ui_in[3], clocks_per_phase = clocks_per_phase, noise_cycles = clocks_per_phase / 8)
    encoder2 = Encoder(dut.clk, dut.ui_in[4], dut.ui_in[5], clocks_per_phase = clocks_per_phase, noise_cycles = clocks_per_phase / 8)
    encoder3 = Encoder(dut.clk, dut.ui_in[6], dut.ui_in[7], clocks_per_phase = clocks_per_phase, noise_cycles = clocks_per_phase / 8)

    # Interact with your design's registers through this TinyQV class.
    # This will allow the same test to be run when your design is integrated
    # with TinyQV - the implementation of this class will be replaces with a
    # different version that uses Risc-V instructions instead of the SPI 
    # interface to read and write the registers.
    tqv = TinyQV(dut, PERIPHERAL_NUM)

    # Reset, always start the test by resetting TinyQV
    await tqv.reset()

    dut._log.info("Test project behavior")

    # debounce strobe is 1 clock high every (debounce_cmp << 6) cycles.
    # default is 128, which is 1 strobe every 8192 cycles, which at 64MHz results in a 7kHz sampling rate on the encoders
    dut._log.info("check default debounce frequency")
    assert await tqv.read_reg(4) == 128

    # takes too long for test, so set to 1, or once sample per 64 cycles
    dut._log.info("update debounce frequency")
    await tqv.write_reg(4, 1)
    assert await tqv.read_reg(4) == 1

    # check encoder is at 0
    dut._log.info("Check all encoders are 0 at reset")
    assert await tqv.read_reg(0) == 0
    assert await tqv.read_reg(1) == 0
    assert await tqv.read_reg(2) == 0
    # assert await tqv.read_reg(3) == 0 encoder 3 will fail because uart shares the same pin

    # twist the encoder knob
    dut._log.info("checking encoder 0")
    for i in range(clocks_per_phase * 2 * 20):
        await encoder0.update(1)
    await ClockCycles(dut.clk, REGISTER_DELAY)
    assert await tqv.read_reg(0) == 20

    # twist the encoder knob
    dut._log.info("checking encoder 1")
    for i in range(clocks_per_phase * 2 * 30):
        await encoder1.update(1)
    await ClockCycles(dut.clk, REGISTER_DELAY)
    assert await tqv.read_reg(1) == 30

    # twist the encoder knob
    dut._log.info("checking encoder 2")
    for i in range(clocks_per_phase * 2 * 40):
        await encoder2.update(1)
    await ClockCycles(dut.clk, REGISTER_DELAY)
    assert await tqv.read_reg(2) == 40

    #twist the encoder knob
    dut._log.info("checking encoder 3")
    for i in range(clocks_per_phase * 2 * 50):
        await encoder3.update(1)
    await ClockCycles(dut.clk, REGISTER_DELAY)
    assert await tqv.read_reg(3) == 50
