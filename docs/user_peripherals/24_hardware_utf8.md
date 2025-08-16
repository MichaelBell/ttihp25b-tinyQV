<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

The peripheral index is the number TinyQV will use to select your peripheral.  You will pick a free
slot when raising the pull request against the main TinyQV repository, and can fill this in then.  You
also need to set this value as the PERIPHERAL_NUM in your test script.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

# Hardware UTF Encoder/Decoder

Author: Rebecca G. Bettencourt

Peripheral index: 24

## What it does

This peripheral converts between the UTF‑8, UTF‑16, and UTF‑32 encodings for Unicode text.

It will detect and raise an error signal on overlong encodings, out of range code point values, and invalid byte sequences.

(You can optionally disable range checking if you wish to use the original UTF‑8 spec that supports values up to 0x7FFFFFFF.)

### Inputting UTF-32, method one

1. Write a value to register 0x00 according to the control register format: 0xFF for big-endian or 0xF7 for little-endian.
2. Write the four bytes of a UTF-32 code unit to register 0x01.
3. If READY (bit 0 of register 0x00) is HIGH and ERROR (bit 5 of register 0x00) is LOW, the input and output are both valid.
4. If READY (bit 0 of register 0x00) is LOW or ERROR (bit 5 of register 0x00) is HIGH, the input was out of range.

### Inputting UTF-32, method two

1. Write a value to register 0x00 according to the control register format: 0xFF for big-endian or 0xF7 for little-endian.
2. Write a UTF-32 code unit to registers 0x08-0x0B.
3. If READY (bit 0 of register 0x00) is HIGH and ERROR (bit 5 of register 0x00) is LOW, the input and output are both valid.
4. If READY (bit 0 of register 0x00) is LOW or ERROR (bit 5 of register 0x00) is HIGH, the input was out of range.

### Inputting UTF-16

1. Write a value to register 0x00 according to the control register format: 0xFF for big-endian or 0xF7 for little-endian.
2. Write the two bytes of a UTF-16 code unit to register 0x02.
3. If HIGHCHAR (bit 3 of register 0x01) is LOW, skip to step 5.
4. Write the two bytes of a UTF-16 code unit to register 0x02.
5. If READY (bit 0 of register 0x00) is HIGH and ERROR (bit 5 of register 0x00) is LOW, the input and output are both valid.
6. If RETRY (bit 1 of register 0x00) is HIGH, the first code unit was a high surrogate but the second code unit was not a low surrogate. The output will be the high surrogate only; the last code unit will need to be processed again.

### Inputting UTF-8

1. Write a value to register 0x00 according to the control register format: 0xFF for big-endian or 0xF7 for little-endian.
2. Write a UTF-8 byte to register 0x03.
3. Repeat step 2 until READY (bit 0 of register 0x00) or ERROR (bit 5 of register 0x00) is HIGH.
4. If READY (bit 0) is HIGH and ERROR (bit 5) is LOW, the input and output are both valid.
5. If RETRY (bit 1) is HIGH, the UTF‑8 sequence was truncated (not enough continuation bytes). The output will be the truncated sequence only; the last byte will need to be processed again.
6. If INVALID (bit 2) is HIGH, the UTF‑8 sequence was a single continuation byte or invalid byte (0xFE or 0xFF).
7. If OVERLONG (bit 3) is HIGH, the UTF‑8 sequence was an overlong encoding.
8. If NONUNI (bit 4) is HIGH, the UTF‑8 sequence was out of range.

### Outputting UTF-32, method one

1. Write a value to register 0x04 according to the control register format: 0xFF for big-endian or 0xF7 for little-endian.
2. Write any value to register 0x05.
3. Read the first byte of the UTF-32 code unit from register 0x05.
4. Write any value to register 0x05.
5. Read the second byte of the UTF-32 code unit from register 0x05.
6. Write any value to register 0x05.
7. Read the third byte of the UTF-32 code unit from register 0x05.
8. Write any value to register 0x05.
9. Read the fourth byte of the UTF-32 code unit from register 0x05.
10. If the UTF‑32 code unit is within range, the input and output are both valid.
11. If the UTF‑32 code unit is not within range, then the input was either incomplete or invalid.

### Outputting UTF-32, method two

1. Write a value to register 0x04 according to the control register format: 0xFF for big-endian or 0xF7 for little-endian.
2. Read the UTF-32 code unit from registers 0x08-0x0B.
3. If the UTF‑32 code unit is within range, the input and output are both valid.
4. If the UTF‑32 code unit is not within range, then the input was either incomplete or invalid.

### Outputting UTF-16

1. Write a value to register 0x04 according to the control register format: 0xFF for big-endian or 0xF7 for little-endian.
2. If UEOF (bit 7 of register 0x02) is HIGH, then the input was either incomplete or invalid.
3. Write any value to register 0x06.
4. Read the next byte of the UTF‑16 sequence from register 0x06.
5. Repeat steps 3 and 4 until UEOF (bit 7 of register 0x02) is HIGH.

