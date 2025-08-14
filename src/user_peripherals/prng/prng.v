/*
 * Copyright (c) 2025 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

// Change the name of this module to something that reflects its functionality and includes your name for uniqueness
// For example tqvp_yourname_spi for an SPI peripheral.
// Then edit tt_wrapper.v line 41 and change tqvp_example to your chosen module name.
module tqvp_cattuto_xoshiro128plusplus_prng (
    input         clk,          // Clock - the TinyQV project clock is normally set to 64MHz.
    input         rst_n,        // Reset_n - low to reset.

    input  [7:0]  ui_in,        // The input PMOD, always available.  Note that ui_in[7] is normally used for UART RX.
                                // The inputs are synchronized to the clock, note this will introduce 2 cycles of delay on the inputs.

    output [7:0]  uo_out,       // The output PMOD.  Each wire is only connected if this peripheral is selected.
                                // Note that uo_out[0] is normally used for UART TX.

    input [5:0]   address,      // Address within this peripheral's address space
    input [31:0]  data_in,      // Data in to the peripheral, bottom 8, 16 or all 32 bits are valid on write.

    // Data read and write requests from the TinyQV core.
    input [1:0]   data_write_n, // 11 = no write, 00 = 8-bits, 01 = 16-bits, 10 = 32-bits
    input [1:0]   data_read_n,  // 11 = no read,  00 = 8-bits, 01 = 16-bits, 10 = 32-bits
    
    output [31:0] data_out,     // Data out from the peripheral, bottom 8, 16 or all 32 bits are valid on read when data_ready is high.
    output        data_ready,

    output        user_interrupt  // Dedicated interrupt request for this peripheral
);

    xoshiro128plusplus xoshiro128plusplus_inst (
        .clk(clk),
        .rst_n(rst_n),
        .rnd(rnd),
        .next(rnd_next),
        .write(seed_write),
        .write_addr(seed_addr),
        .write_data(seed_data)
    );

    wire [31:0] rnd;
    reg rnd_next;

    wire [1:0] seed_addr;
    assign seed_addr = address[1:0] - 1;

    wire [31:0] seed_data;
    assign seed_data = data_in;

    // driven high iff 0x01 <= address <= 0x04 and host is writing a 32-bit word
    wire seed_write;
    assign seed_write = ((address > 0) && (address <= 4) && (data_write_n == 2'b10)) ? 1 : 0;

    always @(posedge clk) begin
        if (!rst_n) begin
            rnd_next <= 1;
        end else begin
            // if reading a 32-bit word from register 0x00, trigger computation of next state
            if ((address == 6'h0) && (data_read_n == 2'b10) && !rnd_next) begin
                rnd_next <= 1;
            end else begin
                rnd_next <= 0;
            end
        end
    end

    // Address 0 reads the current pseudorandom word.  
    // All other addresses read 0.
    assign data_out = (address == 6'h0) ? rnd : 32'h0;

    // All reads complete in 1 clock
    assign data_ready = 1;
    
    assign uo_out = 0;
    assign user_interrupt = 0;

    // List all unused inputs to prevent warnings
    wire _unused = &{ui_in, 1'b0};

endmodule
