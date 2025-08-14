<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 KB in size, and the combined size of all images must be less than 1 MB.
-->

# Spike_Encoder Pheriphral

Author: Riya & Anoushka 

Peripheral index: 22

## What it does

This peripheral implements a spike encoder that detects rapid changes in pixel intensity values.
It compares each new pixel value to the previous one and generates a spike event if the absolute difference exceeds a configurable threshold.
The spike event is output on uo_out[0] and also reflected in the SPI-accessible status register.
The module keeps track of the total number of spikes detected since reset, which can be read via the count register.
This design is useful for lightweight event-driven image processing or neuromorphic systems, where only significant changes in input intensity are relevant.

## Register map

Document the registers that are used to interact with your peripheral

| Address | Name      | Access | Description                                                            |
| ------- | --------- | ------ | ---------------------------------------------------------------------- |
| 0x00    | PIXEL     | W/R    | Current pixel intensity (write new value; read back last written)      |
| 0x01    | THRESHOLD | W/R    | Threshold for edge detection (default = 20)                            |
| 0x02    | SPIKE     | R      | Bit0 = Spike detected (1 = spike event, 0 = no spike)                  |
| 0x03    | COUNT     | R      | Total spike count since last reset (increments on each detected spike) |


## How to test

Run the testbench:

1. Make all :
Inspect tb.vcd waveform in GTKWave to verify:
Spike output pulses when pixel changes exceed the threshold.
COUNT register increments correctly.

2. On silicon :
Write pixel data via SPI register 0x00.
Set threshold via SPI register 0x01.
Read status (0x02) to check for spike events.
Read count (0x03) to monitor total spikes detected.

3. Expected behavior:
When pixel difference ≥ threshold → spike event (uo_out[0] = 1) and count increments.
When difference < threshold → no spike (uo_out[0] = 0).


