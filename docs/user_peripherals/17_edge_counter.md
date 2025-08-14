# Edge Counter

Author: Uri Shaked

Peripheral index: 17

## What it does

Edge counter peripheral for TinyQV that counts the number of edges on selected ui_in pins.

If you select multiple pins, the counter will increase by 1 whenever an edge is detected on any of those pins. However, even if edges occur on several selected pins at the same time (within the same clock cycle), the counter will only increment once per clock cycle.

The lower 4 bits of the counter are displayed on the 7-segment display. The DP is lit when the counter is greater than 0x0F.

## Register map

| Address | Name  | Access | Description                                                         |
|---------|-------|--------|---------------------------------------------------------------------|
| 0x00    | RESET | W      | Resets the counter to 0                                             |
| 0x01    | INC   | W      | Increments the counter by 1                                         |
| 0x02    | VALUE | R/W    | Reads the current value of the counter                              |
| 0x03    | CFG   | R/W    | Edge detection configuration: 0 = disabled, 1 = rising, 2 = falling |
| 0x04    | PINS  | R/W    | Bitmask of ui_in pins to count edges on (0x1 on reset)              |

## How to test

1. Set the pins to count edges on in the PINS register.
2. Set the edge detection configuration in the CFG register.
3. Pulse an edge on the selected pins.
4. The counter will increment by 1 for each edge detected.
5. The counter value is displayed on the 7-segment display.

