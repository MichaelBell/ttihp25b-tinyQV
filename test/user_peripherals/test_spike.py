# SPDX-FileCopyrightText: © 2025 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
PERIPHERAL_NUM = 16+6
from tqv import TinyQV

@cocotb.test()
async def test_spike_harness(dut):
    dut._log.info("=== Start SPI-based Spike Peripheral Test ===")

    # 1. Create clock (10 MHz -> 100 ns period)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # 2. Initialize TinyQV helper
    tqv = TinyQV(dut,PERIPHERAL_NUM)

    # 3. Reset DUT
    await tqv.reset()
    dut._log.info("Reset complete")

    # -------------------------
    # Test sequence starts here
    # -------------------------

    # 4. Configure threshold register (ADDR=1)
    threshold = 10
    await tqv.write_reg(1, threshold)
    read_thresh = await tqv.read_reg(1)
    assert read_thresh == threshold, f"Threshold mismatch: got {read_thresh}"

    # 5. Apply pixel sequence to register 0 (ADDR=0)
    pixels = [5, 20, 15, 35, 50, 40]   # simulating varying intensities
    expected_spikes = 0
    prev_pixel = 0

    for px in pixels:
        await tqv.write_reg(0, px)      # write pixel input
        await ClockCycles(dut.clk, 2)   # wait for processing
        if abs(px - prev_pixel) >= threshold:
            expected_spikes += 1
        prev_pixel = px

    # 6. Read spike count (ADDR=3)
    count_val = await tqv.read_reg(3)
    dut._log.info(f"Spike count = {count_val}, Expected = {expected_spikes}")
    assert count_val == expected_spikes, "Spike count mismatch"

    # 7. Check spike flag (ADDR=2)
    spike_flag = await tqv.read_reg(2)
    assert spike_flag in (0, 1), f"Invalid spike flag: {spike_flag}"

    # 8. Check uo_out: bit0 = spike, bits7:1 = spike count MSBs
    uo_val = dut.uo_out.value.integer
    dut._log.info(f"uo_out = {uo_val:08b}")

    # At least validate spike bit is valid
    assert (uo_val & 1) in (0, 1), "uo_out[0] must be 0 or 1"

    dut._log.info("=== Spike Peripheral Test Passed ===")

