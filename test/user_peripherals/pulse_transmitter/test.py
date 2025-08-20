# SPDX-FileCopyrightText: © 2025 HX2003
# SPDX-License-Identifier: Apache-2.0

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, FallingEdge, Edge

from tqv import TinyQV

# When submitting your design, change this to the peripheral number
# in peripherals.v.  e.g. if your design is i_user_peri05, set this to 5.
# The peripheral number is not used by the test harness.
PERIPHERAL_NUM = 11

MAX_DURATION = 255 # max duration you can put in the duration field

MAX_PROGRAM_1BPE_LEN = 256 # must be power of 2 as this also affects the rollover / wrapping
MAX_PROGRAM_2BPE_LEN = MAX_PROGRAM_1BPE_LEN >> 1 # divide by 2

# Note that with 2bpe mode,
# you need to multiply program_start_index, program_end_index, program_end_loopback_index by 2

MAX_PROGRAM_LOOP_LEN = 256 # the actual value set is MAX_PROGRAM_LOOP_LEN - 1
MAX_TEST_INFINITE_LOOP_LEN = 100

class Device:
    def __init__(self, dut):
        self.dut = dut
        self.reset_config()
    
    async def init(self):
        # We target the clock period to 15.625 ns (64 MHz)
        clock = Clock(self.dut.clk, 15, units="ns")  # test at 66 MHz, close enough to 64MHz
        cocotb.start_soon(clock.start())

        # Interact with your design's registers through this TinyQV class.
        # This will allow the same test to be run when your design is integrated
        # with TinyQV - the implementation of this class will be replaces with a
        # different version that uses Risc-V instructions instead of the SPI test
        # harness interface to read and write the registers.
        self.tqv = TinyQV(self.dut, PERIPHERAL_NUM)

        # Reset
        await self.tqv.reset()
         
    # only sets the member variables, does not actually write to the device
    def reset_config(self):
        self._clear_timer_interrupt = 0
        self._clear_program_loop_interrupt = 0
        self._clear_program_end_interrupt = 0
        self._clear_program_counter_mid_interrupt = 0
        self._start_program = 0
        self._stop_program = 0

        self.config_timer_interrupt_en = 0
        self.config_loop_interrupt_en = 0
        self.config_program_end_interrupt_en = 0
        self.config_program_counter_mid_interrupt_en = 0
        self.config_loop_forever = 0
        self.config_idle_level = 0
        self.config_invert_output = 0
        self.config_carrier_en = 0
        self.config_downcount = 0
        self.config_use_2bpe = 0
        self.config_low_symbol_0 = 0
        self.config_low_symbol_1 = 0
        self.config_high_symbol_0 = 0
        self.config_high_symbol_1 = 0

        self.config_program_start_index = 0
        self.config_program_end_index = 0
        self.config_program_loopback_index = 0
        self.config_program_loop_count = 0
        
        self.config_main_low_duration_a = 0
        self.config_main_low_duration_b = 0
        self.config_main_high_duration_a = 0
        self.config_main_high_duration_b = 0
        
        self.config_auxillary_mask = 0
        self.config_auxillary_duration_a = 0
        self.config_auxillary_duration_b = 0
        self.config_auxillary_prescaler = 0
        self.config_main_prescaler = 0

        self.config_carrier_duration = 0
         

    async def write8_reg_0(self):
        reg0 = self._gen_reg_0()
        await self.tqv.write_byte_reg(0, reg0 & 0xFF)

    async def write32_reg_0(self):
        reg0 = self._gen_reg_0()
        await self.tqv.write_word_reg(0, reg0)
    
    def _gen_reg_0(self):
        return self._clear_timer_interrupt \
            | (self._clear_program_loop_interrupt << 1) \
            | (self._clear_program_end_interrupt << 2) \
            | (self._clear_program_counter_mid_interrupt << 3) \
            | (self._start_program << 4) \
            | (self._stop_program << 5) \
            | (self.config_timer_interrupt_en << 8) \
            | (self.config_loop_interrupt_en << 9) \
            | (self.config_program_end_interrupt_en << 10) \
            | (self.config_program_counter_mid_interrupt_en << 11) \
            | (self.config_loop_forever << 12) \
            | (self.config_idle_level << 13) \
            | (self.config_invert_output << 14) \
            | (self.config_carrier_en << 15) \
            | (self.config_downcount << 16) \
            | (self.config_use_2bpe << 17) \
            | (self.config_low_symbol_0 << 18) \
            | (self.config_low_symbol_1 << 20) \
            | (self.config_high_symbol_0 << 22) \
            | (self.config_high_symbol_1 << 24) \
            
    async def write32_reg_1(self):
        reg1 = self.config_program_start_index \
            | (self.config_program_end_index << 8) \
            | (self.config_program_loopback_index << 16) \
            | (self.config_program_loop_count << 24) \
        
        await self.tqv.write_word_reg(4, reg1)

    async def write32_reg_2(self):
        reg2 = (self.config_main_high_duration_b << 24) | (self.config_main_high_duration_a << 16) | (self.config_main_low_duration_b << 8) | self.config_main_low_duration_a
        await self.tqv.write_word_reg(8, reg2)
    
    async def write32_reg_3(self):
        reg3 = self.config_auxillary_mask \
            | (self.config_auxillary_duration_a << 8) \
            | (self.config_auxillary_duration_b << 16) \
            | (self.config_auxillary_prescaler << 24) \
            | (self.config_main_prescaler << 28)
        
        await self.tqv.write_word_reg(12, reg3)

    async def write32_reg_4(self):
        reg4 = self.config_carrier_duration
        
        await self.tqv.write_word_reg(16, reg4)

    """ Start the program """
    async def start_program(self):
        self._start_program = 1
        await self.write8_reg_0()
        self._start_program = 0

    """ Stop the program """
    async def stop_program(self):
        self._stop_program = 1
        await self.write8_reg_0()
        self._stop_program = 0

    """ Clear the desired interrupts using 8 bit write """
    async def clear_interrupts(self, clear_timer_interrupt = 1, clear_program_loop_interrupt = 1, clear_program_end_interrupt=1, clear_program_counter_mid_interrupt=1):
        self._clear_timer_interrupt = clear_timer_interrupt
        self._clear_program_loop_interrupt = clear_program_loop_interrupt
        self._clear_program_end_interrupt = clear_program_end_interrupt
        self._clear_program_counter_mid_interrupt = clear_program_counter_mid_interrupt
        self._start_program = 0
        self._stop_program = 0

        await self.write8_reg_0()

        self._clear_timer_interrupt = 0
        self._clear_program_loop_interrupt = 0
        self._clear_program_end_interrupt = 0
        self._clear_program_counter_mid_interrupt = 0
        self._start_program = 0
        self._stop_program = 0

    """ Clear the desired interrupts using 8 bit write """
    async def clear_interrupts_using32(self, clear_timer_interrupt = 1, clear_program_loop_interrupt = 1, clear_program_end_interrupt=1, clear_program_counter_mid_interrupt=1):
        self._clear_timer_interrupt = clear_timer_interrupt
        self._clear_program_loop_interrupt = clear_program_loop_interrupt
        self._clear_program_end_interrupt = clear_program_end_interrupt
        self._clear_program_counter_mid_interrupt = clear_program_counter_mid_interrupt
        self._start_program = 0
        self._stop = 0

        await self.write32_reg_0()

        self._clear_timer_interrupt = 0
        self._clear_program_loop_interrupt = 0
        self._clear_program_end_interrupt = 0
        self._clear_program_counter_mid_interrupt = 0
        self._start_program = 0
        self._stop_program = 0

    # for a symbol tuple[int, int], 
    # the first value is the duration selector
    # the second value is the transmit level
    async def write_program_2bpe(self, program: list[tuple[int, int]]):
        assert self.config_use_2bpe

        # We did not check if the program is currently running, 
        # writing while program is running may have undefined behaviour

        await self.write32_reg_0()
        await self.write32_reg_1()
        await self.write32_reg_2()
        await self.write32_reg_3()
        await self.write32_reg_4()

        word = 0
        count = 0
        i = 0
        
        for symbol_duration_selector, symbol_transmit_level in program:
            symbol_data = (symbol_transmit_level << 1 ) | symbol_duration_selector

            word |= symbol_data << (i * 2)
            i += 1

            if i == 16:
                await self.tqv.write_word_reg(0b100000 | count, word)
                word = 0
                i = 0
                count += 4

        # Write the remaining bits
        if i > 0:
            await self.tqv.write_word_reg(0b100000 | count, word)

 
    async def write_program_1bpe(self, program: list[int]):
        assert not self.config_use_2bpe

        # We did not check if the program is currently running, 
        # writing while program is running may have undefined behaviour

        await self.write32_reg_0()
        await self.write32_reg_1()
        await self.write32_reg_2()
        await self.write32_reg_3()
        await self.write32_reg_4()

        word = 0
        count = 0
        i = 0
        
        for single_bit_value in program:
            word |= single_bit_value << i 
            i += 1

            if i == 32:
                await self.tqv.write_word_reg(0b100000 | count, word)
                word = 0
                i = 0
                count += 4

        # Write the remaining bits
        if i > 0:
            await self.tqv.write_word_reg(0b100000 | count, word)
    
    def _get_expected_from_symbol(self, symbol: int, use_auxillary: bool) -> dict:
        """
        Obtain the expected total duration and transmit level for a given 2 bit symbol.

        Args:
            symbol (int): The input 2 bit symbol
            use_auxillary (bool): Whether to use the auxillary prescaler/duration

        Returns:
            dict:
                - 'duration' (int): The expected total duration associated with the symbol.
                - 'output' (int): The expected output level associated with the symbol.
        """
        symbol_duration_selector = symbol & 0b01
        symbol_transmit_level = (symbol & 0b10) >> 1

        if use_auxillary:
            prescaler = self.config_auxillary_prescaler
            if(symbol_duration_selector == 0):
                duration = self.config_auxillary_duration_a
            else:
                duration = self.config_auxillary_duration_b
        else:
            prescaler = self.config_main_prescaler
            match (symbol):
                case 0: duration = self.config_main_low_duration_a
                case 1: duration = self.config_main_low_duration_b
                case 2: duration = self.config_main_high_duration_a
                case 3: duration = self.config_main_high_duration_b

        return {
            'duration': (duration + 2) << prescaler,
            'output': symbol_transmit_level ^ self.config_invert_output
        }
        
    # In 2bpe mode,
    # each element is 2 bits, represented by a tuple of 1 bit each
    async def test_expected_waveform_2bpe(self, program: list[tuple[int, int]]):
        assert len(program) <= MAX_PROGRAM_2BPE_LEN

        # We pre-generate the duration and expected output level (before inversion) in a 2-tuple
        waveform = []
        for i, symbol_tuple in enumerate(program):
            if i < 8 and (self.config_auxillary_mask & (1 << i)):
                use_auxillary = True
            else:
                use_auxillary = False
            
            dict = self._get_expected_from_symbol((symbol_tuple[1] << 1 ) | symbol_tuple[0], use_auxillary)
            
            waveform.append((dict["duration"], dict["output"]))

        await self._test_expected_waveform(waveform)

    # In 1bpe mode,
    # each element is 1 bit
    async def test_expected_waveform_1bpe(self, program: list[int]):
        assert len(program) <= MAX_PROGRAM_1BPE_LEN
        
        # We pre-generate the duration and expected output level (before inversion) in a 2-tuple
        # Note that we expand our program, so the len(waveform) is twice the len(program)
        waveform = []
        for i, single_bit_value in enumerate(program):
            if(single_bit_value):
                first_symbol = self.config_high_symbol_0
                second_symbol = self.config_high_symbol_1
            else:
                first_symbol = self.config_low_symbol_0
                second_symbol = self.config_low_symbol_1

            if i < 8 and (self.config_auxillary_mask & (1 << i)):
                use_auxillary = True
            else:
                use_auxillary = False

            first_dict = self._get_expected_from_symbol(first_symbol, use_auxillary)
            second_dict = self._get_expected_from_symbol(second_symbol, use_auxillary)
            
            waveform.append((first_dict["duration"], first_dict["output"]))
            waveform.append((second_dict["duration"], second_dict["output"]))
            
        await self._test_expected_waveform(waveform)
    
    
    # example waveform [(2, 1), (3, 0), (4, 1), (4, 1), (5, 0)] 
    async def _test_expected_waveform(self, waveform: list[tuple[int, int]]):
        # config_carrier_en must be 0, generation of expected_waveform not supported with this parameter
        assert not self.config_carrier_en

        # lets start the test
        # the program must be already configured
        # Must run concurrently
        cocotb.start_soon(self.start_program()) #await self.start_program()

        # Wait until valid output goes high
        while(self.dut.uo_out[1].value == 0):
            await ClockCycles(self.dut.clk, 1)

        #await RisingEdge(self.dut.test_harness.user_peripheral.valid_output)

        
        # when config_program_loop_count = 0, the program executes once
        # when config_program_loop_count = 1, the program executes twice
        # and so on...
        if(self.config_loop_forever):
            self.dut._log.info(f'config_loop_forever is enabled, but we will only test for {MAX_TEST_INFINITE_LOOP_LEN} number of loops')
            program_loop_counter = MAX_TEST_INFINITE_LOOP_LEN
        else:
            program_loop_counter = self.config_program_loop_count + 1
        
        waveform_len = len(waveform)
        output_valid = True

        # In 2bpe (2 bits per element) mode, program_counter is incremented by 2 each time
        # In 1bpe (1 bits per element) mode, program_counter is incremented by 1 each time

        internal_program_counter = self.config_program_start_index

        while(output_valid):
            if (self.config_use_2bpe):
                assert (internal_program_counter >> 1) < waveform_len # make sure don't access out of bounds
                assert internal_program_counter % 2 == 0 # should be a multiple of 2

                duration = waveform[internal_program_counter >> 1][0]
                expected_level = waveform[internal_program_counter >> 1][1]

                for i in range(duration): # check every cycle for thoroughness
                    assert self.dut.uo_out[5].value == expected_level
                    await ClockCycles(self.dut.clk, 1) 
            else:
                assert internal_program_counter < waveform_len # make sure don't access out of bounds
                duration = waveform[internal_program_counter * 2][0]
                expected_level = waveform[internal_program_counter * 2][1]

                for i in range(duration): # check every cycle for thoroughness
                    assert self.dut.uo_out[5].value == expected_level
                    await ClockCycles(self.dut.clk, 1) 

                assert internal_program_counter < waveform_len # make sure don't access out of bounds
                duration = waveform[internal_program_counter * 2 + 1][0]
                expected_level = waveform[internal_program_counter * 2 + 1][1]

                for i in range(duration): # check every cycle for thoroughness
                    assert self.dut.uo_out[5].value == expected_level
                    await ClockCycles(self.dut.clk, 1) 
                    
            if(internal_program_counter == self.config_program_end_index):
                program_loop_counter -= 1
                
                if(program_loop_counter > 0):
                    internal_program_counter = self.config_program_loopback_index
                else:
                    output_valid = False
            else:
                if (self.config_downcount):
                    if (self.config_use_2bpe):
                        internal_program_counter -= 2
                    else:
                        internal_program_counter -= 1
                else:
                    if (self.config_use_2bpe):
                        internal_program_counter += 2
                    else:
                        internal_program_counter += 1
                 
                # Simulate rollover / wrapping
                if(internal_program_counter >= MAX_PROGRAM_1BPE_LEN):
                    internal_program_counter = internal_program_counter - MAX_PROGRAM_1BPE_LEN
                elif(internal_program_counter < 0):
                    internal_program_counter = internal_program_counter + MAX_PROGRAM_1BPE_LEN
        
        if(not self.config_loop_forever): # do not check if config_loop_forever is enabled
            # lets check the idle state is correct for the next n number of cycles for good measure
            total_duration = 999
            for w in waveform:
                duration = w[0]
                total_duration += duration

            for i in range(total_duration):
                assert self.dut.uo_out[5].value == (self.config_idle_level ^ self.config_invert_output)
                await ClockCycles(self.dut.clk, 1)


