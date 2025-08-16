// Copyright (c) Ken Pettit
// SPDX-License-Identifier: Apache-2.0
// ------------------------------------------------------------------------------
//
//  File        : prism.sv
//  Revision    : 1.2
//  Author      : Ken Pettit
//  Created     : 05/09/2015
//
// ------------------------------------------------------------------------------
//
// Description:  
//    This is a Programmable Reconfigurable Indexed State Machine (PRISM)
//
//                        /\           
//                       /  \           
//                   ..-/----\-..       
//               --''  /      \  ''--   
//                    /________\        
//
// Modifications:
//
//    Author  Date      Rev  Description
//    ======  ========  ===  ================================================
//    KP      05/09/15  1.0  Initial version
//    KP      12/07/17  1.1  Modified the input stage to use muxed inputs
//                           with config space select bits, added AND/OR/XOR
//                           and invert capability, added dual compare logic,
//                           added state transition outputs and conditional
//                           outputs, added SI loop mode when si_inc active.
//    KP      12/13/17  1.2  Added Reconfigurability / Fracturability.
//
// ------------------------------------------------------------------------------


/*
=====================================================================================

    Theory of operation:
                                                                        
    +-------------+     +--------------------------------------------------+
    |   Current   |  5  | State Information Table (SIT)                    |
    | State Index +--/->|                                                  |
    |    (SI)     |     | Output: STate Execution Word (STEW)              |
    +-------------+     ++--------+---------+--------------+-+-------------+
         ^ Next SI       |        |LUT      |NewSI         | |
         |               |        |Data     |              | | Transition
         |               |        |(16)     | 5  |\        | |   Outputs     |\  
         |     Input     |        |         +-/->|1|       | +-------------->|1| Output Values
         |     Select    |        |              | +----+  |  State Outputs  | +--------------> 
         |     Muxes (4) |        v    CurrSI -->|0|    |  +---------------->|0|
         |           -->|\      +-------+        |/     |                    |/ 
         |            o | |  3  |       |         |     |                     |
         |    Inputs  o | +--/->|  LUT  +---------*-----|---------------------+
         |            o | |     |       | New State?    |                   
         |           -->|/      +-------+               |
         |                                              |
         +----------------------------------------------+
                                                
    1.  The current State Index (SI) is used as the address to a RAM (State Information Table - SIT)                                            
    2.  The RAM output word is the STate Execution Word (STEW).
    3.  While in the current state (SI), output values are driven from STEW bits.
    4.  Four (4) inputs are MUXed from the 32 available via STEW bits and sent to the LUT.
    5.  The 4-input LUT is programmed from 16 STEW bits to give a "Goto New State?" decision.
    6.  If the LUT output is HIGH, the FSM goes to the NewSI (from the STEW) state.
    7.  During a transition to a NewSI state, the output values are driven with "Transition" values.
    8.  Also (not shown) are a limited number of Conditional Outputs. In any given state, a 
        conditional output will be determined only by the input values base on a LUT.
    9.  The PRISM is Fracturable, meaning it can be fractured into two (somewhat) independent shards
        (state machines), each with it's own SI.  The SI[0] FSM will have 1/2 of the states and
        the SI[1] will have the remainder (on a power of 2 basis).  If there were 24 states, then:

           SI[0] - 16 states
           SI[1] - 8  states
                                                                                         
    10. In the fractured mode, there are output mask bit registers that assign
        outputs to specific shard. 
    11. The FSM (or each shard) can be debugged.  There are 2 breakpoints for each
        that stop the FSM at a specified state.  Also, the FSM can be halted via
        register interface and single stepped.
=====================================================================================
*/
module prism
 #(
   parameter  DEPTH          = 8,                  // Total number of available states
   parameter  INPUTS         = 16,                 // Total number of Input to the module
   parameter  OUTPUTS        = 12,                 // Nuber of FSM outputs
   parameter  COND_OUT       = 1,                  // Number of conditional outputs
   parameter  COND_LUT_SIZE  = 1,                  // Size (inputs) for COND decision tree LUT
   parameter  STATE_INPUTS   = 3,                  // Number of parallel state input muxes
   parameter  DUAL_COMPARE   = 0,
   parameter  LUT_SIZE       = 2,
   parameter  INCLUDE_DEBUG  = 1,
   parameter  SI_BITS        = DEPTH > 32 ? 6 :
                               DEPTH > 16 ? 5 :
                               DEPTH > 8  ? 4 :
                               DEPTH > 4  ? 3 :
                               DEPTH > 2  ? 2 : 1,
   parameter  INPUT_BITS     = INPUTS > 32 ? 6 :
                               INPUTS > 16 ? 5 :
                               INPUTS > 8  ? 4 :
                               INPUTS > 4  ? 3 :
                               INPUTS > 2  ? 2 : 1,
   parameter  COND_LUT_BITS  = 2**COND_LUT_SIZE,
   parameter  RAM_WIDTH      = STATE_INPUTS   * INPUT_BITS       + // Input mux sel bits
                               (2**LUT_SIZE)  * (DUAL_COMPARE+1) + // AND/OR Invert per jump state
                               SI_BITS        * (DUAL_COMPARE+1) + // JumpTo state bits
                               OUTPUTS        * (DUAL_COMPARE+2) + // Output Bits 
                               COND_LUT_BITS  * COND_OUT         + // Conditional output bits
                               1,                                  // Increment bit
   parameter  W_ADDR         = 6
  )
  (
   // Timing inputs
   input   wire                  clk,              // System clock 
//   input   wire                  clk_div2,         // System clock / 2
   input   wire                  rst_n,            // TRUE when receiving Bit 0
//   input   wire                  debug_reset,
   input   wire                  fsm_enable,       // Enable signal

   // Symbol and other state detect inputs
   input   wire [INPUTS-1:0]     in_data,          // The input data

   // Output data
   output  wire [OUTPUTS-1:0]    out_data,         // Bit Slip pulse back to SerDes
   output  wire [COND_OUT-1:0]   cond_out,         // Conditional outputs

   // ============================
   // Latch programming bus
   // ============================
`ifndef SYNTH_FPGA
   input  wire [31:0]            latch_data,
   input  wire                   latch_wr,
`endif

   // ============================
   // Debug bus for programming
   // ============================
   input  wire [W_ADDR-1:0]      debug_addr,         // Debug address
   input  wire                   debug_wr,           // Active HIGH write strobe
   input  wire [31:0]            debug_wdata,        // Debug write data
   output wire [31:0]            debug_rdata,        // Debug read data
   output wire                   debug_halt_either
  );

   localparam W_PAR_IN    = INPUT_BITS;
   localparam RA_BITS     = DEPTH > 256 ? 9 : DEPTH > 128 ? 8 : DEPTH > 64 ? 7 :
                            DEPTH >  32 ? 6 : DEPTH > 16  ? 5 : DEPTH > 8 ? 4 : 
                            DEPTH >  4 ? 3 : 2;
   localparam CMP_SEL_SIZE= 2**LUT_SIZE;
   localparam W_DBG_CTRL  = SI_BITS*2 + 4;
   localparam RAM_DEPTH   = DEPTH;

   wire                       prism_rst_n;

   // Signal declarations
   reg   [SI_BITS-1:0]        curr_si;         // Current State Index value
   wire  [SI_BITS-1:0]        next_si;         // Next State Index value
   reg   [SI_BITS-1:0]        loop_si;         // Loop State Index value
   reg                        loop_valid;      // Indiactes if loop_si value is valid
   reg   [SI_BITS-1:0]        debug_si;        // Current State Index value

   // Signals to create parallel input muxes
   wire  [W_PAR_IN-1:0]       input_mux_sel [ STATE_INPUTS-1:0 ];
   wire                       input_mux_out_c [ STATE_INPUTS-1:0 ];
   wire                       input_mux_out   [ STATE_INPUTS-1:0 ];

   // RAM interface signals for output values
   wire  [OUTPUTS-1:0]        state_outputs ;                // Output values from RAM
   wire  [OUTPUTS-1:0]        jump_outputs  [ DUAL_COMPARE:0 ]; // Jumpto transition Output values

   // RAM interface signals for SI control
   wire  [SI_BITS-1:0]        jump_to [ DUAL_COMPARE:0 ];    // SI Jump to address
   wire                       inc_si ;                       // SI Inc signal

   // Compare signals from RAM
   wire  [CMP_SEL_SIZE-1:0]   cmp_sel [ DUAL_COMPARE:0 ];
		
   // Signals for doing input compare and muxing
   wire  [DUAL_COMPARE:0]     compare_match;

   // Conditional out control signals
   wire  [COND_LUT_BITS-1:0]  cond_cfg    [ COND_OUT-1:0 ];
   wire                       cond_in     [ COND_OUT-1:0 ];
   wire                       cond_out_c  [ COND_OUT-1:0 ];
   wire                       cond_out_m  [ COND_OUT-1:0 ];

   // Output data masking
   wire  [OUTPUTS-1:0]        out_data_c  ;
   wire  [OUTPUTS-1:0]        out_data_m  ;
   wire  [OUTPUTS-1:0]        out_data_fsm;        // FSM outputs
   
   // Memory control signals
   wire  [RAM_WIDTH-1:0]      ram_dout;
   wire  [RA_BITS-1:0]        ram_raddr1;
   wire  [RAM_WIDTH-1:0]      stew;               // State Execution Word

   // PRISM readback data (SI, etc.)
   reg  [31:0]                debug_rdata_prism;  // Peripheral read data

   // Debug control register
   wire [W_DBG_CTRL-1:0]      debug_ctrl0;
   wire                       debug_ctrl0_en;
   wire                       debug_halt_req;
   wire                       debug_step_si;
   wire                       debug_bp_en0;
   wire                       debug_bp_en1;
   wire  [SI_BITS-1:0]        debug_bp_si0;
   wire  [SI_BITS-1:0]        debug_bp_si1;
   wire                       debug_new_si;
   wire  [SI_BITS-1:0]        debug_new_siv;
   wire                       debug_entry;

   // Debug control regs
   reg                        debug_halt;
   reg                        debug_step_pending;
   reg                        debug_resume_pending;
   reg                        debug_halt_req_p1;
   reg                        debug_step_si_last;
   reg  [1:0]                 debug_break_active;
   reg  [31:0]                decision_tree_data;  // Peripheral read data

   /* 
   =================================================================================
	Generate Section for RAM State Information Table (SIT)
   =================================================================================
   */

   wire [31:0]             debug_rdata_ram;  // Peripheral read data

   assign prism_rst_n = rst_n & fsm_enable;//~debug_reset;

   // Instantiate the Latch based SIT
