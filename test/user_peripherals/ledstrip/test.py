# SPDX-FileCopyrightText: © 2025 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer, Edge
from cocotb.utils import get_sim_time
import random

from tqv import TinyQV

PERIPHERAL_NUM = 18

# Test sending single pixels
@cocotb.test()
async def test_single_pixel1(dut):
    dut._log.info("Start")

    # Set the clock period to 15 ns (~66.7 MHz)
    clock = Clock(dut.clk, 15, units="ns")
    cocotb.start_soon(clock.start())

    led = dut.uo_out[1]

    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    dut._log.info("PUSH 1 PIXEL WITH DEFAULT COLOR (R=32, G=0, B=0)")

    # wait for peripheral to be ready
    dut._log.info("Waiting for peripheral to be ready")
    await wait_peripheral_ready(tqv)

    # push 1 pixel with the color set above
    dut._log.info("Writing PUSH register")
    f = cocotb.start_soon(tqv.write_reg(0, 0x01))  # we need to use a coroutine
    assert led.value == 0
    # parse the the LED strip signal
    bitseq = await get_GRB(dut, led)
    await f  # wait for the coroutine to finish

    dut._log.info(f"Read back {len(bitseq)} bits: {bitseq}")
    assert bitseq == [  0, 0, 0, 0, 0, 0, 0, 0,   # G: 0
                        0, 0, 1, 0, 0, 0, 0, 0,   # R: 32
                        0, 0, 0, 0, 0, 0, 0, 0 ]  # B: 0


# Test sending single pixels
@cocotb.test()
async def test_single_pixel2(dut):
    dut._log.info("Start")

    # Set the clock period to 15 ns (~66.7 MHz)
    clock = Clock(dut.clk, 15, units="ns")
    cocotb.start_soon(clock.start())
   
    led = dut.uo_out[1]

    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    dut._log.info("PUSH 1 PIXEL WITH COLOR (R=15, G=255, B=128)")

    await tqv.write_reg(1, 15)
    await tqv.write_reg(2, 255)
    await tqv.write_reg(3, 128)

    # wait for peripheral to be ready
    dut._log.info("Waiting for peripheral to be ready")
    await wait_peripheral_ready(tqv)

    # push 1 pixel with the color set above
    dut._log.info("Writing PUSH register")
    f = cocotb.start_soon(tqv.write_reg(0, 0x01))  # we need to use a coroutine
    assert led.value == 0
    # parse the the LED strip signal
    bitseq = await get_GRB(dut, led)
    await f  # wait for the coroutine to finish

    dut._log.info(f"Read back {len(bitseq)} bits: {bitseq}")
    assert bitseq == [  1, 1, 1, 1, 1, 1, 1, 1,  # G: 255
                        0, 0, 0, 0, 1, 1, 1, 1,  # R: 15
                        1, 0, 0, 0, 0, 0, 0, 0 ]  # B: 128


    dut._log.info("PUSH 1 BLACK PIXEL")

    # wait for peripheral to be ready
    dut._log.info("Waiting for peripheral to be ready")
    await wait_peripheral_ready(tqv)

    # push (0,0,0) pixel
    dut._log.info("Writing PUSH register")
    f = cocotb.start_soon(tqv.write_reg(0, 0x40 | 0x01))
    assert led.value == 0
    bitseq = await get_GRB(dut, led)
    await f

    dut._log.info(f"Read back {len(bitseq)} bits: {bitseq}")
    assert bitseq == [0] * 24


# Test sending a sequence of pixels with random colors and random strip reset flag
@cocotb.test()
async def test_multiple_pixels(dut):
    NUM_RANDOM_PIXELS = 16
    NUM_PIXELS = 11
    NUM_BLACK_PIXELS = 7
    PROB_RESET = 0.5  # Probability of strip reset for each pixel

    dut._log.info("Start")
    random.seed(42)

    # Set the clock period to 15 ns (~66.7 MHz)
    clock = Clock(dut.clk, 15, units="ns")
    cocotb.start_soon(clock.start())
   
    led = dut.uo_out[1]

    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    dut._log.info("PUSH MULTIPLE PIXELS WITH RANDOMIZED COLORS AND RANDOM STRIP RESET FLAG")

    await wait_peripheral_ready(tqv)

    for count in range(NUM_RANDOM_PIXELS):
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        strip_reset = int(random.random() > PROB_RESET)

        dut._log.info(f"Loading color {color}, reset={strip_reset}")
        await tqv.write_reg(1, color[0])  # R
        await tqv.write_reg(2, color[1])  # G
        await tqv.write_reg(3, color[2])  # B

        dut._log.info(f"Sending pixel #{count}")
        f = cocotb.start_soon(tqv.write_reg(0, 0x01 | (strip_reset << 7)))
        assert led.value == 0
        bitseq = await get_GRB(dut, led)
        await f

        # Check that the read back color matches the one we set
        dut._log.info(f"Read back {len(bitseq)} bits: {bitseq}")
        assert bitseq == list(map(int, f'{color[1]:08b}')) + list(map(int, f'{color[0]:08b}')) + list(map(int, f'{color[2]:08b}'))

        # Check that the strip reset flag results in the expected delay
        # (conservatively, over 300 us for strip reset and under 10 us for no reset)
        delay = await time_peripheral_ready(tqv)
        dut._log.info(f"Peripheral ready after {delay:.2f} us")
        assert (strip_reset and delay > 300) or (not strip_reset and delay < 10)

    # send multiple pixels with final strip reset
    dut._log.info("PUSH MULTIPLE PIXELS AND THEN RESET STRIP")

    await wait_peripheral_ready(tqv)

    await tqv.write_reg(1, 15)   # R
    await tqv.write_reg(2, 255)  # G
    await tqv.write_reg(3, 128)  # B

    dut._log.info(f"Sending {NUM_PIXELS} pixels with strip reset")
    f = cocotb.start_soon(tqv.write_reg(0, 0x80 | NUM_PIXELS))
    assert led.value == 0
    for count in range(NUM_PIXELS):
        bitseq = await get_GRB(dut, led)
        dut._log.info(f"Read back {len(bitseq)} bits: {bitseq}")
        assert bitseq == [  1, 1, 1, 1, 1, 1, 1, 1,   # G: 255
                            0, 0, 0, 0, 1, 1, 1, 1,   # R: 15
                            1, 0, 0, 0, 0, 0, 0, 0 ]  # B: 128
    await f

    delay = await time_peripheral_ready(tqv)
    dut._log.info(f"Peripheral ready after {delay:0.2f} us")
    assert delay > 300

    # send multiple black pixels with final strip reset
    dut._log.info(f"PUSH {NUM_BLACK_PIXELS} BLACK PIXELS AND THEN RESET STRIP")

    await wait_peripheral_ready(tqv)
   
    # send multiple black pixels with final strip reset
    dut._log.info(f"Sending {NUM_BLACK_PIXELS} black pixels with final strip reset")
    f = cocotb.start_soon(tqv.write_reg(0, 0x80 | 0x40 | NUM_BLACK_PIXELS))
    assert led.value == 0
    for count in range(NUM_BLACK_PIXELS):
        bitseq = await get_GRB(dut, led)
        dut._log.info(f"Read back {len(bitseq)} bits: {bitseq}")
        assert bitseq == [0] * 24
    await f
  
    delay = await time_peripheral_ready(tqv)
    dut._log.info(f"Peripheral ready after {delay:0.2f} us")
    assert delay > 300


