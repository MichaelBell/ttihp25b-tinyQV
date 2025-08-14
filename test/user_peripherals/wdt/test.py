# SPDX-FileCopyrightText: © 2025 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

from tqv import TinyQV

PERIPHERAL_NUM = 6
CLK_PERIOD_NS = 100  # 10 MHz test clock (instead of 64 MHz)

# The TAP magic number is used to reset the watchdog timer and prevent firing of an interrupt.
# It is defined in the peripheral's source code.
TAP_MAGIC = 0xABCD
TAP_INVALID = 0xFFFF
# Standard countdown of 300 cycles, used for testing where a write may take a little over
# 100 cycles, and a read a little under 100 cycles. Leaves time for writing the tap value.
STANDARD_COUNTDOWN = 0x0000012C
LARGE_COUNTDOWN = 0x12345678
WDT_ADDR = {
    "enable":     0x00,  # Write 1 to enable, 0 to disable (also clears interrupt)
    "start":      0x04,  # Write 1 to start timer (implicitly enables)
    "countdown":  0x08,  # R/W 8/16/32-bit countdown value
    "tap":        0x0C,  # Write 0xABCD to reset countdown and clear interrupt
    "status":     0x10,  # Read status register
}


def decode_wdt_status(status_word: int) -> dict:
    """
    Decode the WDT status register into named boolean flags.

    Bit layout:
      Bit 0: enabled
      Bit 1: started
      Bit 2: timeout_pending
      Bit 3: counter_active (counter != 0)
    """
    return {
        "enabled":         bool((status_word >> 0) & 1),
        "started":         bool((status_word >> 1) & 1),
        "timeout_pending": bool((status_word >> 2) & 1),
        "counter_active":  bool((status_word >> 3) & 1),
    }


@cocotb.test()
async def test_watchdog_interrupt_on_timeout(dut):
    """Basic test to check that the watchdog timer asserts an interrupt on timeout."""
    clock = Clock(dut.clk, CLK_PERIOD_NS, units="ns")
    cocotb.start_soon(clock.start())
    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    countdown_ticks = 10  # enough to count down in test environment

    # Set countdown value
    await tqv.write_word_reg(WDT_ADDR["countdown"], countdown_ticks)

    # Start the watchdog
    await tqv.write_word_reg(WDT_ADDR["start"], 1)

    # Wait for timeout (countdown_ticks + a few cycles)
    await ClockCycles(dut.clk, countdown_ticks + 3)

    assert await tqv.is_interrupt_asserted(), "Interrupt not asserted on timeout"