`ifndef SYNTH_FPGA
   prism_latch_sit
   #(
      .WIDTH   ( RAM_WIDTH     ),
      .DEPTH   ( RAM_DEPTH     )
    )
   prism_latch_sit_i
   (
      .clk                   ( clk              ),
      .rst_n                 ( rst_n            ),
                                                        
      // Latch bus
      .latch_data            ( latch_data       ),
      .latch_wr              ( latch_wr         ),

      // Periph bus interface                           
      .debug_addr            ( debug_addr       ),
      .debug_rdata           ( debug_rdata_ram  ),
      .debug_wr              ( debug_wr         ),
                                                       
      // PRISM interface                               
      .raddr1                ( ram_raddr1       ),
      .rdata1                ( ram_dout         )
   );
`else
   prism_sr_sit
   #(
      .WIDTH   ( RAM_WIDTH     ),
      .DEPTH   ( RAM_DEPTH     )
    )
   prism_latch_sit_i
   (
      .clk                   ( clk              ),
      .rst_n                 ( rst_n            ),
                                                        
      // Periph bus interface                           
      .debug_addr            ( debug_addr       ),
      .debug_rdata           ( debug_rdata_ram  ),
      .debug_wdata           ( debug_wdata      ),
      .debug_wr              ( debug_wr         ),
                                                       
      // PRISM interface                               
      .raddr1                ( ram_raddr1       ),
      .rdata1                ( ram_dout         )
   );
