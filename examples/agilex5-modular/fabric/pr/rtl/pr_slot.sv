// Physical PR partition interface. All control/isolation lives in the static shell.
module pr_slot (
 input wire clk,reset_n,input wire [3:0] avs_address,input wire avs_read,avs_write,
 input wire [31:0] avs_writedata,input wire [3:0] avs_byteenable,
 output wire [31:0] avs_readdata
);
 lab_ip #(.MODE(1)) ip(.*);
endmodule
module pr_slot_xor (
 input wire clk,reset_n,input wire [3:0] avs_address,input wire avs_read,avs_write,
 input wire [31:0] avs_writedata,input wire [3:0] avs_byteenable,
 output wire [31:0] avs_readdata
);
 lab_ip #(.MODE(2)) ip(.*);
endmodule