#  Simulate Pulse Distance Encoding
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def encoded_1bpe_test1(dut):
    device = Device(dut)
    await device.init()

    program = [1, 0]
    
    device.config_program_end_index = len(program) - 1
    device.config_main_high_duration_a = 0

    # Note (1, 0) means 0b01, I know.... :(

    # A low bit indicates the following symbol sequence: [(0, 1), (0, 0)]
    device.config_low_symbol_0 = 0b10
    device.config_low_symbol_1 = 0b00
    
    # A high bit indicates the following symbol sequence: [(0, 1), (1, 0)]
    device.config_high_symbol_0 = 0b10
    device.config_high_symbol_1 = 0b01
    
    device.config_main_low_duration_a = 5
    device.config_main_low_duration_b = 10 # longer

    device.config_main_high_duration_a = 5
    #device.config_main_high_duration_b is unused

    await device.write_program_1bpe(program)
    await device.test_expected_waveform_1bpe(program)

# Simulate Pulse Distance Encoding
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def encoded_1bpe_test2(dut):
    device = Device(dut)
    await device.init()

    program = [1, 0, 0, 0, 1, 1, 1, 0, 1]
    
    device.config_program_end_index = len(program) - 1
    device.config_main_high_duration_a = 0

    # Note (1, 0) means 0b01, I know.... :(

    # A low bit indicates the following symbol sequence: [(0, 1), (0, 0)]
    device.config_low_symbol_0 = 0b10
    device.config_low_symbol_1 = 0b00
    
    # A high bit indicates the following symbol sequence: [(0, 1), (1, 0)]
    device.config_high_symbol_0 = 0b10
    device.config_high_symbol_1 = 0b01
    
    device.config_main_low_duration_a = 5
    device.config_main_low_duration_b = 10 # longer

    device.config_main_high_duration_a = 5
    #device.config_main_high_duration_b is unused

    await device.write_program_1bpe(program)
    await device.test_expected_waveform_1bpe(program)

