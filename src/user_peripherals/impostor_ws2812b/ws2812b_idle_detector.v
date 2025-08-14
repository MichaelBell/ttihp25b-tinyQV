

module ws2812b_idle_detector (
    input  wire        clk,
    input  wire        reset,
    input  wire        din,
    input  wire [15:0] idle_threshold_ticks,  // dynamic threshold in clock cycles
    output reg         idle
);

    reg [15:0] idle_counter;

    always @(posedge clk) begin
        if (reset) begin
            idle_counter <= 0;
            idle <= 0;
        end else if (din == 1'b1) begin
            idle_counter <= 0;
            idle <= 0;
        end else begin
            if (idle_counter < idle_threshold_ticks)
                idle_counter <= idle_counter + 1;
            else
                idle <= 1;
        end
    end
    
endmodule
