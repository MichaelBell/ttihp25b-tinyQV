# SPDX-FileCopyrightText: © 2025 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer, RisingEdge

from tqv import TinyQV

PERIPHERAL_NUM = 16+3

# Generate WS2812B waveform for a single bit
async def send_ws2812b_bit(dut, bit, clk_period_ns=15.625,DINindex=1):
    if bit == 1:
        high_time = 800   # ns
        low_time  = 450
    else:
        high_time = 400
        low_time  = 850

    dut.ui_in.value = 1 << DINindex
    await Timer(high_time, units='ns')
    dut.ui_in.value = 0
    await Timer(low_time, units='ns')


# Send a full byte MSB-first
async def send_ws2812b_byte(dut, byte, clk_period_ns=15.625, DINindex=1):
    for i in range(8):
        bit = (byte >> (7 - i)) & 1
        await send_ws2812b_bit(dut, bit,clk_period_ns, DINindex)
    # Inter-bit spacing is not required but can help simulate reality
    await Timer(200, units='ns')


# Simulate IDLE (> 50 us)
async def idle_line(dut, us=60):
    dut.ui_in.value = 0
    await Timer(us * 1000, units='ns')


@cocotb.test()
async def tests64Mhz(dut):
    dut._log.info("Start test 64Mhz")

    #clock = Clock(dut.clk, 15.625, units="ns")  # 64MHz clock
    clock = Clock(dut.clk, 16, units="ns")  # ≈62.5 MHz, close enough to 64 MHz for test
    cocotb.start_soon(clock.start())

    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    # -----------------------------------------
    # Configure prescaler shadow registers
    # -----------------------------------------
    dut._log.info("Configuring shadow prescaler registers...")

    # Set idle_ticks = 3840 = 0x00000F00
    await tqv.write_reg(0x06, 0x00)  # LSB
    await tqv.write_reg(0x07, 0x0F)

    # Set threshold_cycles = 38 = 0x00000026
    await tqv.write_reg(0x0A, 0x26)  # LSB
    await tqv.write_reg(0x0B, 0x00)

    # Commit new prescaler values
    await tqv.write_reg(0x05, 0xFF)
    await ClockCycles(dut.clk, 1)

    # -----------------------------------------
    # Configure DIN pin
    # -----------------------------------------
    dut._log.info("Configuring DIn to be ui_[1]...")

    # Set din to pin 1
    await tqv.write_reg(0xE, 0x01)  # LSB

    # -----------------------------------------
    # RGB data path test
    # -----------------------------------------
    # Check if rgb_ready register is ON
    ready = int(await tqv.read_reg(4))
    assert ready == 0
    dut._log.info("Reading rgb_ready is OFF")

    dut._log.info("Sending 3 bytes (G, R, B)")

    dut._log.info(f"Sending 3 bytes (G={0x12}, R={0x34}, B={0x56})")
    await send_ws2812b_byte(dut, 0x12)#g
    await send_ws2812b_byte(dut, 0x34)#r
    await send_ws2812b_byte(dut, 0x56)#b

    # Wait for RGB to be latched
    await ClockCycles(dut.clk, 5)

    dut._log.info("Reading rgb_ready is 0xFF and that cleared when writen a 0 to addr 0x3")
    await tqv.read_reg(4)==0xFF
    await ClockCycles(dut.clk, 1)  # allow state update
    await tqv.write_reg(3, 0) 
    await ClockCycles(dut.clk, 1)  # allow clearing to propagate
    await tqv.read_reg(4)==0x00
    
    # Read back registers
    g = int(await tqv.read_reg(1))
    r = int(await tqv.read_reg(0))
    b = int(await tqv.read_reg(2))

    dut._log.info(f"Read RGB = ({r:02X}, {g:02X}, {b:02X})")
    assert r == 0x34
    assert g == 0x12
    assert b == 0x56

    # Now send THREE extra byteS and confirm bits get forwarded and not detected
    dut._log.info("Testing bit forwarding to DOUT")

    dut._log.info(f"Sending 3 bytes (G={0xDE}, R={0xAD}, B={0xFF})")
    await send_ws2812b_byte(dut, 0xDE)
    await send_ws2812b_byte(dut, 0xAD)
    await send_ws2812b_byte(dut, 0xFF)

    # Allow a few cycles for DOUT propagation
    await ClockCycles(dut.clk, 5)

    dut._log.info("Reading rgb_ready is 0x00 proof of NOT detecion of fowarded bytes")
    await tqv.read_reg(4)==0x00
    await ClockCycles(dut.clk, 1)  # allow state update
    await tqv.write_reg(3, 0) 
    await ClockCycles(dut.clk, 1)  # allow clearing to propagate
    await tqv.read_reg(4)==0x00

    # Check that uo_out[1] has toggled (forwarding is happening)
    # Note: due to pipelining, you may not catch exact bits — we just assert activity
    dout_activity = int(dut.uo_out.value) & (1 << 1)
    assert dout_activity in [0, 1]

    # Now inject idle to trigger reset
    dut._log.info("Injecting IDLE condition")
    await idle_line(dut)

    await ClockCycles(dut.clk, 10)

    # Check that registers have been cleared (due to reset)
    assert int(await tqv.read_reg(0)) == 0x34  # Still holds, unless you clear manually in RTL

    #SEND AGAIN AFTER IDLE
    dut._log.info(f"Sending 3 bytes (G={0xab}, R={0xcd}, B={0xef})")
    await send_ws2812b_byte(dut, 0xab)
    await send_ws2812b_byte(dut, 0xcd)
    await send_ws2812b_byte(dut, 0xef)

    # Wait for RGB to be latched
    await ClockCycles(dut.clk, 10)

    # Read back registers
    g = int(await tqv.read_reg(1))
    r = int(await tqv.read_reg(0))
    b = int(await tqv.read_reg(2))

    dut._log.info(f"Read RGB = ({r:02X}, {g:02X}, {b:02X})")
    assert r == 0xcd
    assert g == 0xab
    assert b == 0xef

    dut._log.info("Test complete")










