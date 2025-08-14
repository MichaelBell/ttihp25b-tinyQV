<!---
This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

# PWM

Author: Sujith Kani A.

Peripheral index: 20

## What it does

This project implements a simple 8-bit Pulse Width Modulation (PWM) peripheral, designed as a memory-mapped device for integration with a RISC-V SoC in the TinyTapeout ecosystem.

It allows the user to set a duty cycle via a single register. The peripheral compares an internal 8-bit counter with the programmed duty cycle value and drives `uo_out[0]` high whenever the counter is less than the duty cycle, and low otherwise. This behavior creates a repeating PWM signal that can be used to control brightness, speed, or other analog-like control signals.

The design is minimal, fully synthesizable, and compatible with the TinyQVP peripheral interface.

---

## Register map

| Address | Name       | Access | Description                                  |
|---------|------------|--------|----------------------------------------------|
| 0x00    | DUTY_CYCLE | R/W    | Sets the 8-bit PWM duty cycle (0–255)        |

- **Write**: Writing to address `0x00` updates the duty cycle register.
- **Read**: Reading from address `0x00` returns the current duty cycle.

---

## How to test

This peripheral is tested using a Cocotb testbench with the TinyQVP simulation infrastructure.

### To run the test locally:

```bash
cd test
make results.xml