# Simulate Pulse Distance Encoding, with initial long header pulse
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def encoded_1bpe_test3(dut):
    device = Device(dut)
    await device.init()

    program = [1, 1, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
    
    device.config_program_end_index = len(program) - 1
    device.config_main_high_duration_a = 0

    # Note (1, 0) means 0b01, I know.... :(

    # A low bit indicates the following symbol sequence: [(0, 1), (0, 0)]
    device.config_low_symbol_0 = 0b10
    device.config_low_symbol_1 = 0b00
    
    # A high bit indicates the following symbol sequence: [(0, 1), (1, 0)]
    device.config_high_symbol_0 = 0b10
    device.config_high_symbol_1 = 0b01
    
    device.config_main_low_duration_a = 5
    device.config_main_low_duration_b = 10 # longer

    device.config_main_high_duration_a = 5
    #device.config_main_high_duration_b is unused
    
    device.config_auxillary_mask = 0b0000001
    device.config_auxillary_duration_a = 50
    device.config_auxillary_duration_b = 25
    device.config_auxillary_prescaler = 2

    await device.write_program_1bpe(program)
    await device.test_expected_waveform_1bpe(program)

# Simulate Pulse Width Encoding
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def encoded_1bpe_test4(dut):
    device = Device(dut)
    await device.init()

    program = [1, 0, 0, 0, 1, 1, 1, 0, 1]
    
    device.config_program_end_index = len(program) - 1
    device.config_main_high_duration_a = 0

    # Note (1, 0) means 0b01, I know.... :(

    device.config_low_symbol_0 = 0b10
    device.config_low_symbol_1 = 0b00
    
    device.config_high_symbol_0 = 0b11
    device.config_high_symbol_1 = 0b00
    
    device.config_main_low_duration_a = 5
    #device.config_main_low_duration_b = is unused

    device.config_main_high_duration_a = 5
    device.config_main_high_duration_b = 10

    await device.write_program_1bpe(program)
    await device.test_expected_waveform_1bpe(program)

# Simulate Manchester Encoding
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def encoded_1bpe_test5(dut):
    device = Device(dut)
    await device.init()

    program = [1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1]
    
    device.config_program_end_index = len(program) - 1
    device.config_main_high_duration_a = 0

    # Note (1, 0) means 0b01, I know.... :(

    # Falling from 0 to 1
    device.config_low_symbol_0 = 0b10
    device.config_low_symbol_1 = 0b00
    
    # Rising from 0 to 1
    device.config_high_symbol_0 = 0b00
    device.config_high_symbol_1 = 0b10
    
    device.config_main_low_duration_a = 0
    #device.config_main_low_duration_b = is unused

    device.config_main_high_duration_a = 0
    # device.config_main_high_duration_b is unused

    await device.write_program_1bpe(program)
    await device.test_expected_waveform_1bpe(program)

# Simulate WS2812B timings to display cyan colour
# There are different timings online, so I just settled on this:
# T0H -> 350 ns
# T1H -> 800 ns
# T0L -> 800 ns
# T1H -> 350 ns
# Assuming we are running at 64 MHz, we will get a good 15.625 ns resolution
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def encoded_1bpe_test6(dut):
    device = Device(dut)
    await device.init()

    program = [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1]
    
    device.config_program_end_index = len(program) - 1

    device.config_low_symbol_0 = 0b10
    device.config_low_symbol_1 = 0b00
    
    device.config_high_symbol_0 = 0b11
    device.config_high_symbol_1 = 0b01
    
    device.config_main_low_duration_a = 52   # Target 850 ns, actual 843.75 ns
    device.config_main_low_duration_b = 20   # Target 350 ns, actual 343.75 ns

    device.config_main_high_duration_a = 20  # Target 350 ns, actual 343.75 ns
    device.config_main_high_duration_b = 52  # Target 800 ns, actual 843.75 ns

    await device.write_program_1bpe(program)
    await device.test_expected_waveform_1bpe(program)

# Simulate WS2812B timings, with down counting, and loop. To repeat the colour on multiple pixels.
# There are different timings online, so I just settled on this:
# T0H -> 350 ns
# T1H -> 800 ns
# T0L -> 800 ns
# T1H -> 350 ns
# Assuming we are running at 64 MHz, we will get a good 15.625 ns resolution
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def encoded_1bpe_test7(dut):
    device = Device(dut)
    await device.init()

    program = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1]
    
    device.config_downcount = 1
    device.config_program_start_index = len(program) - 1
    device.config_program_loopback_index = len(program) - 1
    device.config_program_end_index = 0

    device.config_program_loop_count = 1

    device.config_low_symbol_0 = 0b10
    device.config_low_symbol_1 = 0b00
    
    device.config_high_symbol_0 = 0b11
    device.config_high_symbol_1 = 0b01
    
    device.config_main_low_duration_a = 52   # Target 850 ns, actual 843.75 ns
    device.config_main_low_duration_b = 20   # Target 350 ns, actual 343.75 ns

    device.config_main_high_duration_a = 20  # Target 350 ns, actual 343.75 ns
    device.config_main_high_duration_b = 52  # Target 800 ns, actual 843.75 ns

    await device.write_program_1bpe(program)
    await device.test_expected_waveform_1bpe(program)