# Test character generator
@cocotb.test()
async def test_character_generator(dut):
    dut._log.info("Start")

    # Set the clock period to 15 ns (~66.7 MHz)
    clock = Clock(dut.clk, 15, units="ns")
    cocotb.start_soon(clock.start())
   
    led = dut.uo_out[1]

    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    dut._log.info("PUSH A PRINTABLE ASCII CHARACTER")

    await wait_peripheral_ready(tqv)

    await tqv.write_reg(1, 255) # R
    await tqv.write_reg(2, 0)   # G
    await tqv.write_reg(3, 0)   # B

    # send ASCI character 'A' (65)
    dut._log.info(f"Push 7x5 pixel matrix for ASCII 65, do not reset strip")
    f = cocotb.start_soon(tqv.write_reg(4, 65))
    assert led.value == 0
    c = await get_char(dut, led)
    await f
    assert c.bitmap == "00100010101000110001111111000110001"  # from character ROM
 
    delay = await time_peripheral_ready(tqv)
    dut._log.info(f"Peripheral ready after {delay:0.2f} us")

    dut._log.info("PUSH A NON-PRINTABLE ASCII CHARACTER")

    await wait_peripheral_ready(tqv)

    # request non-printable ASCI character 10
    dut._log.info(f"Push 7x5 pixel matrix for ASCII 10, then reset strip")
    f = cocotb.start_soon(tqv.write_reg(4, 10 | 0x80))
    assert led.value == 0
    c = await get_char(dut, led)
    await f
    assert c.bitmap == "11111111111111111111111111111111111"  # filled matrxi for non-printable characters
 
    delay = await time_peripheral_ready(tqv)
    dut._log.info(f"Peripheral ready after {delay:0.2f} us")
    assert delay > 300


async def wait_peripheral_ready(tqv):
  while await tqv.read_reg(0) == 0:
        await ClockCycles(tqv.dut.clk, 1000)

async def time_peripheral_ready(tqv):
    t1 = get_sim_time('ns')
    while await tqv.read_reg(0) == 0:
        await Timer(1, units="us")
    t2 = get_sim_time('ns')
    return (t2 - t1) / 1000.0

# read 24 color bits (G / R / B) parsing WA2812B signal
async def get_GRB(dut, led):
    bitseq = []

    for i in range(24):
        while led.value == 0:
            await Edge(dut.uo_out)
        t1 = get_sim_time('ns')

        while led.value == 1:
            await Edge(dut.uo_out)
        t2 = get_sim_time('ns')

        pulse_ns = t2-t1
        # check pulse duration
        assert pulse_ns > 300
        assert pulse_ns < 900

        # decode bit
        bitseq.append( 1 if (pulse_ns > 625) else 0 )

    return bitseq

# class to hold character's bitmap & color
class Char():
    def __init__(self, bitmap, color):
        self.bitmap = bitmap
        self.color = color

# read 5x7 character matrix
async def get_char(dut, led):
    cseq = []
    color_set = set()
    for count in range(35):
        bitseq = await get_GRB(dut, led)
        if sum(bitseq):
            cseq.append(1)
            color_set.add("".join([str(x) for x in bitseq]))
        else:
            cseq.append(0)
        dut._log.info(f"{count}: {bitseq}")

    # same color for all non-black pixels in a given character
    assert len(color_set) <= 1

    # print character
    print()
    for i in range(7):
        linestring = "".join(["O" if x==1 else "." for x in cseq[i*5:(i+1)*5]])
        dut._log.info(linestring)
    print()

    bitmap = "".join([str(x) for x in cseq])
    color = list(color_set)[0]

    return Char(bitmap, color)
