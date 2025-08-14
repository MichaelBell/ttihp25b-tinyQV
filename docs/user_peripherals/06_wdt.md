# WatchDog Timer

Author: Niklas Anderson

Peripheral index: 06

## What it does

The watchdog timer (WDT) peripheral provides a mechanism to detect software lockups or system hangs. Once started, it begins counting down from a configured value. If the countdown reaches zero without being "tapped", the WDT asserts an interrupt (`user_interrupt`) to signal a system fault.

A tap entails writing a specified value (0xABCD) to address 0x3. This is designed to reduce the likelihood of an inadvertent clearing of the interrupt due to corrupt or misbehaving signals. Besides the tap action, only a reset will clear the interrupt.

## Register map

| Address | Name       | Access | Description                                                                 |
|---------|------------|--------|-----------------------------------------------------------------------------|
|  0x00  | ENABLE     | W      | Write 1 to enable the watchdog, 0 to disable. Does not clear timeout.       |
|  0x04  | START      | W      | Starts the watchdog (also enables). Has no effect if countdown = 0.         |
|  0x08  | COUNTDOWN  | R/W    | Sets or reads the countdown value (in clock cycles). 8/16/32-bit writes allowed. |
|  0x0C  | TAP        | W      | Write 0xABCD to reset countdown and clear timeout, only if enabled and started. |
|  0x10  | STATUS     | R      | Bit 0: enabled, Bit 1: started, Bit 2: timeout_pending, Bit 3: counter active |


## How to test

The WDT is configured and interacted with through memory-mapped registers using byte/half-word/word writes, with countdown resolution based on the system clock (typically 64 MHz). Configuration on system startup requires writing a countdown value to the peripheral, then starting the counter by writing to the start address. The countdown begins immediately, and proceeds until reaching zero or receiving the correct pre-specified value (0xABCD) at the tap address. If the countdown reaches zero before receiving a valid tap, the `user_interrupt` signal is asserted. If a valid tap is recieved, the countdown is restarted and any existing interrupt is de-asserted.

The timer may be disabled by writing a 0 to the enable address. When re-starting the timer by writing to the start address, the counter is reset to the saved countdown value. If no countdown value has been set, the timer will not start.

A typical test covering standard expected functionality should include:
- Bring the `rst_n` reset signal low
- Write a countdown value in clock ticks to the countdown address (0x2)
- Write any value to the start address (0x1)
- Write the tap value 0xABCD to the tap address (0x3) before the number of clock cycles previously set has elapsed
- Confirm that the `user_interrupt` signal has not been asserted
- Continue writing to the tap address in order to prevent or clear the interrupt

Tests using the `tt_um_tqv_peripheral_harness.v` may be run with the following command:
```sh
make -B
```

Examples of possible countdown values include the following, assuming a 64MHz clock frequency (15.625ns clock period):
|  Time  |  Hex Value  |
|--------|-------------|
|  10ms  |  0x0009C400 |
|    1s  |  0x03D09000 |
|   60s  |  0xE4E1C000 |

## External hardware

None