# Basic test
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_2bpe_test1(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1)]

    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_high_duration_a = 0

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Basic test
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_2bpe_test2(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1)]

    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_high_duration_a = 157

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Basic test
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_2bpe_test3(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 2
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 3

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Basic test with output inverted
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_2bpe_test4(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_use_2bpe = 1
    device.config_invert_output = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 3
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 2

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Basic test
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_2bpe_test5(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0), (1, 1), (1, 1), (1, 0)]
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 13
    device.config_main_low_duration_b = 34
    device.config_main_high_duration_a = 10
    device.config_main_high_duration_b = 10

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Basic test
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_2bpe_test6(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0), (1, 1), (1, 1), (0, 0), (0, 0), (1, 0), (0, 1)]
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    
    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Basic test with idle level
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_2bpe_test7(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0), (1, 1), (1, 1), (0, 0), (0, 0), (1, 0), (0, 1)]
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_idle_level = 1
    
    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Basic test with prescaler
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_2bpe_test8(dut):
    device = Device(dut)
    await device.init()

    program = [(1, 0), (0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 2
    device.config_main_low_duration_b = 0
    device.config_main_high_duration_a = 4
    device.config_main_high_duration_b = 6
    device.config_main_prescaler = 1

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Basic test with prescaler
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_2bpe_test9(dut):
    device = Device(dut)
    await device.init()

    program = [(1, 0), (0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 2
    device.config_main_low_duration_b = 0
    device.config_main_high_duration_a = 4
    device.config_main_high_duration_b = 6
    device.config_main_prescaler = 2

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Basic test with bigger prescaler
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_2bpe_test10(dut):
    device = Device(dut)
    await device.init()

    program = [(1, 0), (0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 3
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 2
    device.config_main_prescaler = 9

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Basic test to test that config_program_end_index is respected
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_2bpe_test11(dut):
    device = Device(dut)
    await device.init()

    program = [(1, 0), (0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 3
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 2

    # fill in the rest of the buffer with some data
    program_with_extras = [(1, 0), (0, 1), (0, 0), (1, 1), (1, 0), (1, 0), (0, 1), (0, 0), (1, 1), (1, 0), (0, 0), (1, 1), (1, 0), (1, 0), (0, 1)]
    await device.write_program_2bpe(program_with_extras)

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Basic test to test that config_program_start_index is respected
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_2bpe_test12(dut):
    device = Device(dut)
    await device.init()

    program = [(1, 0), (0, 1), (0, 0), (1, 1), (1, 0)]

    device.config_use_2bpe = 1    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_program_start_index = 3 * 2
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 3
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 2

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Basic test rollover / wrapping test
# It starts at config_program_start_index, rolls over, 
# and terminates at config_program_end_index without looping
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_2bpe_test13(dut):
    device = Device(dut)
    await device.init()

    program_len = MAX_PROGRAM_2BPE_LEN
    
    program = []

    random.seed(8888) 
    for _ in range(program_len):
        duration_selector = random.randint(0, 1)  # 1-bit selector: 0 or 1
        transmit_level = random.randint(0, 1)     # 1-bit transmit level: 0 or 1
        program.append((duration_selector, transmit_level))
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_program_start_index = 77 * 2
    device.config_program_end_index = 33 * 2
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 3
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 2

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Basic test MAX_PROGRAM_2BPE_LEN number of symbols
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_2bpe_test14(dut):
    device = Device(dut)
    await device.init()

    program_len = MAX_PROGRAM_2BPE_LEN
    
    program = []

    random.seed(8888) 
    for _ in range(program_len):
        duration_selector = random.randint(0, 1)  # 1-bit selector: 0 or 1
        transmit_level = random.randint(0, 1)     # 1-bit transmit level: 0 or 1
        program.append((duration_selector, transmit_level))
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Basic test MAX_PROGRAM_2BPE_LEN number of symbols with prescaler
@cocotb.test(timeout_time=11, timeout_unit="ms")
async def basic_2bpe_test15(dut):
    device = Device(dut)
    await device.init()

    program_len = MAX_PROGRAM_2BPE_LEN
    
    program = []

    random.seed(8888) 
    for _ in range(program_len):
        duration_selector = random.randint(0, 1)  # 1-bit selector: 0 or 1
        transmit_level = random.randint(0, 1)     # 1-bit transmit level: 0 or 1
        program.append((duration_selector, transmit_level))
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_main_prescaler = 3

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Basic test with infinite loop
@cocotb.test(timeout_time=11, timeout_unit="ms")
async def basic_2bpe_test16(dut):
    device = Device(dut)
    await device.init()

    program = [(1, 0), (0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_main_prescaler = 3
    device.config_loop_forever = 1

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Basic test with MAX_DURATION
@cocotb.test(timeout_time=11, timeout_unit="ms")
async def basic_2bpe_test17(dut):
    device = Device(dut)
    await device.init()

    program = [(1, 0), (0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = MAX_DURATION
    device.config_main_low_duration_a = 242
    device.config_main_high_duration_b = MAX_DURATION
    device.config_main_high_duration_a = 193

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)


# Advanced test with looping a certain number of counts
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_2bpe_test1(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1)]

    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 1

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Advanced test with looping a certain number of counts
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_2bpe_test2(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1)]

    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 2

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Advanced test with looping a certain number of counts
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_2bpe_test3(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1)]

    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 45

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Advanced test with looping MAX_PROGRAM_LOOP_LEN times
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_2bpe_test4(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0)]

    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = MAX_PROGRAM_LOOP_LEN - 1

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Advanced test with looping a certain number of counts
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_2bpe_test5(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0)]

    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 1

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Advanced test with looping a certain number of counts
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_2bpe_test6(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0)]

    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 2

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Advanced test with looping a certain number of counts
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_2bpe_test7(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0)]

    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 45

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Advanced test with looping MAX_PROGRAM_LOOP_LEN times
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_2bpe_test8(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0)]

    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = MAX_PROGRAM_LOOP_LEN - 1

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Advanced test with looping a certain number of counts with prescaler
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_2bpe_test9(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1)]

    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 1
    device.config_main_prescaler = 1

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Advanced test with looping a certain number of counts with prescaler
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_2bpe_test10(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1)]

    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 2
    device.config_main_prescaler = 1

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Advanced test with looping a certain number of counts with prescaler
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_2bpe_test11(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1)]

    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 45
    device.config_main_prescaler = 1

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Advanced test with looping MAX_PROGRAM_LOOP_LEN times with prescaler
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_2bpe_test12(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0)]

    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = MAX_PROGRAM_LOOP_LEN - 1
    device.config_main_prescaler = 1

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Advanced test with looping a certain number of counts with prescaler
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_2bpe_test13(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0)]

    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 1
    device.config_main_prescaler = 1

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Advanced test with looping a certain number of counts with prescaler
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_2bpe_test14(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0)]

    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 2
    device.config_main_prescaler = 1

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Advanced test with looping a certain number of counts with prescaler
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_2bpe_test15(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0)]

    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 45
    device.config_main_prescaler = 1

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Advanced test with looping MAX_PROGRAM_LOOP_LEN times
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_2bpe_test16(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0)]

    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = MAX_PROGRAM_LOOP_LEN - 1

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Advanced test with looping a certain number of counts, with MAX_PROGRAM_2BPE_LEN number of symbols
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_2bpe_test17(dut):
    device = Device(dut)
    await device.init()

    program_len = MAX_PROGRAM_2BPE_LEN
    
    program = []

    random.seed(8888) 
    for _ in range(program_len):
        duration_selector = random.randint(0, 1)  # 1-bit selector: 0 or 1
        transmit_level = random.randint(0, 1)     # 1-bit transmit level: 0 or 1
        program.append((duration_selector, transmit_level))
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 1

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Advanced test with looping a certain number of counts, with MAX_PROGRAM_2BPE_LEN number of symbols
@cocotb.test(timeout_time=15, timeout_unit="ms")
async def advanced_2bpe_test18(dut):
    device = Device(dut)
    await device.init()

    program_len = MAX_PROGRAM_2BPE_LEN
    
    program = []

    random.seed(8888) 
    for _ in range(program_len):
        duration_selector = random.randint(0, 1)  # 1-bit selector: 0 or 1
        transmit_level = random.randint(0, 1)     # 1-bit transmit level: 0 or 1
        program.append((duration_selector, transmit_level))
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 0
    device.config_main_low_duration_a = 1
    device.config_main_high_duration_b = 2
    device.config_main_high_duration_a = 0
    device.config_program_loop_count = 23

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Advanced test with looping a MAX_PROGRAM_LOOP_LEN times, with MAX_PROGRAM_2BPE_LEN number of symbols
@cocotb.test(timeout_time=15, timeout_unit="ms")
async def advanced_2bpe_test19(dut):
    device = Device(dut)
    await device.init()

    program_len = MAX_PROGRAM_2BPE_LEN
    
    program = []

    random.seed(8888) 
    for _ in range(program_len):
        duration_selector = random.randint(0, 1)  # 1-bit selector: 0 or 1
        transmit_level = random.randint(0, 1)     # 1-bit transmit level: 0 or 1
        program.append((duration_selector, transmit_level))
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 0
    device.config_main_low_duration_a = 1
    device.config_main_high_duration_b = 2
    device.config_main_high_duration_a = 0
    device.config_program_loop_count = MAX_PROGRAM_LOOP_LEN - 1

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Advanced test with auxillary duration
@cocotb.test(timeout_time=15, timeout_unit="ms")
async def advanced_2bpe_test20(dut):
    device = Device(dut)
    await device.init()

    program = [(1, 0), (0, 1), (0, 0), (1, 1), (1, 0), (1, 0), (0, 1), (0, 0), (1, 1), (1, 0), (0, 0), (1, 1), (1, 0), (1, 0), (0, 1)]

    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 0
    device.config_main_low_duration_a = 1
    device.config_main_high_duration_b = 2
    device.config_main_high_duration_a = 0
    device.config_auxillary_duration_a = 42
    device.config_auxillary_duration_b = 98
    device.config_auxillary_mask = 0b10101010
     
    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Advanced test with auxillary duration and auxillary prescaler
