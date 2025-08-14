`default_nettype none

`define NUM_REGS 16
`define ADDR_BITS 4

module rot_register_file (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire [`ADDR_BITS-1:0] r1_addr,
    input  wire [`ADDR_BITS-1:0] r2_addr,
    input  wire [`ADDR_BITS-1:0] w_addr,
    input  wire            [3:0] data_in,
    input  wire                  set_data,
    output wire            [3:0] data_out1,
    output wire            [3:0] data_out2
);

wire [3:0] rr_data_out [`NUM_REGS-1:0];

generate genvar i;
    for (i=0; i<`NUM_REGS; i=i+1) begin : rreg
        rot_register rr (
            .clk,
            .rst_n,
            .data_in,
            .set_data(set_data & (w_addr == i)),
            .data_out(rr_data_out[i])
        );
    end
endgenerate

assign data_out1 = rr_data_out[r1_addr];
assign data_out2 = rr_data_out[r2_addr];

endmodule
