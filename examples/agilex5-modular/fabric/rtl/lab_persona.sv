// MODE is a compile-time persona choice, never a runtime multiplexer control.
module lab_persona # (parameter integer MODE = 1) (
    input wire [31:0] a, b,
    output wire [31:0] result, persona_id
);
    assign persona_id = MODE == 1 ? 32'h41444431 : 32'h584f5231; // ADD1 / XOR1
    assign result = MODE == 1 ? a + b : a ^ b;
endmodule