@cocotb.test(timeout_time=15, timeout_unit="ms")
async def advanced_2bpe_test21(dut):
    device = Device(dut)
    await device.init()

    program = [(1, 0), (0, 1), (0, 0), (1, 1), (1, 0), (1, 0), (0, 1), (0, 0), (1, 1), (1, 0), (0, 0), (1, 1), (1, 0), (1, 0), (0, 1)]

    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 0
    device.config_main_low_duration_a = 1
    device.config_main_high_duration_b = 2
    device.config_main_high_duration_a = 0
    device.config_auxillary_duration_a = 4 #33
    device.config_auxillary_duration_b = 4 #127
    device.config_auxillary_prescaler = 1
    device.config_auxillary_mask = 0b10101010
     
    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Advanced test with auxillary duration and larger auxillary prescaler
@cocotb.test(timeout_time=15, timeout_unit="ms")
async def advanced_2bpe_test22(dut):
    device = Device(dut)
    await device.init()

    program = [(1, 0), (0, 1), (0, 0), (1, 1), (1, 0), (1, 0), (0, 1), (0, 0), (1, 1), (1, 0), (0, 0), (1, 1), (1, 0), (1, 0), (0, 1)]

    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 0
    device.config_main_low_duration_a = 1
    device.config_main_high_duration_b = 2
    device.config_main_high_duration_a = 0
    device.config_auxillary_duration_a = 33
    device.config_auxillary_duration_b = 127
    device.config_auxillary_prescaler = 6
    device.config_auxillary_mask = 0b10101010
     
    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Elite test with looping and config_program_loopback_index set to exactly the (len(program) - 1) * 2
