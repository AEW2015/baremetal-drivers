// Synthesizable shell. Host JTAG coordinator writes 0x60 around quartus_pgm --pr.
// 0x80 simulated loader register is deliberately absent.
module lab_pr (
 input wire clk,reset_n,input wire [5:0] address,input wire read,write,
 input wire [31:0] writedata,input wire [3:0] byteenable,output wire [31:0] readdata
);
 reg [2:0] host_status;reg host_read;
 wire [31:0] shell_data,region_data;wire [3:0] ra,be;
 wire rr,rw,rn,frozen;wire [31:0] wd;
 always @(posedge clk or negedge reset_n)begin
  if(!reset_n)begin host_status<=0;host_read<=0;end
  else begin
   if(read)host_read<=address==24;
   if(write && address==24 && byteenable==15)host_status<=writedata[2:0];
  end
 end
 assign readdata=host_read?{29'b0,host_status}:shell_data;
 pr_static shell(.clk(clk),.reset_n(reset_n),.address(address),.read(read),.write(write),
  .writedata(writedata),.byteenable(byteenable),.readdata(shell_data),
  .region_address(ra),.region_read(rr),.region_write(rw),.region_writedata(wd),
  .region_byteenable(be),.region_readdata(region_data),.region_reset_n(rn),
  .pr_busy(host_status[0]),.pr_done(host_status[1]),.pr_error(host_status[2]),.frozen(frozen));
 pr_slot slot(.clk(clk),.reset_n(rn),.avs_address(ra),.avs_read(rr),.avs_write(rw),
  .avs_writedata(wd),.avs_byteenable(be),.avs_readdata(region_data));
endmodule