`endif

   assign debug_rdata  = debug_rdata_prism;
   assign ram_raddr1   = curr_si;

   /* 
   =================================================================================
   Assign signals from generated / instantiated RAM
   =================================================================================
   */
   localparam INPUT_SEL_SIZE  = STATE_INPUTS * W_PAR_IN;
   
   localparam INPUT_SEL_START = 1;
   localparam JUMP_TO_START   = INPUT_SEL_SIZE + INPUT_SEL_START;
   localparam OUTPUTS_START   = JUMP_TO_START  + SI_BITS*(DUAL_COMPARE+1);
   localparam CMP_SEL_START   = OUTPUTS_START  + OUTPUTS*(DUAL_COMPARE+2); 
   localparam COND_START      = CMP_SEL_START  + CMP_SEL_SIZE*(DUAL_COMPARE+1);

`ifdef DEBUG_PRISM_STEW
   initial begin
      $display("RAM_WIDTH       = %d", RAM_WIDTH);
      $display("RAM_DEPTH       = %d", RAM_DEPTH);
      $display("INPUT_SEL_START = %d", INPUT_SEL_START);
      $display("OUTPUTS_START   = %d", OUTPUTS_START);
      $display("JUMP_TO_START   = %d", JUMP_TO_START); 
      $display("CMP_SEL_START   = %d", CMP_SEL_START);
      $display("COND_START      = %d", COND_START);
      $display("W_ADDR          = %d", W_ADDR);
   end