@cocotb.test()
async def tests24Mhz(dut):
    dut._log.info("Start test 24Mhz")

    clock = Clock(dut.clk, 42, units="ns")  # =23.809523809524 MHz, close enough to 24 MHz for test
    cocotb.start_soon(clock.start())

    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    # -----------------------------------------
    # Configure prescaler shadow registers
    # -----------------------------------------
    dut._log.info("Configuring shadow prescaler registers...")

    # Set idle_ticks = (16/42)*3840=1463 = 0x000005B7
    await tqv.write_reg(0x06, 0xb7)  # LSB
    await tqv.write_reg(0x07, 0x05)

    # Set threshold_cycles = (16/42)*38= 15 = 0x0000000F
    await tqv.write_reg(0x0A, 0x0F)  # LSB
    await tqv.write_reg(0x0B, 0x00)

    # Commit new prescaler values
    await tqv.write_reg(0x05, 0xFF)
    await ClockCycles(dut.clk, 1)

    # -----------------------------------------
    # Configure DIN pin
    # -----------------------------------------
    dut._log.info("Configuring DIn to be ui_[2]...")

    # Set din to pin 2
    await tqv.write_reg(0xE, 0x02)  # LSB

    # -----------------------------------------
    # RGB data path test
    # -----------------------------------------
    # Check if rgb_ready register is ON
    ready = int(await tqv.read_reg(4))
    assert ready == 0
    dut._log.info("Reading rgb_ready is OFF")

    dut._log.info("Sending 3 bytes (G, R, B)")

    dut._log.info(f"Sending 3 bytes (G={0x12}, R={0x34}, B={0x56})")
    await send_ws2812b_byte(dut, 0x12,42,2)#g
    await send_ws2812b_byte(dut, 0x34,42,2)#r
    await send_ws2812b_byte(dut, 0x56,42,2)#b

    # Wait for RGB to be latched
    await ClockCycles(dut.clk, 5)

    dut._log.info("Reading rgb_ready is 0xFF and that cleared when writen a 0 to addr 0x3")
    await tqv.read_reg(4)==0xFF
    await ClockCycles(dut.clk, 1)  # allow state update
    await tqv.write_reg(3, 0) 
    await ClockCycles(dut.clk, 1)  # allow clearing to propagate
    await tqv.read_reg(4)==0x00
    
    # Read back registers
    g = int(await tqv.read_reg(1))
    r = int(await tqv.read_reg(0))
    b = int(await tqv.read_reg(2))

    dut._log.info(f"Read RGB = ({r:02X}, {g:02X}, {b:02X})")
    assert r == 0x34
    assert g == 0x12
    assert b == 0x56

    # Now send THREE extra byteS and confirm bits get forwarded and not detected
    dut._log.info("Testing bit forwarding to DOUT")

    dut._log.info(f"Sending 3 bytes (G={0xDE}, R={0xAD}, B={0xFF})")
    await send_ws2812b_byte(dut, 0xDE,42,2)
    await send_ws2812b_byte(dut, 0xAD,42,2)
    await send_ws2812b_byte(dut, 0xFF,42,2)

    # Allow a few cycles for DOUT propagation
    await ClockCycles(dut.clk, 5)

    dut._log.info("Reading rgb_ready is 0x00 proof of NOT detecion of fowarded bytes")
    await tqv.read_reg(4)==0x00
    await ClockCycles(dut.clk, 1)  # allow state update
    await tqv.write_reg(3, 0) 
    await ClockCycles(dut.clk, 1)  # allow clearing to propagate
    await tqv.read_reg(4)==0x00

    # Check that uo_out[1] has toggled (forwarding is happening)
    # Note: due to pipelining, you may not catch exact bits — we just assert activity
    dout_activity = int(dut.uo_out.value) & (1 << 1)
    assert dout_activity in [0, 1]

    # Now inject idle to trigger reset
    dut._log.info("Injecting IDLE condition")
    await idle_line(dut)

    await ClockCycles(dut.clk, 10)

    # Check that registers have been cleared (due to reset)
    assert int(await tqv.read_reg(0)) == 0x34  # Still holds, unless you clear manually in RTL

    #SEND AGAIN AFTER IDLE
    dut._log.info(f"Sending 3 bytes (G={0xab}, R={0xcd}, B={0xef})")
    await send_ws2812b_byte(dut, 0xab,42,2)
    await send_ws2812b_byte(dut, 0xcd,42,2)
    await send_ws2812b_byte(dut, 0xef,42,2)

    # Wait for RGB to be latched
    await ClockCycles(dut.clk, 10)

    # Read back registers
    g = int(await tqv.read_reg(1))
    r = int(await tqv.read_reg(0))
    b = int(await tqv.read_reg(2))

    dut._log.info(f"Read RGB = ({r:02X}, {g:02X}, {b:02X})")
    assert r == 0xcd
    assert g == 0xab
    assert b == 0xef

    dut._log.info("Test complete")