@cocotb.test()
async def test_watchdog_tap_prevents_timeout(dut):
    """Basic test to check that tapping the watchdog prevents an interrupt."""
    clock = Clock(dut.clk, CLK_PERIOD_NS, units="ns")
    cocotb.start_soon(clock.start())
    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    countdown_ticks = STANDARD_COUNTDOWN

    # Set countdown
    await tqv.write_word_reg(WDT_ADDR["countdown"], countdown_ticks)
    await tqv.write_word_reg(WDT_ADDR["start"], 1)

    # Wait until we have confirmed an interrupt has been asserted
    await ClockCycles(dut.clk, countdown_ticks)
    assert await tqv.is_interrupt_asserted(), "Interrupt not asserted on timeout"

    # Tap the watchdog to reset countdown and clear interrupt
    await tqv.write_word_reg(WDT_ADDR["tap"], TAP_MAGIC)

    # Wait again a few cycles and then check that the interrupt is not asserted
    await ClockCycles(dut.clk, countdown_ticks // 10)

    assert not await tqv.is_interrupt_asserted(), "Interrupt incorrectly asserted after tap"


@cocotb.test()
async def test_enable_does_not_clear_timeout(dut):
    """Writing 0 to enable register should NOT clear a pending timeout."""
    clock = Clock(dut.clk, CLK_PERIOD_NS, units="ns")
    cocotb.start_soon(clock.start())
    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    countdown_ticks = 10

    # Set countdown
    await tqv.write_word_reg(WDT_ADDR["countdown"], countdown_ticks)
    await tqv.write_word_reg(WDT_ADDR["start"], 1)

    # Wait until we have confirmed an interrupt has been asserted
    await ClockCycles(dut.clk, countdown_ticks)
    assert await tqv.is_interrupt_asserted(), "Interrupt not asserted on timeout"

    await tqv.write_word_reg(WDT_ADDR["enable"], 0)

    assert await tqv.is_interrupt_asserted(), "Interrupt cleared by enable write of zero"


@cocotb.test()
async def test_multiple_valid_taps_prevent_interrupt(dut):
    """Multiple correct taps should keep reloading the countdown and prevent timeout."""
    clock = Clock(dut.clk, CLK_PERIOD_NS, units="ns")
    cocotb.start_soon(clock.start())
    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    countdown_ticks = STANDARD_COUNTDOWN

    # Set countdown
    await tqv.write_word_reg(WDT_ADDR["countdown"], countdown_ticks)
    await tqv.write_word_reg(WDT_ADDR["start"], 1)

    # Tap the watchdog multiple times within countdown period.
    # The total cycles exceeds countdown_ticks, but the taps should prevent the interrupt.
    await ClockCycles(dut.clk, countdown_ticks // 2)
    await tqv.write_word_reg(WDT_ADDR["tap"], TAP_MAGIC)

    await ClockCycles(dut.clk, countdown_ticks // 2)
    await tqv.write_word_reg(WDT_ADDR["tap"], TAP_MAGIC)

    assert not await tqv.is_interrupt_asserted(), "Interrupt incorrectly asserted after valid taps"


@cocotb.test()
async def test_tap_with_wrong_value_ignored(dut):
    """Writing incorrect value to tap address should have no effect (timeout occurs)."""
    clock = Clock(dut.clk, CLK_PERIOD_NS, units="ns")
    cocotb.start_soon(clock.start())
    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    countdown_ticks = STANDARD_COUNTDOWN

    # Set countdown
    await tqv.write_word_reg(WDT_ADDR["countdown"], countdown_ticks)
    await tqv.write_word_reg(WDT_ADDR["start"], 1)

    # Wait until we have confirmed an interrupt has been asserted
    await ClockCycles(dut.clk, countdown_ticks)
    assert await tqv.is_interrupt_asserted(), "Interrupt not asserted on timeout"

    # Tap the watchdog with valid number, should *not* reset countdown and clear interrupt
    await tqv.write_word_reg(WDT_ADDR["tap"], TAP_INVALID)

    # Wait again a few cycles and then check that the interrupt is still asserted
    await ClockCycles(dut.clk, countdown_ticks // 10)

    assert await tqv.is_interrupt_asserted(), "Interrupt cleared by invalid tap"


@cocotb.test()
async def test_start_does_not_clear_interrupt(dut):
    """Writes to 'start' should not clear timeout."""
    clock = Clock(dut.clk, CLK_PERIOD_NS, units="ns")
    cocotb.start_soon(clock.start())
    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    countdown_ticks = 50

    # Set countdown
    await tqv.write_word_reg(WDT_ADDR["countdown"], countdown_ticks)
    await tqv.write_word_reg(WDT_ADDR["start"], 1)

    await ClockCycles(dut.clk, countdown_ticks)

    assert await tqv.is_interrupt_asserted(), "Interrupt not asserted on timeout"

    # Writing to start should reload the counter, but not clear any existing interrupt
    await tqv.write_word_reg(WDT_ADDR["start"], 1)

    assert await tqv.is_interrupt_asserted(), "Write to start incorrectly cleared interrupt"


@cocotb.test()
async def test_repeated_start_reloads_countdown(dut):
    """Multiple writes to 'start' should reload countdown."""
    clock = Clock(dut.clk, CLK_PERIOD_NS, units="ns")
    cocotb.start_soon(clock.start())
    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    # NOTE: The write_word_reg takes enough cycles that we need a long enough WDT cycle such that
    # we allow for about 100 cycles for the final read.
    countdown_ticks = 600

    # Set countdown
    await tqv.write_word_reg(WDT_ADDR["countdown"], countdown_ticks)
    await tqv.write_word_reg(WDT_ADDR["start"], 1)

    # Wait 1/4 of the countdown, write to start, wait the rest of the countdown time and check interrupt not asserted
    await ClockCycles(dut.clk, countdown_ticks // 3)
    await tqv.write_word_reg(WDT_ADDR["start"], 1)

    await ClockCycles(dut.clk, 2 * (countdown_ticks // 3))

    assert not await tqv.is_interrupt_asserted(), "Write to start did not reload countdown"


@cocotb.test()
async def test_countdown_value_readback(dut):
    """Read from countdown address should return last written value."""
    clock = Clock(dut.clk, CLK_PERIOD_NS, units="ns")
    cocotb.start_soon(clock.start())
    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    countdown_ticks = LARGE_COUNTDOWN

    await tqv.write_word_reg(WDT_ADDR["countdown"], countdown_ticks)
    readback = await tqv.read_word_reg(WDT_ADDR["countdown"])
    assert readback == countdown_ticks, f"Expected 0x{countdown_ticks:08X}, got 0x{readback:08X}"


@cocotb.test()
async def test_partial_write_8bit_zeros_upper_bits(dut):
    """8-bit write to countdown should zero upper 24 bits."""
    clock = Clock(dut.clk, CLK_PERIOD_NS, units="ns")
    cocotb.start_soon(clock.start())
    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    # Set to known large value first
    await tqv.write_word_reg(WDT_ADDR["countdown"], LARGE_COUNTDOWN)

    # Now write only the low 8 bits
    await tqv.write_byte_reg(WDT_ADDR["countdown"], 0x42)

    readback = await tqv.read_word_reg(WDT_ADDR["countdown"])
    assert readback == 0x00000042, f"Expected 0x00000042, got 0x{readback:08X}"


@cocotb.test()
async def test_partial_write_16bit_zeros_upper_bits(dut):
    """16-bit write to countdown should zero upper 16 bits."""
    clock = Clock(dut.clk, CLK_PERIOD_NS, units="ns")
    cocotb.start_soon(clock.start())
    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    # Set to known large value first
    await tqv.write_word_reg(WDT_ADDR["countdown"], LARGE_COUNTDOWN)

    # Now write only the low 16 bits
    await tqv.write_hword_reg(WDT_ADDR["countdown"], 0xFFFF)

    readback = await tqv.read_word_reg(WDT_ADDR["countdown"])
    assert readback == 0x0000FFFF, f"Expected 0x0000BEEF, got 0x{readback:08X}"


@cocotb.test()
async def test_start_without_countdown_value(dut):
    """Starting the watchdog without setting countdown should not start the timer."""
    clock = Clock(dut.clk, CLK_PERIOD_NS, units="ns")
    cocotb.start_soon(clock.start())
    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    # Do not set countdown, just issue start
    await tqv.write_word_reg(WDT_ADDR["start"], 1)

    # Read status register
    status_word = await tqv.read_word_reg(WDT_ADDR["status"])
    status = decode_wdt_status(status_word)

    assert not status["enabled"], "Status: expected enabled=0 without countdown"
    assert not status["started"], "Status: expected started=0 without countdown"
    assert not status["timeout_pending"], "Status: expected timeout_pending=0"
    assert not status["counter_active"], "Status: expected counter=0"


@cocotb.test()
async def test_status_after_start(dut):
    """Status register reflects enabled=1, started=1, counter!=0 before timeout."""
    clock = Clock(dut.clk, CLK_PERIOD_NS, units="ns")
    cocotb.start_soon(clock.start())
    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    countdown_ticks = 200

    # Set countdown and start the watchdog
    await tqv.write_word_reg(WDT_ADDR["countdown"], countdown_ticks)
    await tqv.write_word_reg(WDT_ADDR["start"], 1)

    # Read the status register
    status_word = await tqv.read_word_reg(WDT_ADDR["status"])
    status = decode_wdt_status(status_word)

    assert status["enabled"], "Status: expected enabled=1"
    assert status["started"], "Status: expected started=1"
    assert not status["timeout_pending"], "Status: expected timeout_pending=0"
    assert status["counter_active"], "Status: expected counter!=0"


@cocotb.test()
async def test_status_after_timeout(dut):
    """Status register reflects timeout_pending=1 after timer expiry."""
    clock = Clock(dut.clk, CLK_PERIOD_NS, units="ns")
    cocotb.start_soon(clock.start())
    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    countdown_ticks = 10

    # Set countdown and start the watchdog
    await tqv.write_word_reg(WDT_ADDR["countdown"], countdown_ticks)
    await tqv.write_word_reg(WDT_ADDR["start"], 1)

    await ClockCycles(dut.clk, countdown_ticks)
    assert await tqv.is_interrupt_asserted(), "Interrupt not asserted on timeout"

    # Read the status register
    status_word = await tqv.read_word_reg(WDT_ADDR["status"])
    status = decode_wdt_status(status_word)

    assert status["enabled"], "Status: expected enabled=1 after timeout"
    assert status["started"], "Status: expected started=1 after timeout"
    assert status["timeout_pending"], "Status: expected timeout_pending=1 after timeout"
    assert not status["counter_active"], "Status: expected counter=0 after timeout"


@cocotb.test()
async def test_disable_before_start_has_no_effect(dut):
    """Disabling before watchdog is started should have no effect and not assert interrupt."""
    clock = Clock(dut.clk, CLK_PERIOD_NS, units="ns")
    cocotb.start_soon(clock.start())
    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    # Write 0 to disable (has no effect before start)
    await tqv.write_word_reg(WDT_ADDR["enable"], 0)

    # Wait a few cycles and confirm no spurious interrupt
    await ClockCycles(dut.clk, 10)
    assert not await tqv.is_interrupt_asserted(), "Unexpected interrupt before WDT was started"