`endif

   // Assign stew either as registered or non-registered ram_dout
   assign stew = ram_dout[RAM_WIDTH-1:0];

   // Now map the stew to the individual fields
   for (genvar cmp = 0; cmp < DUAL_COMPARE+1; cmp++)
   begin : OPCODE_ASSIGN_GEN
      // Assign JumpTo bits
      assign jump_to[cmp]       = stew[SI_BITS           + JUMP_TO_START + SI_BITS*(DUAL_COMPARE-cmp) -1      -: SI_BITS];

      // Assign jump_outputs
      assign jump_outputs[cmp]  = stew[OUTPUTS           + OUTPUTS_START + OUTPUTS*((DUAL_COMPARE-cmp)+1) -1  -: OUTPUTS];

      // Assign cmp_sel bits
      assign cmp_sel[cmp]       = stew[CMP_SEL_SIZE*(cmp+1)-1+ CMP_SEL_START -: CMP_SEL_SIZE];
   end

   // Assign conditional output bits
   for (genvar cond = 0; cond < COND_OUT; cond++)
   begin : COND_ASSIGN_GEN
      assign cond_cfg[cond]     = stew[COND_LUT_BITS*cond + COND_START +: COND_LUT_BITS]; 
   end

   // Assign output bits
   assign state_outputs         = stew[OUTPUTS     + OUTPUTS_START-1 -: OUTPUTS];

   // Assign Input mux selection bits
   for (genvar inp = 0; inp < STATE_INPUTS; inp++)
   begin: GEN_IN_MUX_SEL
      assign input_mux_sel[inp] = stew[INPUT_SEL_START + W_PAR_IN * (inp+1) - 1 -: W_PAR_IN];
   end

   // Assign increment bit
   assign inc_si                = stew[0];

   /* 
   =================================================================================
   Clocked State Block for state machine SI
   =================================================================================
   */
   //always @(posedge clk_div2 or negedge prism_rst_n)
   always @(posedge clk or negedge prism_rst_n)
   begin
      if (~prism_rst_n)
      begin
         curr_si <= 'h0;
      end
      else
      begin
//         if (fsm_enable)
         begin
            curr_si <= next_si;
         end
      end
   end

   /* 
   =================================================================================
   Logic for next SI 
   =================================================================================
   */
   assign next_si = debug_halt ? debug_si : 
                       compare_match[0] ? jump_to[0] :
                       DUAL_COMPARE && compare_match[DUAL_COMPARE] ? jump_to[DUAL_COMPARE] :
                       inc_si ? curr_si + 1 :
                       loop_valid ? loop_si :
                       curr_si;
   assign debug_halt_either = debug_halt;

   /* 
   =================================================================================
   Logic for loop_si
   =================================================================================
   */
   //always @(posedge clk_div2 or negedge prism_rst_n)
   always @(posedge clk or negedge prism_rst_n)
   begin
      if (~prism_rst_n)
      begin
         loop_valid <= 1'b0;
         loop_si <= 'h0;
      end
      else
      begin
         if (compare_match[0] || compare_match[DUAL_COMPARE])
            loop_valid <= 1'b0;

         else if (inc_si && ~loop_valid && curr_si != {SI_BITS{1'b1}})
         begin
            loop_valid <= 1'b1;
            loop_si <= curr_si;
         end
      end
   end
   
   /* 
   =================================================================================
   Create a mux for each STATE_INPUT
   =================================================================================
   */
   generate
      for (genvar inp = 0; inp < STATE_INPUTS; inp++)
      begin : STATE_IN_MUX_GEN
         assign input_mux_out_c[inp] = in_data[input_mux_sel[inp]];
         assign input_mux_out[inp] = input_mux_out_c[inp];
      end
   endgenerate

   /* 
   =================================================================================
   For each state index, Generate a LUT
   =================================================================================
   */
   wire [LUT_SIZE-1:0] lut_inputs[DUAL_COMPARE : 0];

   generate
   // Simple LUT4 lookup
   for (genvar cmp = 0; cmp < DUAL_COMPARE+1; cmp++)
   begin : CMP_INST
      // Map MUX outputs to lut inputs
      for (genvar inp = 0; inp < LUT_SIZE; inp++)
      begin: GEN_LUT_INPUTS
         assign lut_inputs[cmp][inp] = input_mux_out[cmp*(STATE_INPUTS-LUT_SIZE)+inp];
      end
      
      assign compare_match[cmp] = cmp_sel[cmp][lut_inputs[cmp]];
   end
   endgenerate

   /* 
   =================================================================================
   Assign the output values.
   =================================================================================
   */
   // Assign outputs based on state compare
   assign out_data_c = compare_match[0] ? jump_outputs[0] : DUAL_COMPARE && 
         compare_match[DUAL_COMPARE] ? jump_outputs[DUAL_COMPARE] : state_outputs;

   // If fractured, mask output bits based on config settings
   assign out_data_m = out_data_c;

   assign out_data_fsm = fsm_enable ? out_data_m : {OUTPUTS{1'b0}};
   assign out_data = out_data_fsm;

   /* 
   =================================================================================
   Assign the conditional outputs
   =================================================================================
   */
   for (genvar cond = 0; cond < COND_OUT; cond++)
   begin : COND_FACTORS
      // Create OR and AND output for each conditional OUT
      assign cond_in[cond] = input_mux_out[2];

      // Drive the conditional output based on enable and ao_sel 
      assign cond_out_c[cond] = cond_cfg[cond][cond_in[cond]];

      // Assign masked registers based on fractured state
      assign cond_out_m[cond] = cond_out_c[cond];
   end

   for (genvar cond = 0; cond < COND_OUT; cond++)
   begin : COND_OUT_GEN
      // Assign final conditional outputs
      assign cond_out[cond] = fsm_enable ? cond_out_m[cond] : 1'b0;
      
   end  

   /* 
   =================================================================================
   Debug Bus Register Map:

   0x00: 
   0x04: debug_ctrl0
   0x08: debug_ctrl1
   0x0c: Current State info
              { {(26-SI_BITS*4) {1'b0}}, 
                debug_break_active[FRACTURABLE], debug_halt[FRACTURABLE], next_si[FRACTURABLE], curr_si[FRACTURABLE],
                debug_break_active[0],           debug_halt[0],           next_si[0],           curr_si[0]
              };
   0x10: STEW LSB
   0x14: STEW MSB
   0x24: cfg_cond_out_mask[0]
   0x2c: cfg_cond_out_mask[1]
   0x30: debug_output_bits;
   0x34: decision_tree_data
   0x38: outut_data
   0x3c: input_data
   ===================================================================================== 
   */
   always @(posedge clk or negedge prism_rst_n)
   begin
      if (~prism_rst_n)
      begin
         debug_si    <= {SI_BITS{1'b0}};
      end
      else
      begin
         // Test for write to debug output register
         if (INCLUDE_DEBUG && debug_wr && (debug_addr[W_ADDR-1:4] == 2'h0))
         begin
            // Test for write to top-level control reg
            if (debug_addr[3:0] == 4'h4)
            begin
               // New SI load from debug interface
               if (debug_new_si)
                  debug_si <= debug_new_siv;
            end
         end
         else if (INCLUDE_DEBUG && debug_entry)
            debug_si <= next_si;
      end
   end


   /*
   ===================================================================================== 
   Instantiate the debug_ctrl register
   ===================================================================================== 
   */
`ifndef SYNTH_FPGA
   prism_latch_reg
   #(
      .WIDTH   ( W_DBG_CTRL )
    )
   i_debug_ctrl0
   (
      .rst_n    ( rst_n                      ),
      .enable   ( debug_ctrl0_en             ),
      .wr       ( latch_wr                   ),
      .data_in  ( latch_data[W_DBG_CTRL-1:0] ),
      .data_out ( debug_ctrl0                )
   );