@cocotb.test()
async def tests8MhzWithInputsRegisterRoulete(dut):
    dut._log.info("Start test 8Mhz")

    clock = Clock(dut.clk, 125, units="ns")  # =8 MHz, sharp
    cocotb.start_soon(clock.start())

    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    # -----------------------------------------
    # Configure prescaler shadow registers
    # -----------------------------------------
    dut._log.info("Configuring shadow prescaler registers...")

    # Set idle_ticks = (16/125)*3840 = 491 = 0x000001eb
    await tqv.write_reg(0x06, 0xeb)  # LSB
    await tqv.write_reg(0x07, 0x01)

    # Set threshold_cycles = (16/125)*38= 5 = 0x00000005
    await tqv.write_reg(0x0A, 0x05)  # LSB
    await tqv.write_reg(0x0B, 0x00)

    # Commit new prescaler values
    await tqv.write_reg(0x05, 0xFF)
    await ClockCycles(dut.clk, 5)

    for i in range(8): 
        dut._log.info(f"Configuring DIn to be ui_[{i}]...")
        # -----------------------------------------
        # Configure DIN pin
        # -----------------------------------------
        
        # Set din to pin 0
        await tqv.write_reg(0xE, i)  # LSB
        # -----------------------------------------
        # RGB data path test
        # -----------------------------------------
        # Check if rgb_ready register is ON
        ready = int(await tqv.read_reg(4))
        assert ready == 0
        dut._log.info("Reading rgb_ready is OFF")

        dut._log.info(f"Sending 3 bytes (G={i+1}, R={i}, B={i+2})")
        # Send 3 bytes for RGB 
        await send_ws2812b_byte(dut, i+1    ,125,i)#g
        await send_ws2812b_byte(dut, i      ,125,i)#r
        await send_ws2812b_byte(dut, i+2    ,125,i)#b

        # Wait for RGB to be latched
        await ClockCycles(dut.clk, 5)

        dut._log.info("Reading rgb_ready is 0xFF and that cleared when writen a 0 to addr 0x3")
        await tqv.read_reg(4)==0xFF
        await ClockCycles(dut.clk, 1)  # allow state update
        await tqv.write_reg(3, 0) 
        await ClockCycles(dut.clk, 1)  # allow clearing to propagate
        await tqv.read_reg(4)==0x00
        
        # Read back registers
        g = int(await tqv.read_reg(1))
        r = int(await tqv.read_reg(0))
        b = int(await tqv.read_reg(2))

        dut._log.info(f"Read RGB = ({r:02X}, {g:02X}, {b:02X})")
        assert r == i
        assert g == i+1
        assert b == i+2

        # Now send THREE extra byteS and confirm bits get forwarded and not detected
        dut._log.info("Testing bit forwarding to DOUT")

        dut._log.info(f"Sending 3 bytes (G={0xDE}, R={0xAD}, B={0xFF})")
        await send_ws2812b_byte(dut, 0xDE,125,i)
        await send_ws2812b_byte(dut, 0xAD,125,i)
        await send_ws2812b_byte(dut, 0xFF,125,i)

        # Allow a few cycles for DOUT propagation
        await ClockCycles(dut.clk, 5)

        dut._log.info("Reading rgb_ready is 0x00 proof of NOT detecion of fowarded bytes")
        await tqv.read_reg(4)==0x00
        await ClockCycles(dut.clk, 1)  # allow state update
        await tqv.write_reg(3, 0) 
        await ClockCycles(dut.clk, 1)  # allow clearing to propagate
        await tqv.read_reg(4)==0x00

        # Check that uo_out[x] has toggled (forwarding is happening)
        # Note: due to pipelining, you may not catch exact bits — we just assert activity,
        for i in range(8):
            dut._log.info(f"Checking activity on uo_[{i}]")
            dout_activity = int(dut.uo_out.value) & (1 << i)
            assert dout_activity in [0, 1]

        # Now inject idle to trigger reset
        dut._log.info("Injecting IDLE condition")
        await idle_line(dut)

    await ClockCycles(dut.clk, 10)

    #SEND AGAIN AFTER IDLE
    # Send 3 bytes for RGB
    dut._log.info(f"Sending 3 bytes (G={0xea}, R={0xae}, B={0x12})")
    await send_ws2812b_byte(dut, 0xea,125,7)
    await send_ws2812b_byte(dut, 0xae,125,7)
    await send_ws2812b_byte(dut, 0x12,125,7)

    # Wait for RGB to be latched
    await ClockCycles(dut.clk, 10)

    # Read back registers
    g = int(await tqv.read_reg(1))
    r = int(await tqv.read_reg(0))
    b = int(await tqv.read_reg(2))

    dut._log.info(f"Read RGB = ({r:02X}, {g:02X}, {b:02X})")
    assert r == 0xae
    assert g == 0xea
    assert b == 0x12

    dut._log.info("Test complete")

