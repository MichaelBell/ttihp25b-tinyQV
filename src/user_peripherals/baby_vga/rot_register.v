`default_nettype none

module rot_register (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [3:0] data_in,
    input  wire       set_data,
    output wire [3:0] data_out
);

reg [31:0] data;

always @(posedge clk) begin
    if (!rst_n) begin
        data[31:28] <= 4'b0;
    end else if (set_data) begin
        data[31:28] <= data_in;
    end else begin
        data[31:28] <= data[3:0];
    end
    data[27:0] <= data[31:4];
end

assign data_out = data[31:28];

endmodule