`else

   reg  [W_DBG_CTRL-1:0]      debug_ctrl0_reg;
   always @(posedge clk or negedge rst_n)
      if (~rst_n)
         debug_ctrl0_reg <= 'h0; 
      else
         if (debug_ctrl0_en && debug_wr)
            debug_ctrl0_reg <= debug_wdata[W_DBG_CTRL-1:0];
   assign debug_ctrl0 = debug_ctrl0_reg;

`endif
   assign debug_ctrl0_en = INCLUDE_DEBUG && (debug_addr == 6'h4);

   /*
   ===================================================================================== 
   Register READ
   ===================================================================================== 
   */
   always @*
   begin
      debug_rdata_prism = 32'h0;

      // Detect debug read
      case (debug_addr[W_ADDR-1:4])
      2'h0: begin
               case (debug_addr[3:0])
                  4'h4:    debug_rdata_prism = {{(32-(W_DBG_CTRL+SI_BITS)){1'b0}},debug_si, debug_ctrl0};
                  4'hC:    debug_rdata_prism = {{(32-SI_BITS*2 - 2){1'b0}}, debug_break_active[0], debug_halt, next_si, curr_si};
                  default: debug_rdata_prism = 32'h0; 
               endcase
           end
      2'h1:   debug_rdata_prism = debug_rdata_ram;

      2'h3:   begin
                  case (debug_addr[3:0])
                       // ID REG:            CLUTSize CondOut   Inputs   OUTPUTS  States  FracDual  NLUTS LUT_SIZE
                  4'h0: debug_rdata_prism = {    3'd1,   3'd1,    6'd16,   6'd11,  6'd08,     2'h0,  3'h3,   3'h2};
                  4'h4: debug_rdata_prism = decision_tree_data;
                  4'h8: debug_rdata_prism = {{(32-OUTPUTS){1'b0}}, out_data};
                  4'hc: debug_rdata_prism = {{(32-INPUTS){1'b0}}, in_data};
                  default: debug_rdata_prism = 32'h0; 
                  endcase
              end
      default: debug_rdata_prism = 32'h0;
      endcase
   end

   localparam LUT_INOUT_SIZE = 1 + LUT_SIZE;

   always @*
   begin
      integer cmp;

      // Default to zero
      decision_tree_data = 32'h0;

      // Add decision tree data
      for (cmp = 0; cmp <= DUAL_COMPARE; cmp++)
         decision_tree_data[(cmp+1)*LUT_INOUT_SIZE-1 -: LUT_INOUT_SIZE] = {compare_match[cmp], lut_inputs[cmp]};
   end

   /* 
   =================================================================================
   Debug print the state changes
   =================================================================================
   */

