module ws2812b #(parameter CLOCK_MHZ=64) (
    input wire clk,               // 64 MHz input clock
    input wire rst_n,
    input wire [23:0] data_in,    // color data
    input wire valid,
    input wire latch,
    output reg ready,
    output reg led                // output signal to LED strip
);

  localparam [63:0] CLOCK_HZ = CLOCK_MHZ * 1_000_000;
  localparam [63:0] NS_PER_S = 1_000_000_000;

  // Define timing parameters according to WS2812B datasheet
  localparam T0H_NS = 400;            // width of '0' high pulse (400 ns)
  localparam T1H_NS = 800;            // width of '1' high pulse (800 ns)
  localparam T0L_NS = 850;            // width of '0' low pulse (850 ns)
  localparam T1L_NS = 450;            // width of '1' low pulse (450 ns)
  localparam PERIOD_NS = 1250;        // total period of one bit (1250 ns)
  localparam RES_DELAY_NS = 325_000;  // reset duration (325 us)

  `define CYCLES_FROM_NS(_NSVAL) \
  ( ((CLOCK_HZ * (64'd0 + _NSVAL)) + (NS_PER_S /2)) / NS_PER_S )

  // Calculate clock cycles for each timing parameter
  localparam [63:0] CYCLES_PERIOD_U = `CYCLES_FROM_NS(PERIOD_NS);
  localparam [63:0] CYCLES_T0H_U =    `CYCLES_FROM_NS(T0H_NS);
  localparam [63:0] CYCLES_T1H_U =    `CYCLES_FROM_NS(T1H_NS);
  localparam [63:0] CYCLES_T0L_U =    `CYCLES_FROM_NS(PERIOD_NS - T0H_NS);
  localparam [63:0] CYCLES_T1L_U =    `CYCLES_FROM_NS(PERIOD_NS - T1H_NS);
  localparam [63:0] CYCLES_RESET_U =  `CYCLES_FROM_NS(RES_DELAY_NS);

  localparam [15:0] CYCLES_PERIOD =   CYCLES_PERIOD_U[15:0];
  localparam [15:0] CYCLES_T0H    =   CYCLES_T0H_U[15:0];
  localparam [15:0] CYCLES_T1H    =   CYCLES_T1H_U[15:0];
  localparam [15:0] CYCLES_T0L    =   CYCLES_T0L_U[15:0];
  localparam [15:0] CYCLES_T1L    =   CYCLES_T1L_U[15:0];
  localparam [15:0] CYCLES_RESET  =   CYCLES_RESET_U[15:0];

  // state machine
  parameter IDLE = 2'd0, START = 2'd1, SEND_BIT = 2'd2, RESET = 2'd3;
  reg [1:0] state;

  reg [4:0] bitpos;
  reg [15:0] time_counter;
  reg [23:0] data;
  reg will_latch;

  // State machine logic
  always @(posedge clk) begin
    if (!rst_n) begin
      state <= RESET;
      bitpos <= 5'd0;
      time_counter <= 16'd0;
      led <= 0;
      ready <= 0;
      data <= 24'd0;
      will_latch <= 0;
    end else begin
      case (state)
        IDLE: begin
          bitpos <= 5'd0;
          time_counter <= 16'd0;
          led <= 0;
          if (ready && valid) begin
            data <= data_in;
            will_latch <= latch;
            ready <= 0;
            state <= START;
          end else begin
            ready <= 1;
          end
        end

        START: begin
          // Initialize for sending data
          state <= SEND_BIT;
          bitpos <= 5'd23;
          time_counter <= 16'd0;
          led <= 1;
          ready <= 0;
        end

        SEND_BIT: begin
          if (time_counter < CYCLES_PERIOD - 1) begin
            // Continue sending current bit
            time_counter <= time_counter + 1;
            if (time_counter == (data[bitpos] ? (CYCLES_T1H - 1) : (CYCLES_T0H - 1))) begin
                led <= 0;
            end
          end else if (bitpos > 0) begin
            // Move to next bit
            bitpos <= bitpos - 1;
            time_counter <= 16'd0;
            led <= 1;
          end else begin
            // All bits sent
            state <= will_latch ? RESET : IDLE;
            will_latch <= 0;
            time_counter <= 16'd0;
            led <= 0;
          end
        end

        RESET: begin
          if (time_counter < CYCLES_RESET) begin
            // Continue reset pulse
            time_counter <= time_counter + 1;
          end else begin
            // Reset complete, return to idle
            state <= IDLE;
            time_counter <= 16'd0;
          end
        end

        default: begin
          state <= RESET;
          bitpos <= 5'd0;
          time_counter <= 16'd0;
          led <= 0;
          ready <= 0;
          data <= 24'd0;
          will_latch <= 0;
        end
      endcase
    end
  end

endmodule
