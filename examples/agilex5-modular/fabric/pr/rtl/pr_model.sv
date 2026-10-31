// SIMULATION ONLY: two RTL personas and an explicit simulated loader.
// This mux is never a physical PR implementation or a bitstream parser.
module pr_model (
 input wire clk,reset_n,input wire [5:0] address,input wire read,write,
 input wire [31:0] writedata,input wire [3:0] byteenable,
 output wire [31:0] readdata,
 input wire [1:0] select_persona,input wire pr_busy,pr_done,pr_error,
 input wire suppress_reset,output wire frozen,output wire persona_reset_n
);
 wire [3:0] ra,be;wire rr,rw;wire [31:0] wd,add_data,xor_data;
 wire [31:0] region_data = pr_busy ? 32'hxxxxxxxx : select_persona==1 ? add_data : select_persona==2 ? xor_data : 32'hxxxxxxxx;
 pr_static shell(.clk(clk),.reset_n(reset_n),.address(address),.read(read),.write(write),
  .writedata(writedata),.byteenable(byteenable),.readdata(readdata),
  .region_address(ra),.region_read(rr),.region_write(rw),.region_writedata(wd),
  .region_byteenable(be),.region_readdata(region_data),
  .region_reset_n(persona_reset_n),.pr_busy(pr_busy),.pr_done(pr_done),.pr_error(pr_error),.frozen(frozen));
 wire rn = suppress_reset ? reset_n : persona_reset_n;
 lab_ip #(.MODE(1)) add_ip(.clk(clk),.reset_n(rn),.avs_address(ra),.avs_read(rr && select_persona==1),
  .avs_write(rw && select_persona==1),.avs_writedata(wd),.avs_byteenable(be),.avs_readdata(add_data));
 lab_ip #(.MODE(2)) xor_ip(.clk(clk),.reset_n(rn),.avs_address(ra),.avs_read(rr && select_persona==2),
  .avs_write(rw && select_persona==2),.avs_writedata(wd),.avs_byteenable(be),.avs_readdata(xor_data));
endmodule