`ifdef DEBUG_PRISM_TRANSITIONS
   always @(curr_si or out_data)
      $display("SI=%02x   OutData=%06X   Jump0 Out=%06X   JumpTo 0=%3d  LUT_in=%X  CMP=%d", 
            curr_si, out_data, jump_outputs[0], jump_to[0], lut_inputs[0], compare_match[0]);

   if (DUAL_COMPARE)
   begin
      always @(compare_match[1])
         $display("CompareMatch 1 = %d\n", compare_match[1]);
      always @(jump_outputs[1])
         $display("Jump1 Out=%x\n", jump_outputs[1]);
      always @(jump_to[1])
         $display("JumpTo 1 = %d\n", jump_to[1]);
   end
`endif

   /* 
   =================================================================================
   Assign debug control register bits
   =================================================================================
   */
   // Control for fracture unit 0
   assign debug_halt_req = debug_ctrl0[0];
   assign debug_step_si  = debug_ctrl0[1];
   assign debug_bp_en0   = debug_ctrl0[2];
   assign debug_bp_en1   = debug_ctrl0[3];
   assign debug_bp_si0   = debug_ctrl0[SI_BITS  +4-1 -: SI_BITS];
   assign debug_bp_si1   = debug_ctrl0[SI_BITS*2+4-1 -: SI_BITS];
   assign debug_new_si   = debug_wdata[SI_BITS*2+4];
   assign debug_new_siv  = debug_wdata[SI_BITS*3+5-1 -: SI_BITS];

   /* 
   =================================================================================
   Debugger code
   =================================================================================
   */
   assign debug_entry = debug_step_pending || 
                       (debug_bp_en0 && !debug_break_active[0] && !debug_resume_pending && (debug_bp_si0 == next_si)) ||
                       (debug_bp_en1 && !debug_break_active[1] && !debug_resume_pending && (debug_bp_si1 == next_si)) ||
                       (debug_halt_req & !debug_halt_req_p1);

   //always @(posedge clk_div2 or negedge prism_rst_n)
   always @(posedge clk or negedge prism_rst_n)
   begin
      if (~prism_rst_n)
      begin
         debug_halt <= 1'b0;
         debug_step_pending <= 1'h0;
         debug_resume_pending <= 1'h0;
         debug_halt_req_p1 <= 1'h0;
         debug_step_si_last <= 1'h0;

         debug_break_active <= 2'h0;
      end
      else
      begin
         // Create rising edge detector for debug_step_si
         debug_step_si_last <= debug_step_si;

         // Test for single-step request
         if (debug_halt && debug_step_si && !debug_step_si_last && !debug_step_pending)
         begin
            // Disable halt and enable step_pending
            debug_halt <= 1'b0;
            debug_step_pending <= 1'b1;
            debug_break_active <= 2'b0;
         end

         // Test if we need to halt the FSM
         else if (debug_entry)
         begin
            // Halt the FSM
            debug_halt <= 1'b1;
            debug_step_pending <= 1'b0;

            // If halt requested, clear debug_break_active
            if (debug_halt_req)
               debug_break_active <= 2'h0;
            else
            begin
               // Test if we broke because of breakpoint 0
               if (debug_bp_en0 && !debug_break_active[0] && (debug_bp_si0 == curr_si))
                  debug_break_active[0] <= 1'b1;
               else
                  debug_break_active[0] <= 1'b0;

               // Test if we broke because of breakpoint 1
               if (debug_bp_en1 && !debug_break_active[1] && (debug_bp_si1 == curr_si))
                  debug_break_active[1] <= 1'b1;
               else
                  debug_break_active[1] <= 1'b0;
            end
         end

         // Test if we need to resume the FSM
         else if (debug_halt && !debug_halt_req && !debug_break_active[0] && !debug_break_active[1])
         begin
            debug_halt <= 1'b0;
            debug_step_pending <= 1'b0;
            debug_break_active <= 2'b0;
         end

         // Test for resume from halt request
         debug_halt_req_p1 <= debug_halt_req;
         debug_resume_pending <= debug_halt_req_p1 & !debug_halt_req;
         if (debug_halt_req_p1 & !debug_halt_req)
         begin
            debug_halt <= 1'b0;
            debug_break_active <= 2'b0;
         end
      end
   end

endmodule // prism


