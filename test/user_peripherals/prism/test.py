
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, FallingEdge, Edge

from tqv import TinyQV

PERIPHERAL_NUM = 8

'''
==============================================================
PRISM Downloadable Configuration

Input:    chroma_gpio24.sv
Config:   tinyqv.cfg
==============================================================
'''
chroma_gpio24 = [
   0x000003c0, 0x08000000, 
   0x000003c0, 0x08000000, 
   0x00000140, 0x08010010, 
   0x00000bc0, 0x0800b200, 
   0x00000140, 0x0801401d, 
   0x00000280, 0x0841601a, 
   0x000003c0, 0x08004000, 
   0x00000288, 0x00012010, 
]
chroma_gpio24_ctrlReg = 0x00000598

'''
==============================================================
PRISM Downloadable Configuration

Input:    chroma_spislave.sv
Config:   tinyqv.cfg
==============================================================
'''
chroma_spislave = [
   0x000003c0, 0x08000000, 
   0x00000380, 0x08010000, 
   0x00000141, 0x08012003, 
   0x000003f8, 0x0800a000, 
   0x00000140, 0x0801a01d, 
   0x00000380, 0x08010000, 
   0x00000282, 0x08016003, 
   0x00000041, 0x08012000, 
]
chroma_spislave_ctrlReg = 0x00002912