# So it should run from 0 to (len(program) - 1) * 2, then the last symbol is repeatedly sent
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def elite_2bpe_test1(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0), (1, 0), (1, 0), (0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 3
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 2
    device.config_program_loop_count = 10
    device.config_program_loopback_index = (len(program) - 1) * 2

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Elite test with looping and config_program_loopback_index set to exactly the (len(program) - 2) * 2
# So it should run from 0 to (len(program) - 1) * 2 then the last 2 symbols is repeatedly sent
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def elite_2bpe_test2(dut):
    device = Device(dut)
    await device.init()
    
    program = [(0, 1), (0, 0), (1, 0), (1, 0), (0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 3
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 2
    device.config_program_loop_count = 10
    device.config_program_loopback_index = (len(program) - 2) * 2

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Elite test with looping and config_program_loopback_index set to exactly to 1 * 2
# So it should run from 0 to (len(program) - 1) * 2, then the last len(program) - 1 number of symbols is repeatedly sent
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def elite_2bpe_test3(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0), (1, 0), (1, 0), (0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 3
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 2
    device.config_program_loop_count = 10
    device.config_program_loopback_index = 1 * 2

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Elite test with looping and config_program_loopback_index set to exactly the (len(program) - 1) * 2, with MAX_PROGRAM_2BPE_LEN number of symbols
# So it should run from 0 to (len(program) - 1) * 2, then the last symbol is repeatedly sent
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def elite_2bpe_test4(dut):
    device = Device(dut)
    await device.init()

    program_len = MAX_PROGRAM_2BPE_LEN

    program = []

    random.seed(8888) 
    for _ in range(program_len):
        duration_selector = random.randint(0, 1)  # 1-bit selector: 0 or 1
        transmit_level = random.randint(0, 1)     # 1-bit transmit level: 0 or 1
        program.append((duration_selector, transmit_level))
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 3
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 2
    device.config_program_loop_count = 55
    device.config_program_loopback_index = (len(program) - 1) * 2

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Elite test with looping and config_program_loopback_index set to exactly the (len(program) - 2) * 2, with MAX_PROGRAM_2BPE_LEN number of symbols
# So it should run from 0 to (len(program) - 1) * 2 then the last 2 symbols is repeatedly sent
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def elite_2bpe_test5(dut):
    device = Device(dut)
    await device.init()

    program_len = MAX_PROGRAM_2BPE_LEN

    program = []

    random.seed(8888) 
    for _ in range(program_len):
        duration_selector = random.randint(0, 1)  # 1-bit selector: 0 or 1
        transmit_level = random.randint(0, 1)     # 1-bit transmit level: 0 or 1
        program.append((duration_selector, transmit_level))
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 3
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 2
    device.config_program_loop_count = 55
    device.config_program_loopback_index = (len(program) - 2) * 2

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)
 

# Elite test with rollover / wrapping, with auxillary prescaler and auxillary duration
# It starts at config_program_start_index, rolls over,
# and terminates at config_program_end_index without looping
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def elite_2bpe_test6(dut):
    device = Device(dut)
    await device.init()

    program_len = MAX_PROGRAM_2BPE_LEN

    program = []

    random.seed(8888) 
    for _ in range(program_len):
        duration_selector = random.randint(0, 1)  # 1-bit selector: 0 or 1
        transmit_level = random.randint(0, 1)     # 1-bit transmit level: 0 or 1
        program.append((duration_selector, transmit_level))
    
    device.config_use_2bpe = 1
    device.config_program_start_index = 100 * 2
    device.config_program_end_index = 33 * 2
    device.config_main_low_duration_a = 15
    device.config_main_low_duration_b = 35
    device.config_main_high_duration_a = 10
    device.config_main_high_duration_b = 55
    device.config_auxillary_mask = 0b00000001
    device.config_auxillary_duration_b = 100
    device.config_auxillary_duration_a = 50
    device.config_auxillary_prescaler = 3

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Elite test with rollover / wrapping, with auxillary prescaler and auxillary duration
# It starts at config_program_start_index, rolls over,
# and terminates at config_program_end_index without looping
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def elite_2bpe_test7(dut):
    device = Device(dut)
    await device.init()

    program_len = MAX_PROGRAM_2BPE_LEN

    program = []

    random.seed(8888) 
    for _ in range(program_len):
        duration_selector = random.randint(0, 1)  # 1-bit selector: 0 or 1
        transmit_level = random.randint(0, 1)     # 1-bit transmit level: 0 or 1
        program.append((duration_selector, transmit_level))
    
    device.config_use_2bpe = 1
    device.config_program_start_index = 100 * 2
    device.config_program_end_index = 33 * 2
    device.config_main_low_duration_a = 15
    device.config_main_low_duration_b = 35
    device.config_main_high_duration_a = 10
    device.config_main_high_duration_b = 55
    device.config_auxillary_mask = 0b00111100
    device.config_auxillary_duration_b = 100
    device.config_auxillary_duration_a = 50
    device.config_auxillary_prescaler = 3

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

# Interrupt disable test - do not enable interrupts,
# but we loop, have program counter past 64
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def interrupt_2bpe_test1(dut):
    device = Device(dut)
    await device.init()

    program = []

    random.seed(1234) 
    for _ in range(96):
        duration_selector = random.randint(0, 1)  # 1-bit selector: 0 or 1
        transmit_level = random.randint(0, 1)     # 1-bit transmit level: 0 or 1
        program.append((duration_selector, transmit_level))
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 2
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 3
    device.config_program_loop_count = 4

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

    assert not await device.tqv.is_interrupt_asserted()

# Program end interrupt test, using 8 bit write to clear
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def interrupt_2bpe_test2(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_program_end_interrupt_en = 1
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 2
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 3

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

    assert await device.tqv.is_interrupt_asserted()

    await device.clear_interrupts(
        clear_timer_interrupt = 1,
        clear_program_loop_interrupt = 1,
        clear_program_end_interrupt = 0,  # Means no effect (don't clear program end interrupt)
        clear_program_counter_mid_interrupt = 1
    )
    # there should be no effect, program end interrupt interrupt should not be cleared
    assert await device.tqv.is_interrupt_asserted()

    await device.clear_interrupts(
        clear_timer_interrupt = 0,
        clear_program_loop_interrupt = 0,
        clear_program_end_interrupt = 1,
        clear_program_counter_mid_interrupt = 0
    )

    assert not await device.tqv.is_interrupt_asserted()

# Program end interrupt test using 32 bit write to clear
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def interrupt_2bpe_test3(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_program_end_interrupt_en = 1
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 2
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 3

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

    assert await device.tqv.is_interrupt_asserted()

    await device.clear_interrupts_using32(
        clear_timer_interrupt = 1,
        clear_program_loop_interrupt = 1,
        clear_program_end_interrupt = 0, # Means no effect (don't clear timer interrupt)
        clear_program_counter_mid_interrupt = 1
    )

    # there should be no effect
    assert await device.tqv.is_interrupt_asserted()
    
    await device.clear_interrupts_using32(
        clear_timer_interrupt = 0,
        clear_program_loop_interrupt = 0,
        clear_program_end_interrupt = 1,
        clear_program_counter_mid_interrupt = 0
    )
    assert not await device.tqv.is_interrupt_asserted()

# Loop interrupt test
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def interrupt_2bpe_test4(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_loop_interrupt_en = 1
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 2
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 3

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

    # No interrupt triggered because we did not loop
    assert not await device.tqv.is_interrupt_asserted()

    device.config_program_loop_count = 2

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

    # Interrupt triggered because we looped once
    assert await device.tqv.is_interrupt_asserted()

    await device.clear_interrupts_using32(
        clear_timer_interrupt = 0,
        clear_program_loop_interrupt = 1,
        clear_program_end_interrupt = 0,
        clear_program_counter_mid_interrupt = 0
    )

    assert not await device.tqv.is_interrupt_asserted()

# Timer interrupt test
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def interrupt_2bpe_test5(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_use_2bpe = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_timer_interrupt_en = 1
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 2
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 3

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

    assert await device.tqv.is_interrupt_asserted()


    # Interrupt triggered because we looped once
    assert await device.tqv.is_interrupt_asserted()

    await device.clear_interrupts(
        clear_timer_interrupt = 1,
        clear_program_loop_interrupt = 1,
        clear_program_end_interrupt = 1,
        clear_program_counter_mid_interrupt = 1
    )

    assert not await device.tqv.is_interrupt_asserted()
 
# Program counter mid interrupt test
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def interrupt_2bpe_test6(dut):
    device = Device(dut)
    await device.init()

    program_len = MAX_PROGRAM_2BPE_LEN
    
    program = []

    random.seed(8888) 
    for _ in range(program_len):
        duration_selector = random.randint(0, 1)  # 1-bit selector: 0 or 1
        transmit_level = random.randint(0, 1)     # 1-bit transmit level: 0 or 1
        program.append((duration_selector, transmit_level))
    
    device.config_use_2bpe = 1
    device.config_program_end_index = 63 * 2
    device.config_program_counter_mid_interrupt_en = 1
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 2
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 3

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

    # No interrupt triggered because program counter did not reach 64
    assert not await device.tqv.is_interrupt_asserted()

    device.config_program_end_index = 64 * 2

    await device.write_program_2bpe(program)
    await device.test_expected_waveform_2bpe(program)

    # Interrupt triggered because program counter reached 64
    assert await device.tqv.is_interrupt_asserted()

    await device.clear_interrupts_using32(
        clear_timer_interrupt = 0,
        clear_program_loop_interrupt = 0,
        clear_program_end_interrupt = 0,
        clear_program_counter_mid_interrupt = 1
    )

    assert not await device.tqv.is_interrupt_asserted()


# make sure we can switch different program & configs without residue

#assert await tqv.read_word_reg(8) == 0