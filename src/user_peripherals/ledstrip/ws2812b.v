module ws2812b (
    input wire clk,               // 64 MHz input clock
    input wire rst_n,
    input wire [23:0] data_in,    // color data
    input wire valid,
    input wire latch,
    output reg ready,
    output reg led                // output signal to LED strip
);

  localparam CLOCK_HZ = 64_000_000;
  localparam NS_PER_S = 1_000_000_000;

  function [15:0] cycles_from_ns;
  input [31:0] ns;     // argument in ns
  reg   [63:0] num;    // wide intermediate
  reg   [63:0] q64;
  begin
    num = (64'd64_000_000 * ns) + 64'd500_000_000;
    q64 = num / 64'd1_000_000_000;
    cycles_from_ns = q64[15:0];
  end
  endfunction

  // Define timing parameters according to WS2812B datasheet
  localparam T0H = 400;             // width of '0' high pulse (400 ns)
  localparam T1H = 800;             // width of '1' high pulse (800 ns)
  localparam T0L = 850;             // width of '0' low pulse (850 ns)
  localparam T1L = 450;             // width of '1' low pulse (450 ns)
  localparam PERIOD = 1250;         // total period of one bit (1250 ns)
  localparam RES_DELAY = 325_000;   // reset duration (325 us)

  // Calculate clock cycles for each timing parameter
  localparam [15:0] CYCLES_PERIOD = cycles_from_ns(PERIOD);
  localparam [15:0] CYCLES_T0H = cycles_from_ns(T0H);
  localparam [15:0] CYCLES_T1H = cycles_from_ns(T1H);
  localparam [15:0] CYCLES_T0L = cycles_from_ns(PERIOD - T0H);
  localparam [15:0] CYCLES_T1L = cycles_from_ns(PERIOD - T1H);
  localparam [15:0] CYCLES_RESET = cycles_from_ns(RES_DELAY);

  // state machine
  parameter IDLE = 0, START = 1, SEND_BIT = 2, RESET = 3;
  reg [1:0] state;

  reg [4:0] bitpos;
  reg [15:0] time_counter;
  reg [23:0] data;
  reg will_latch;

  // State machine logic
  always @(posedge clk) begin
    if (!rst_n) begin
      state <= RESET;
      bitpos <= 0;
      time_counter <= 0;
      led <= 0;
      ready <= 0;
      data <= 24'b0;
      will_latch <= 0;
    end else begin
      case (state)
        IDLE: begin
          bitpos <= 0;
          time_counter <= 0;
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
          bitpos <= 23;
          time_counter <= 0;
          led <= 1;
          ready <= 0;
        end

        SEND_BIT: begin
          if (time_counter < CYCLES_PERIOD - 1) begin
            // Continue sending current bit
            time_counter <= time_counter + 1;
            if (time_counter == (data[bitpos] ? (CYCLES_T1H - 1) : (CYCLES_T0H - 1)))
                led <= 0;
          end else if (bitpos > 0) begin
            // Move to next bit
            bitpos <= bitpos - 1;
            time_counter <= 0;
            led <= 1;
          end else begin
            // All bits sent
            state <= will_latch ? RESET : IDLE;
            will_latch <= 0;
            time_counter <= 0;
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
            time_counter <= 0;
          end
        end

        default: begin
          state <= RESET;
          bitpos <= 0;
          time_counter <= 0;
          led <= 0;
          ready <= 0;
          data <= 24'b0;
          will_latch <= 0;
        end
      endcase
    end
  end

endmodule
