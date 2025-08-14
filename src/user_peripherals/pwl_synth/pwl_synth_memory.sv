/*
 * Copyright (c) 2025 Toivo Henningsson
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
`include "pwl_synth.vh"

`ifdef USE_LATCHES

module pwls_shared_data #(parameter BITS=16) (
		input wire clk, reset,
		input wire [BITS-1:0] in,
		output wire [BITS-1:0] out
	);
	genvar i;

	wire [BITS-1:0] data_in = reset ? '0 : in;
	generate
		for (i = 0; i < BITS; i++) begin
			sky130_fd_sc_hd__dlxtn_1 n_latch(.GATE_N(clk), .D(data_in[i]), .Q(out[i]));
		end
	endgenerate
endmodule : pwls_shared_data

module pwls_register #(parameter BITS=16) (
		input wire clk, reset,
		input wire we,
		input wire [BITS-1:0] wdata,
		output wire [BITS-1:0] rdata
	);
	genvar i;

	wire gclk;
	sky130_fd_sc_hd__dlclkp_1 clock_gate(.CLK(clk), .GATE(we || reset), .GCLK(gclk));

	generate
		for (i = 0; i < BITS; i++) begin
			sky130_fd_sc_hd__dlxtp_1 p_latch(.GATE(gclk), .D(wdata[i]), .Q(rdata[i]));
		end
	endgenerate
endmodule

`else // not USE_LATCHES

module pwls_shared_data #(parameter BITS=16) (
		input wire clk, reset,
		input wire [BITS-1:0] in,
		output wire [BITS-1:0] out
	);
	assign out = in;
endmodule : pwls_shared_data

module pwls_register #(parameter BITS=16) (
		input wire clk, reset,
		input wire we,
		input wire [BITS-1:0] wdata,
		output wire [BITS-1:0] rdata
	);
	reg [BITS-1:0] data;
	always_ff @(posedge clk) begin
		if (reset) data <= 0;
		else if (we) data <= wdata;
	end
	assign rdata = data;
endmodule

`endif