### Outputting UTF-8

1. Write a value to register 0x04 according to the control register format: 0xFF for big-endian or 0xF7 for little-endian.
2. If BEOF (bit 7 of register 0x03) is HIGH, then the input was either incomplete or invalid.
3. Write any value to register 0x07.
4. Read the next byte of the UTF‑8 sequence from register 0x07.
5. Repeat steps 3 and 4 until BEOF (bit 7 of register 0x03) is HIGH.

## Register map

| Address | Name  | Access | Description                                                         |
|---------|-------|--------|---------------------------------------------------------------------|
| 0x00    | ERRS  | R      | Error state.                                                        |
| 0x01    | PROPS | R      | Character properties.                                               |
| 0x02    | ULEN  | R      | UTF-16 length.                                                      |
| 0x03    | BLEN  | R      | UTF-8 length.                                                       |
| 0x00    | RIN   | W      | Reset UTF input and output.                                         |
| 0x01    | CIN   | W      | Write a UTF-32 byte.                                                |
| 0x02    | UIN   | W      | Write a UTF-16 byte.                                                |
| 0x03    | BIN   | W      | Write a UTF-8 byte.                                                 |
| 0x04    | ROUT  | W      | Reset UTF output but not input.                                     |
| 0x05    | COUT  | W/R    | Write any value, then read the next UTF-32 byte.                    |
| 0x06    | UOUT  | W/R    | Write any value, then read the next UTF-16 byte.                    |
| 0x07    | BOUT  | W/R    | Write any value, then read the next UTF-8 byte.                     |
| 0x08    | RC0   | W/R    | Direct access to UTF-32 value.                                      |
| 0x09    | RC1   | W/R    | Direct access to UTF-32 value.                                      |
| 0x0A    | RC2   | W/R    | Direct access to UTF-32 value.                                      |
| 0x0B    | RC3   | W/R    | Direct access to UTF-32 value.                                      |

### Control register format

Used when writing to address 0x00 or 0x04.

| Bit | Mask | Name | Description                                                                |
|-----|------|------|----------------------------------------------------------------------------|
| 2   | 0x04 | CHK  | Range check. Set to 1 to restrict valid values to 0-0x10FFFF. Set to 0 to allow values up to 0x7FFFFFFF.
| 3   | 0x08 | CBE  | Endianness. Set to 1 for big endian. Set to 0 for little endian.

Other bits are reserved and should be set to 1.

### Error state format

Used when reading from address 0x00.

| Bit | Mask | Name     | Description                                                            |
|-----|------|----------|------------------------------------------------------------------------|
| 0   | 0x01 | READY    | The input and output are complete sequences.
| 1   | 0x02 | RETRY    | The previous input was invalid or the start of another sequence and was ignored. Process the output, reset, and try the previous input again.
| 2   | 0x04 | INVALID  | The input and output are invalid.
| 3   | 0x08 | OVERLONG | The UTF‑8 input was an overlong sequence.
| 4   | 0x10 | NONUNI   | The code point value is out of range (≥0x110000). (This is set independently of the CHK input; the CHK input only changes whether this counts as an error.)
| 5   | 0x20 | ERROR    | Equivalent to (RETRY or INVALID or OVERLONG or (NONUNI and CHK)).

### Character property format

Used when reading from address 0x01.

| Bit | Mask | Name      | Description                                                           |
|-----|------|-----------|-----------------------------------------------------------------------|
| 0   | 0x01 | NORMAL    | The code point value is valid and not a C0 or C1 control character, surrogate, private use character, or noncharacter.
| 1   | 0x02 | CONTROL   | The code point value is valid and a C0 or C1 control character (0x00-0x1F or 0x7F-0x9F).
| 2   | 0x04 | SURROGATE | The code point value is valid and a UTF‑16 surrogate (0xD800-0xDFFF).
| 3   | 0x08 | HIGHCHAR  | The code point value is valid and either a high surrogate (0xD800-0xDBFF) or a non-BMP character (≥0x10000).
| 4   | 0x10 | PRIVATE   | The code point value is valid and either a private use character (0xE000-0xF8FF, ≥0xF0000) or the high surrogate of a private use character (0xDB80-0xDBFF).
| 5   | 0x20 | NONCHAR   | The code point value is valid and a noncharacter (0xFDD0-0xFDEF or the last two code points of any plane).

### Length format

Used when reading from address 0x02 or 0x03.

| Bit | Mask | Name | Description                                                                |
|-----|------|------|----------------------------------------------------------------------------|
| 0-2 | 0x07 | LEN  | Number of bytes.                                                           |
| 7   | 0x80 | EOF  | Set if the maximum number of bytes has been read.                          |
