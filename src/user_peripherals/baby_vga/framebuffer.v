`default_nettype none

`define ADDR_BITS 4

module framebuffer (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire            [2:0] counter,
    input  wire [`ADDR_BITS-1:0] r1_addr,
    input  wire [`ADDR_BITS-1:0] r2_addr,
    input  wire [`ADDR_BITS-1:0] w_addr,
    input  wire           [31:0] data_in,
    input  wire                  set_data,
    output reg            [31:0] data_out1,
    output reg            [31:0] data_out2
);

reg [`ADDR_BITS-1:0] w_addr_saved;
reg [31:0] data_in_saved;
reg [2:0] w_index;
reg [3:0] data_in_frag;
reg set_data_reg;
wire [3:0] data_out1_frag;
wire [3:0] data_out2_frag;

wire [2:0] counter_shifted = counter + 2;

rot_register_file rrf (
    .clk,
    .rst_n,
    .r1_addr,
    .r2_addr,
    .w_addr(w_addr_saved),
    .data_in(data_in_frag),
    .set_data(set_data_reg),
    .data_out1(data_out1_frag),
    .data_out2(data_out2_frag)
);

always @(posedge clk) begin
    if (set_data) begin
        data_in_saved <= data_in;
        w_addr_saved <= w_addr;
        w_index <= 3'b1;
        data_in_frag <= data_in[{counter_shifted, 2'b00} +: 4];
        set_data_reg <= 1'b1; 
    end else if (w_index != 0) begin
        w_index <= w_index + 1;
        data_in_frag <= data_in_saved[{counter_shifted, 2'b00} +: 4];
        set_data_reg <= 1'b1;
    end else begin
        set_data_reg <= 1'b0;
    end
    data_out1[{counter, 2'b00} +: 4] <= data_out1_frag;
    data_out2[{counter, 2'b00} +: 4] <= data_out2_frag;
end

endmodule
