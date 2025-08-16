# SPDX-FileCopyrightText: © 2025 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

from tqv import TinyQV

# When submitting your design, change this to 16 + the peripheral number
# in peripherals.v.  e.g. if your design is i_user_simple00, set this to 16.
# The peripheral number is not used by the test harness.
PERIPHERAL_NUM = 24

@cocotb.test()
async def test_project(dut):
    dut._log.info("Start")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Interact with your design's registers through this TinyQV class.
    # This will allow the same test to be run when your design is integrated
    # with TinyQV - the implementation of this class will be replaces with a
    # different version that uses Risc-V instructions instead of the SPI 
    # interface to read and write the registers.
    tqv = TinyQV(dut, PERIPHERAL_NUM)

    # Reset, always start the test by resetting TinyQV
    await tqv.reset()
    assert await tqv.read_reg(0) == 0
    assert await tqv.read_reg(1) == 0
    assert await tqv.read_reg(2) == 0
    assert await tqv.read_reg(3) == 0
    assert await tqv.read_reg(4) == 0
    assert await tqv.read_reg(5) == 0
    assert await tqv.read_reg(6) == 0
    assert await tqv.read_reg(7) == 0
    assert await tqv.read_reg(8) == 0
    assert await tqv.read_reg(9) == 0
    assert await tqv.read_reg(10) == 0
    assert await tqv.read_reg(11) == 0
    assert await tqv.read_reg(12) == 0
    assert await tqv.read_reg(13) == 0
    assert await tqv.read_reg(14) == 0
    assert await tqv.read_reg(15) == 0

    dut._log.info("Test project behavior")

    # Test register write and read back
    await tqv.write_reg(3, 0x41)
    assert await tqv.read_reg(0) == 1
    assert await tqv.read_reg(1) == 1
    assert await tqv.read_reg(2) == 2
    assert await tqv.read_reg(3) == 1
    assert await tqv.read_reg(4) == 0
    assert await tqv.read_reg(5) == 0
    assert await tqv.read_reg(6) == 0
    assert await tqv.read_reg(7) == 0
    assert await tqv.read_reg(8) == 0
    assert await tqv.read_reg(9) == 0
    assert await tqv.read_reg(10) == 0
    assert await tqv.read_reg(11) == 0x41
    assert await tqv.read_reg(12) == 0
    assert await tqv.read_reg(13) == 0
    assert await tqv.read_reg(14) == 0
    assert await tqv.read_reg(15) == 0x41

    # Keep testing the module by changing the input values, waiting for
    # one or more clock cycles, and asserting the expected output values.
    await tqv.write_reg(0, 0xFF)
    assert await tqv.read_reg(0) == 0
    assert await tqv.read_reg(1) == 0
    assert await tqv.read_reg(2) == 0
    assert await tqv.read_reg(3) == 0
    assert await tqv.read_reg(4) == 0
    assert await tqv.read_reg(5) == 0
    assert await tqv.read_reg(6) == 0
    assert await tqv.read_reg(7) == 0
    assert await tqv.read_reg(8) == 0
    assert await tqv.read_reg(9) == 0
    assert await tqv.read_reg(10) == 0
    assert await tqv.read_reg(11) == 0
    assert await tqv.read_reg(12) == 0
    assert await tqv.read_reg(13) == 0
    assert await tqv.read_reg(14) == 0
    assert await tqv.read_reg(15) == 0

    global ctl
    ctl = 0xFF

    ERRS = 0x02 # errors/properties output
    CHKR = 0x04 # range check
    IOBE = 0x08 # big endian I/O

    UNDERFLOW = 0x00
    READY     = 0x01
    RETRY     = 0x02
    INVALID   = 0x04
    OVERLONG  = 0x08
    NONUNI    = 0x10
    ERROR     = 0x20

    NORMAL    = 0x01
    CONTROL   = 0x02
    SURROGATE = 0x04
    HIGHCHAR  = 0x08
    PRIVATE   = 0x10
    NONCHAR   = 0x20

    async def clear_input(b):
        global ctl
        ctl &=~ b
        await tqv.write_reg(4, ctl)

    async def set_input(b):
        global ctl
        ctl |= b
        await tqv.write_reg(4, ctl)

    async def write_byte(b, eof):
        await tqv.write_reg(3, b)
        assert (1 if (((await tqv.read_reg(3)) & 15) >= 6) else 0) == eof

    async def read_byte(b, eof):
        await tqv.write_reg(7, 0)
        assert await tqv.read_reg(7) == b
        assert (1 if ((await tqv.read_reg(3)) & 128) else 0) == eof

    async def write_char(b):
        await tqv.write_reg(1, b)

    async def read_char(b):
        await tqv.write_reg(5, 0)
        assert await tqv.read_reg(5) == b

    async def read_reset():
        global ctl
        await tqv.write_reg(4, ctl)

    async def write_reset():
        global ctl
        await tqv.write_reg(0, ctl)

    async def write_cp(cp):
        await tqv.write_reg(1, (cp >> 24) & 0xFF)
        await tqv.write_reg(1, (cp >> 16) & 0xFF)
        await tqv.write_reg(1, (cp >> 8) & 0xFF)
        await tqv.write_reg(1, cp & 0xFF)

    async def write_utf16(*args, tl=None):
        for b in args:
            await tqv.write_reg(2, b)
        assert await tqv.read_reg(2) == (len(args) if tl is None else tl)

    async def write_bytes(*args, tl=None):
        for b in args:
            await tqv.write_reg(3, b)
        assert await tqv.read_reg(3) == (len(args) if tl is None else tl)

    async def read_bytes(*args):
        for b in args:
            assert await tqv.read_reg(3) == len(args)
            await tqv.write_reg(7, 0)
            assert await tqv.read_reg(7) == b
        assert await tqv.read_reg(3) == len(args) | 128
        await tqv.write_reg(7, 0)
        assert await tqv.read_reg(7) == 0
        assert await tqv.read_reg(3) == len(args) | 128

    async def read_utf16(*args):
        for b in args:
            assert await tqv.read_reg(2) == len(args)
            await tqv.write_reg(6, 0)
            assert await tqv.read_reg(6) == b
        assert await tqv.read_reg(2) == len(args) | 128
        await tqv.write_reg(6, 0)
        assert await tqv.read_reg(6) == 0
        assert await tqv.read_reg(2) == len(args) | 128

    async def read_cp(cp):
        assert await tqv.read_reg(8) == (cp >> 24) & 0xFF
        assert await tqv.read_reg(9) == (cp >> 16) & 0xFF
        assert await tqv.read_reg(10) == (cp >> 8) & 0xFF
        assert await tqv.read_reg(11) == cp & 0xFF
        assert await tqv.read_reg(12) == (cp >> 24) & 0xFF
        assert await tqv.read_reg(13) == (cp >> 16) & 0xFF
        assert await tqv.read_reg(14) == (cp >> 8) & 0xFF
        assert await tqv.read_reg(15) == cp & 0xFF
        await tqv.write_reg(5, 0)
        assert await tqv.read_reg(5) == (cp >> 24) & 0xFF
        await tqv.write_reg(5, 0)
        assert await tqv.read_reg(5) == (cp >> 16) & 0xFF
        await tqv.write_reg(5, 0)
        assert await tqv.read_reg(5) == (cp >> 8) & 0xFF
        await tqv.write_reg(5, 0)
        assert await tqv.read_reg(5) == cp & 0xFF

    async def want_errs(errs):
        assert await tqv.read_reg(0) == errs

    async def want_retry(retry):
        assert (await tqv.read_reg(0) & RETRY) == (RETRY if retry else 0)

    async def want_props(props):
        assert await tqv.read_reg(1) == props

    # register I/O

    # write to byte buffer
    await write_byte(0xFD, 0)
    await write_byte(0xBE, 0)
    await write_byte(0xAC, 0)
    await write_byte(0x97, 0)
    await write_byte(0x86, 0)
    await write_byte(0xB5, 1)
    await write_byte(0xA4, 1)

    # read from byte buffer
    await read_byte(0xFD, 0)
    await read_byte(0xBE, 0)
    await read_byte(0xAC, 0)
    await read_byte(0x97, 0)
    await read_byte(0x86, 0)
    await read_byte(0xB5, 1)
    await read_byte(0, 1)

    # read from byte buffer again
    await read_reset()
    await read_byte(0xFD, 0)
    await read_byte(0xBE, 0)
    await read_byte(0xAC, 0)
    await read_byte(0x97, 0)
    await read_byte(0x86, 0)
    await read_byte(0xB5, 1)
    await read_byte(0, 1)

    await write_reset()

    # write to character buffer, big endian
    await write_char(11)
    await write_char(22)
    await write_char(33)
    await write_char(44)
    await write_char(55)

    # read from character buffer, big endian
    await read_char(11)
    await read_char(22)
    await read_char(33)
    await read_char(44)
    await read_char(0)

    # read from character buffer again
    await read_reset()
    await read_char(11)
    await read_char(22)
    await read_char(33)
    await read_char(44)
    await read_char(0)

    await clear_input(IOBE)
    await write_reset()

    # write to character buffer, little endian
    await write_char(11)
    await write_char(22)
    await write_char(33)
    await write_char(44)
    await write_char(55)

    # read from character buffer, little endian
    await read_char(11)
    await read_char(22)
    await read_char(33)
    await read_char(44)
    await read_char(0)

    # read from character buffer again
    await read_reset()
    await read_char(11)
    await read_char(22)
    await read_char(33)
    await read_char(44)
    await read_char(0)

    await set_input(IOBE)
    await write_reset()

    # write to byte buffer
    await write_byte(0xFD, 0)
    await write_byte(0xBE, 0)
    await write_byte(0xAC, 0)

    # read from byte buffer
    await read_byte(0xFD, 0)
    await read_byte(0xBE, 0)
    await read_byte(0xAC, 1)
    await read_byte(0, 1)

    # read from byte buffer again
    await read_reset()
    await read_byte(0xFD, 0)
    await read_byte(0xBE, 0)
    await read_byte(0xAC, 1)
    await read_byte(0, 1)

    await write_reset()

    # write to character buffer, big endian
    await write_char(111)
    await write_char(222)

    # read from character buffer, big endian
    await read_char(0)
    await read_char(0)
    await read_char(111)
    await read_char(222)
    await read_char(0)

    # read from character buffer again
    await read_reset()
    await read_char(0)
    await read_char(0)
    await read_char(111)
    await read_char(222)
    await read_char(0)

    await clear_input(IOBE)
    await write_reset()

    # write to character buffer, little endian
    await write_char(111)
    await write_char(222)

    # read from character buffer, little endian
    await read_char(111)
    await read_char(222)
    await read_char(0)
    await read_char(0)
    await read_char(0)

    # read from character buffer again
    await read_reset()
    await read_char(111)
    await read_char(222)
    await read_char(0)
    await read_char(0)
    await read_char(0)

    await set_input(IOBE)
    await write_reset()

    # UTF-8 encoding

    async def test_encode(cp, errs, props, *args):
        await write_cp(cp)
        await want_errs(errs)
        await want_props(props)
        await read_bytes(*args)
        await write_reset()

    await test_encode(0x00000000, READY, CONTROL, 0x00) # 1-byte sequence
    await test_encode(0x0000007F, READY, CONTROL, 0x7F) # 1-byte sequence
    await test_encode(0x00000080, READY, CONTROL, 0xC2, 0x80) # 2-byte sequence
    await test_encode(0x000007FF, READY, NORMAL, 0xDF, 0xBF) # 2-byte sequence
    await test_encode(0x00000800, READY, NORMAL, 0xE0, 0xA0, 0x80) # 3-byte sequence
    await test_encode(0x0000FFFF, READY, NONCHAR, 0xEF, 0xBF, 0xBF) # 3-byte sequence
    await test_encode(0x00010000, READY, NORMAL|HIGHCHAR, 0xF0, 0x90, 0x80, 0x80) # 4-byte sequence
    await test_encode(0x0010FFFF, READY, NONCHAR|HIGHCHAR, 0xF4, 0x8F, 0xBF, 0xBF) # 4-byte sequence
    await test_encode(0x00110000, READY|NONUNI|ERROR, 0, 0xF4, 0x90, 0x80, 0x80) # 4-byte sequence (out of range)
    await clear_input(CHKR) # disable range check
    await test_encode(0x00110000, READY|NONUNI, PRIVATE|HIGHCHAR, 0xF4, 0x90, 0x80, 0x80) # 4-byte sequence
    await test_encode(0x001FFFFF, READY|NONUNI, NONCHAR|HIGHCHAR, 0xF7, 0xBF, 0xBF, 0xBF) # 4-byte sequence
    await test_encode(0x00200000, READY|NONUNI, PRIVATE|HIGHCHAR, 0xF8, 0x88, 0x80, 0x80, 0x80) # 5-byte sequence
    await test_encode(0x03FFFFFF, READY|NONUNI, NONCHAR|HIGHCHAR, 0xFB, 0xBF, 0xBF, 0xBF, 0xBF) # 5-byte sequence
    await test_encode(0x04000000, READY|NONUNI, PRIVATE|HIGHCHAR, 0xFC, 0x84, 0x80, 0x80, 0x80, 0x80) # 6-byte sequence
    await test_encode(0x7FFFFFFF, READY|NONUNI, NONCHAR|HIGHCHAR, 0xFD, 0xBF, 0xBF, 0xBF, 0xBF, 0xBF) # 6-byte sequence
    await set_input(CHKR) # reënable range check
    await test_encode(0x7FFFFFFF, READY|NONUNI|ERROR, 0, 0xFD, 0xBF, 0xBF, 0xBF, 0xBF, 0xBF) # 6-byte sequence (out of range)
    await test_encode(0xFFFFFF80, READY|INVALID|ERROR, 0, 0x80) # lone trailing byte
    await test_encode(0xFFFFFFBF, READY|INVALID|ERROR, 0, 0xBF) # lone trailing byte
    await test_encode(0xFFFFFFC0, UNDERFLOW, 0, 0xC0) # lone leading byte
    await test_encode(0xFFFFFFFD, UNDERFLOW, 0, 0xFD) # lone leading byte
    await test_encode(0xFFFFFFFE, READY|INVALID|ERROR, 0, 0xFE) # lone invalid byte
    await test_encode(0xFFFFFFFF, READY|INVALID|ERROR, 0, 0xFF) # lone invalid byte

    # UTF-8 decoding

    global td_pad
    td_pad = 0

    async def test_decode(cp, errs, props, *args):
        global td_pad
        await write_bytes(*args)
        await want_errs(errs)
        await want_props(props)
        await read_cp(cp)
        await read_reset()
        if errs or td_pad < 0x80 or td_pad >= 0xC0:
            await write_bytes(td_pad, tl=len(args))
            await want_errs(errs|RETRY|ERROR)
            await want_props(props)
            await read_cp(cp)
        else:
            await write_bytes(td_pad, tl=len(args)+1)
            await want_retry(0)
        await write_reset()
        td_pad = (td_pad + 0x33) & 0xFF

    await test_decode(0x00000000, READY, CONTROL, 0x00) # 1-byte sequence
    await test_decode(0x0000007F, READY, CONTROL, 0x7F) # 1-byte sequence
    await test_decode(0x00000080, READY, CONTROL, 0xC2, 0x80) # 2-byte sequence
    await test_decode(0x000007FF, READY, NORMAL, 0xDF, 0xBF) # 2-byte sequence
    await test_decode(0x00000800, READY, NORMAL, 0xE0, 0xA0, 0x80) # 3-byte sequence
    await test_decode(0x0000FFFF, READY, NONCHAR, 0xEF, 0xBF, 0xBF) # 3-byte sequence
    await test_decode(0x00010000, READY, NORMAL|HIGHCHAR, 0xF0, 0x90, 0x80, 0x80) # 4-byte sequence
    await test_decode(0x0010FFFF, READY, NONCHAR|HIGHCHAR, 0xF4, 0x8F, 0xBF, 0xBF) # 4-byte sequence
    await test_decode(0x00110000, READY|NONUNI|ERROR, 0, 0xF4, 0x90, 0x80, 0x80) # 4-byte sequence (out of range)
    await clear_input(CHKR) # disable range check
    await test_decode(0x00110000, READY|NONUNI, PRIVATE|HIGHCHAR, 0xF4, 0x90, 0x80, 0x80) # 4-byte sequence
    await test_decode(0x001FFFFF, READY|NONUNI, NONCHAR|HIGHCHAR, 0xF7, 0xBF, 0xBF, 0xBF) # 4-byte sequence
    await test_decode(0x00200000, READY|NONUNI, PRIVATE|HIGHCHAR, 0xF8, 0x88, 0x80, 0x80, 0x80) # 5-byte sequence
    await test_decode(0x03FFFFFF, READY|NONUNI, NONCHAR|HIGHCHAR, 0xFB, 0xBF, 0xBF, 0xBF, 0xBF) # 5-byte sequence
    await test_decode(0x04000000, READY|NONUNI, PRIVATE|HIGHCHAR, 0xFC, 0x84, 0x80, 0x80, 0x80, 0x80) # 6-byte sequence
    await test_decode(0x7FFFFFFF, READY|NONUNI, NONCHAR|HIGHCHAR, 0xFD, 0xBF, 0xBF, 0xBF, 0xBF, 0xBF) # 6-byte sequence
    await set_input(CHKR) # reënable range check
    await test_decode(0x7FFFFFFF, READY|NONUNI|ERROR, 0, 0xFD, 0xBF, 0xBF, 0xBF, 0xBF, 0xBF) # 6-byte sequence (out of range)
    await test_decode(0xFFFFFF80, READY|INVALID|ERROR, 0, 0x80) # lone trailing byte
    await test_decode(0xFFFFFFBF, READY|INVALID|ERROR, 0, 0xBF) # lone trailing byte
    await test_decode(0xFFFFFFC0, UNDERFLOW, 0, 0xC0) # lone leading byte
    await test_decode(0xFFFFFFFD, UNDERFLOW, 0, 0xFD) # lone leading byte
    await test_decode(0xFFFFFFFE, READY|INVALID|ERROR, 0, 0xFE) # lone invalid byte
    await test_decode(0xFFFFFFFF, READY|INVALID|ERROR, 0, 0xFF) # lone invalid byte

    # UTF-16 encoding

    def swap32(i):
        return ((i >> 24) & 0xFF) | ((i >> 8) & 0xFF00) | ((i & 0xFF00) << 8) | ((i & 0xFF) << 24);

    async def test_encode_utf16(cp, errs, props, *args):
        await write_cp(cp)
        await want_errs(errs)
        await want_props(props)
        await read_utf16(*args)
        await clear_input(IOBE)
        await write_reset()
        await write_cp(swap32(cp))
        await want_errs(errs)
        await want_props(props)
        if len(args) == 4:
            await read_utf16(args[1], args[0], args[3], args[2])
        elif len(args) == 3:
            await read_utf16(args[1], args[0], args[2])
        elif len(args) == 2:
            await read_utf16(args[1], args[0])
        else:
            await read_utf16(*args)
        await set_input(IOBE)
        await write_reset()

    await test_encode_utf16(0x00000000, READY, CONTROL, 0x00, 0x00)
    await test_encode_utf16(0x0000FFFF, READY, NONCHAR, 0xFF, 0xFF)
    await test_encode_utf16(0x00010000, READY, NORMAL|HIGHCHAR, 0xD8, 0x00, 0xDC, 0x00)
    await test_encode_utf16(0x0010FFFF, READY, NONCHAR|HIGHCHAR, 0xDB, 0xFF, 0xDF, 0xFF)
    await test_encode_utf16(0x00110000, READY|NONUNI|ERROR, 0)
    await test_encode_utf16(0x7FFFFFFF, READY|NONUNI|ERROR, 0)
    # invalid input
    await test_encode_utf16(0x80000000, READY|INVALID|ERROR, 0)
    await test_encode_utf16(0xDDD7FFFF, READY|INVALID|ERROR, 0)
    await test_encode_utf16(0xDDD80000, UNDERFLOW, 0, 0xD8, 0x00, 0x00)
    await test_encode_utf16(0xDDDBFFFF, UNDERFLOW, 0, 0xDB, 0xFF, 0xFF)
    await test_encode_utf16(0xDDDC0000, READY|INVALID|ERROR, 0)
    await test_encode_utf16(0xDDDDDCFF, READY|INVALID|ERROR, 0)
    await test_encode_utf16(0xDDDDDD00, UNDERFLOW, 0, 0x00)
    await test_encode_utf16(0xDDDDDDFF, UNDERFLOW, 0, 0xFF)
    await test_encode_utf16(0xDDDDDE00, READY|INVALID|ERROR, 0)
    await test_encode_utf16(0xFFFFFFFF, READY|INVALID|ERROR, 0)

    # UTF-16 decoding

    async def test_decode_utf16(cp, errs, props, *args):
        tl = 2 if (errs & RETRY) else len(args)
        await write_utf16(*args, tl=tl)
        await want_errs(errs)
        await want_props(props)
        await read_cp(cp)
        await clear_input(IOBE)
        await write_reset()
        if len(args) == 4:
            await write_utf16(args[1], args[0], args[3], args[2], tl=tl)
        elif len(args) == 3:
            await write_utf16(args[1], args[0], args[2], tl=tl)
        elif len(args) == 2:
            await write_utf16(args[1], args[0], tl=tl)
        else:
            await write_utf16(*args, tl=tl)
        await want_errs(errs)
        await want_props(props)
        await read_cp(swap32(cp))
        await set_input(IOBE)
        await write_reset()

    await test_decode_utf16(0x00000000, READY, CONTROL, 0x00, 0x00)
    await test_decode_utf16(0x0000FFFF, READY, NONCHAR, 0xFF, 0xFF)
    await test_decode_utf16(0x00010000, READY, NORMAL|HIGHCHAR, 0xD8, 0x00, 0xDC, 0x00)
    await test_decode_utf16(0x0010FFFF, READY, NONCHAR|HIGHCHAR, 0xDB, 0xFF, 0xDF, 0xFF)
    await test_decode_utf16(0xDDD80000, UNDERFLOW, 0, 0xD8, 0x00, 0x00)
    await test_decode_utf16(0xDDDBFFFF, UNDERFLOW, 0, 0xDB, 0xFF, 0xFF)
    await test_decode_utf16(0xDDDDDD00, UNDERFLOW, 0, 0x00)
    await test_decode_utf16(0xDDDDDDFF, UNDERFLOW, 0, 0xFF)
    # not a high surrogate + a byte
    await test_decode_utf16(0x00000000, READY|RETRY|ERROR, CONTROL, 0x00, 0x00, 0xDD)
    await test_decode_utf16(0x0000FFFF, READY|RETRY|ERROR, NONCHAR, 0xFF, 0xFF, 0xDD)
    # not a high surrogate + a word
    await test_decode_utf16(0x00000000, READY|RETRY|ERROR, CONTROL, 0x00, 0x00, 0xDD, 0xDD)
    await test_decode_utf16(0x0000FFFF, READY|RETRY|ERROR, NONCHAR, 0xFF, 0xFF, 0xDD, 0xDD)
    # high surrogate + not a low surrogate
    await test_decode_utf16(0x0000D800, READY|RETRY|ERROR, SURROGATE|HIGHCHAR, 0xD8, 0x00, 0x00, 0x00)
    await test_decode_utf16(0x0000DB7F, READY|RETRY|ERROR, SURROGATE|HIGHCHAR, 0xDB, 0x7F, 0xFF, 0xFF)
    await test_decode_utf16(0x0000DB80, READY|RETRY|ERROR, SURROGATE|HIGHCHAR|PRIVATE, 0xDB, 0x80, 0x00, 0x00)
    await test_decode_utf16(0x0000DBFF, READY|RETRY|ERROR, SURROGATE|HIGHCHAR|PRIVATE, 0xDB, 0xFF, 0xFF, 0xFF)

    # UTF-8 to UTF-16

    async def test_utf8_to_utf16(u8, errs, props, u16):
        await write_bytes(*u8)
        await want_errs(errs)
        await want_props(props)
        await read_utf16(*u16)
        await write_reset()

    await test_utf8_to_utf16([0x00], READY, CONTROL, [0x00, 0x00])
    await test_utf8_to_utf16([0x7F], READY, CONTROL, [0x00, 0x7F])
    await test_utf8_to_utf16([0xC2, 0x80], READY, CONTROL, [0x00, 0x80])
    await test_utf8_to_utf16([0xDF, 0xBF], READY, NORMAL, [0x07, 0xFF])
    await test_utf8_to_utf16([0xE0, 0xA0, 0x80], READY, NORMAL, [0x08, 0x00])
    await test_utf8_to_utf16([0xEF, 0xBF, 0xBF], READY, NONCHAR, [0xFF, 0xFF])
    await test_utf8_to_utf16([0xF0, 0x90, 0x80, 0x80], READY, NORMAL|HIGHCHAR, [0xD8, 0x00, 0xDC, 0x00])
    await test_utf8_to_utf16([0xF4, 0x8F, 0xBF, 0xBF], READY, NONCHAR|HIGHCHAR, [0xDB, 0xFF, 0xDF, 0xFF])

    # UTF-16 to UTF-8

    async def test_utf16_to_utf8(u16, errs, props, u8):
        await write_utf16(*u16)
        await want_errs(errs)
        await want_props(props)
        await read_bytes(*u8)
        await write_reset()

    await test_utf16_to_utf8([0x00, 0x00], READY, CONTROL, [0x00])
    await test_utf16_to_utf8([0x00, 0x7F], READY, CONTROL, [0x7F])
    await test_utf16_to_utf8([0x00, 0x80], READY, CONTROL, [0xC2, 0x80])
    await test_utf16_to_utf8([0x07, 0xFF], READY, NORMAL, [0xDF, 0xBF])
    await test_utf16_to_utf8([0x08, 0x00], READY, NORMAL, [0xE0, 0xA0, 0x80])
    await test_utf16_to_utf8([0xFF, 0xFF], READY, NONCHAR, [0xEF, 0xBF, 0xBF])
    await test_utf16_to_utf8([0xD8, 0x00, 0xDC, 0x00], READY, NORMAL|HIGHCHAR, [0xF0, 0x90, 0x80, 0x80])
    await test_utf16_to_utf8([0xDB, 0xFF, 0xDF, 0xFF], READY, NONCHAR|HIGHCHAR, [0xF4, 0x8F, 0xBF, 0xBF])