@cocotb.test()
async def test_project(dut):
    dut._log.info("Start")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Setup simulated external devices
    input_value = 0xA5A5A5  # whatever test value you want
    output_shift = 0
    output_value = 0
    input_shift = input_value
    spi_data = []
    chroma = ''
    spi_transfer = False
    rx_byte = 0

    async def simulate_74165():
        nonlocal input_shift
        val_str = dut.uo_out.value.binstr.replace('x', '0').replace('z', '0')
        prev_val = int(val_str, 2)
        while True:
            # Wait for rising edge of uo_out[7] (shift clock)
            await RisingEdge(dut.clk)
            if chroma != 'gpio24':
               continue;

            # Get uo_out as an integer safely ('x' -> 0)
            val_str = dut.uo_out.value.binstr.replace('x', '0').replace('z', '0')
            curr_val = int(val_str, 2)

            # Check for clear or clock
            if curr_val & 2 == 0:
                # Load new value
                input_shift = input_value
            elif ((prev_val ^ curr_val) & (1 << 7)) and (curr_val & (1 << 7)):
                # Shift left
                input_shift = (input_shift << 1) & 0xFFFFFF
            else:
               prev_val = curr_val
               continue
            prev_val = curr_val

            # Set ui_in[0] to MSB
            dut.ui_in[0].value = (input_shift >> 23) & 1

    async def simulate_74595():
        nonlocal output_shift, output_value
        val_str = dut.uo_out.value.binstr.replace('x', '0').replace('z', '0')
        prev_val = int(val_str, 2)

        while True:
            # Wait for either posedge uo_out[7] (shift clk) or posedge uo_out[2] (store)
            await RisingEdge(dut.clk)
            if chroma != 'gpio24':
               continue;

            val_str = dut.uo_out.value.binstr.replace('x', '0').replace('z', '0')
            curr_val = int(val_str, 2)
            if curr_val & 4 != 0:
                # On store, latch output
                output_value = output_shift
            elif ((prev_val ^ curr_val) & (1 << 7)) and (curr_val & (1 << 7)):
                # On shift, shift in from uo_out[3]
                bit = int(dut.uo_out[3].value)
                output_shift = ((output_shift << 1) | bit) & 0xFFFFFF
            prev_val = curr_val


    async def delay(clocks):
        for i in range(clocks):
            await RisingEdge(dut.clk)

    async def simulate_spimaster():
        nonlocal spi_data, chroma, spi_transfer, rx_byte
        val_str = dut.uo_out.value.binstr.replace('x', '0').replace('z', '0')
        prev_val = int(val_str, 2)
        baud = 16
        idx  = 0
        rx_byte = 0

        while True:
            # Wait for either posedge uo_out[7] (shift clk) or posedge uo_out[2] (store)
            await RisingEdge(dut.clk)
            if chroma != 'spislave':
               continue
            if not spi_transfer:
               continue

            # Get first bit of first byte
            next_byte = spi_data[idx]
            idx += 1

            # Set input bit
            bit = (next_byte >> 7) & 1
            next_byte = next_byte << 1
            dut.ui_in[2].value = bit

            # Drop chip select
            dut.ui_in[0].value = 0

            for b in range(8): 
                # Pulse SCLK high
                await delay(baud)
                dut.ui_in[1].value = 1

                # Read MISO line
                bit = dut.uo_out[2].value
                rx_byte = (rx_byte << 1) | bit

                # Drive SCLK low
                await delay(baud)
                dut.ui_in[1].value = 0

                # Set next MOSI bit
                bit = (next_byte >> 7) & 1
                next_byte = next_byte << 1
                dut.ui_in[2].value = bit

            # Raise chip select
            await delay(baud)
            dut.ui_in[0].value = 1

            # Clear spi_transfer so we don't send over and over
            spi_transfer = False;

    async def load_chroma(chroma, ctrl_reg):
        '''
           Loads the specified chroma to the PRISM State Information Table
        '''
        # First reset the PRISM
        await tqv.write_word_reg(0x00, 0x00000000)
        await delay(64)
        assert await tqv.read_word_reg(0x0) == 0x00000000

        # Now load the chroma
        for i in range(8):
          # Load MSB of the control word first
          await tqv.write_word_reg(0x14, chroma[i * 2])
        
          # Loading LSB initates the shift
          await tqv.write_word_reg(0x10, chroma[i * 2 +1])
        
        # Validate the shift operation succeeded
        assert await tqv.read_word_reg(0x14) == chroma[0]
        assert await tqv.read_word_reg(0x10) == chroma[1]
        
        # Now program the PRISM peripheral configuration registers
        await tqv.write_word_reg(0x0, ctrl_reg)
        assert await tqv.read_word_reg(0x0) == ctrl_reg
       
        # Now enable PRISM
        await tqv.write_word_reg(0x0, 0x40000000 | ctrl_reg)

    async def test_chroma_gpio24():
        nonlocal input_value, chroma

        await load_chroma(chroma_gpio24, chroma_gpio24_ctrlReg)
        
        # Put 24-bit OUTPUT data in the 24-bit Shift register
        await tqv.write_word_reg(0x20, 0x00F05077)
        
        # Set an input value in the testbench
        input_value = 0x00BEEF

        chroma = 'gpio24'

        # Set a breakpoint in the PRISM debugger
        await tqv.write_word_reg(0x04, 0x00000034)
        
        # Start a transfer
        dut._log.info(f"    Starting GPIO24 shift operation")
        await tqv.write_word_reg(0x18, 0x03000000)
        await tqv.write_word_reg(0x18, 0x02000000)

        # Delay a bit to give FSM time to break
        for i in range(40):
            await RisingEdge(dut.clk)

        dut._log.info(f"    Testing if PRISM halted at breakpoint")
        dbg_status = await tqv.read_word_reg(0x0C)
        assert (dbg_status & 3) == 3
        assert (dbg_status & 0x40) == 0x40

        # Issue a single step request
        dut._log.info(f"    Single stepping PRISM")
        await tqv.write_word_reg(0x04, 0x00000036)

        dut._log.info(f"    Testing if PRISM stepped ")
        dbg_status = await tqv.read_word_reg(0x0C)
        assert (dbg_status & 3) == 2

        # Clear the interrupt caused by halt
        await tqv.write_byte_reg(0x03, 0x000000C0)

        # Resume the execution
        await tqv.write_word_reg(0x04, 0x00000001)
        await tqv.write_word_reg(0x04, 0x00000000)

        for i in range(200):
            await RisingEdge(dut.clk)
        
        # See if we got the input value
        dut._log.info(f"    Testing input read value")
        assert await tqv.read_word_reg(0x24) == 0x0000BEEF
        dut._log.info(f"    Testing output store value")
        assert output_value == 0x00F05077

    async def test_chroma_spislave():
        nonlocal spi_data, chroma, spi_transfer

        # Reset PRISM
        await tqv.write_word_reg(0x00, 0x00000000)
        chroma = ''

        # Set CS high (ui_in[0])
        dut.ui_in[0].value = 1
        dut.ui_in[1].value = 0
        dut.ui_in[2].value = 0
        
        # Load the chroma
        await load_chroma(chroma_spislave, chroma_spislave_ctrlReg)
        
        # Put 24-bit OUTPUT data in the 24-bit Shift register
        spi_data = [0xF5]
        chroma = 'spislave'

        # Write a known byte to comm_data register
        await tqv.write_byte_reg(0x18, 0x67)
        
        # Start a transfer
        spi_transfer = True 

        # Wait for transfer to complete
        while spi_transfer == True:
            await RisingEdge(dut.clk)

        for i in range(200):
            await RisingEdge(dut.clk)

        # Read a byte from the FIFO
        dut._log.info(f"    Testing read byte from FIFO")
        assert await tqv.read_byte_reg(0x19) == 0xF5

        # Test if the interrupt was set
        dut._log.info(f"    Testing if Interrupt was set")
        assert await tqv.read_word_reg(0) & 0x80000000 != 0

    # Start the simulations
    cocotb.start_soon(simulate_74165())
    cocotb.start_soon(simulate_74595())
    cocotb.start_soon(simulate_spimaster())

    # Interact with your design's registers through this TinyQV class.
    # This will allow the same test to be run when your design is integrated
    # with TinyQV - the implementation of this class will be replaces with a
    # different version that uses Risc-V instructions instead of the SPI 
    # interface to read and write the registers.
    tqv = TinyQV(dut, PERIPHERAL_NUM)

    # Reset
    await tqv.reset()

    dut._log.info("Testing PRISM")

    # Write values to the count2_compare / count1_preload
    await tqv.write_word_reg(0x00, 0x40000000)
    await ClockCycles(dut.clk, 8)
    await tqv.write_word_reg(0x20, 0x0300FA12)
    await ClockCycles(dut.clk, 8)

    dut._log.info("Testing basic control and latch register access")
    assert await tqv.read_word_reg(0x20) == 0x0300FA12
    assert await tqv.read_word_reg(0x0) == 0x40000000

    await tqv.write_word_reg(0x00, 0x00000000)

    # Test register write and read back
    # Write a value to the config array 
    dut._log.info("Testing PRISM state information integrity")
    await tqv.write_word_reg(0x14, 0x00001010)
    await tqv.write_word_reg(0x10, 0x10101010)

    await tqv.write_word_reg(0x14, 0x00002020)
    await tqv.write_word_reg(0x10, 0x20202020)

    await tqv.write_word_reg(0x14, 0x00003030)
    await tqv.write_word_reg(0x10, 0x30303030)

    await tqv.write_word_reg(0x14, 0x00004040)
    await tqv.write_word_reg(0x10, 0x40404040)

    await tqv.write_word_reg(0x14, 0x00005050)
    await tqv.write_word_reg(0x10, 0x50505050)

    await tqv.write_word_reg(0x14, 0x00006060)
    await tqv.write_word_reg(0x10, 0x60606060)

    await tqv.write_word_reg(0x14, 0x00007070)
    await tqv.write_word_reg(0x10, 0x70707070)

    await tqv.write_word_reg(0x14, 0x00008080)
    await tqv.write_word_reg(0x10, 0x80808080)

    # Wait for two clock cycles to see the output values, because ui_in is synchronized over two clocks,
    # and a further clock is required for the output to propagate.
    await ClockCycles(dut.clk, 3)

    # 0x10101010 should be read back from register 8
    assert await tqv.read_word_reg(0x10) == 0x10101010

    # ===========================================================
    # Okay, now load up a real design and see if it does anything
    # This is the 24-Bit GPIO Chroma
    # ===========================================================
    dut._log.info("Testing gpio24 Chroma")
    await test_chroma_gpio24()
 
    dut._log.info("Testing spislave Chroma")
    await test_chroma_spislave()
    
