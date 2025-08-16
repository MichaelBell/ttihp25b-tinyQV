
module font_rom (
    input  [2:0] digit,
    input  [2:0] column,
    output [7:0] data
);

    reg [7:0] font [0:63];

    initial begin
        // Digit 0
        font[ 0] = 8'h00;
        font[ 1] = 8'h3C;
        font[ 2] = 8'h42;
        font[ 3] = 8'h3C;
        font[ 4] = 8'h00;
        font[ 5] = 8'h00;
        font[ 6] = 8'h00;
        font[ 7] = 8'h00;

        // Digit 1
        font[ 8] = 8'h00;
        font[ 9] = 8'h44;
        font[10] = 8'h7E;
        font[11] = 8'h40;
        font[12] = 8'h00;
        font[13] = 8'h00;
        font[14] = 8'h00;
        font[15] = 8'h00;

        // Digit 2
        font[16] = 8'h00;
        font[17] = 8'h32;
        font[18] = 8'h2A;
        font[19] = 8'h24;
        font[20] = 8'h00;
        font[21] = 8'h00;
        font[22] = 8'h00;
        font[23] = 8'h00;

        // Digit 3
        font[24] = 8'h00;
        font[25] = 8'h22;
        font[26] = 8'h2A;
        font[27] = 8'h14;
        font[28] = 8'h00;
        font[29] = 8'h00;
        font[30] = 8'h00;
        font[31] = 8'h00;

        // Digit 4
        font[32] = 8'h00;
        font[33] = 8'h0E;
        font[34] = 8'h08;
        font[35] = 8'h3C;
        font[36] = 8'h00;
        font[37] = 8'h00;
        font[38] = 8'h00;
        font[39] = 8'h00;

        // Digit 5
        font[40] = 8'h00;
        font[41] = 8'h26;
        font[42] = 8'h2A;
        font[43] = 8'h12;
        font[44] = 8'h00;
        font[45] = 8'h00;
        font[46] = 8'h00;
        font[47] = 8'h00;

        // Digit 6
        font[48] = 8'h00;
        font[49] = 8'h1C;
        font[50] = 8'h2A;
        font[51] = 8'h12;
        font[52] = 8'h00;
        font[53] = 8'h00;
        font[54] = 8'h00;
        font[55] = 8'h00;

        // Digit 7
        font[56] = 8'h00;
        font[57] = 8'h02;
        font[58] = 8'h02;
        font[59] = 8'h3E;
        font[60] = 8'h00;
        font[61] = 8'h00;
        font[62] = 8'h00;
        font[63] = 8'h00;
    end

    assign data = font[{digit, column}]; // data = font[digit * 8 + column];

endmodule
