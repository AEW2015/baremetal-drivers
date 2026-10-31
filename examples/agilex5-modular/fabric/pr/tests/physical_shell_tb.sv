`timescale 1ns/1ps
module physical_shell_tb;
 reg clk=0,reset_n=0,read=0,write=0;reg [5:0] address=0;reg [31:0] wd=0;wire [31:0] rd;reg [31:0] value;
 always #5 clk=~clk;
 lab_pr dut(.clk(clk),.reset_n(reset_n),.address(address),.read(read),.write(write),.writedata(wd),.byteenable(4'hf),.readdata(rd));
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 task put(input [5:0] a,input [31:0] v);begin address=a;wd=v;write=1;tick;write=0;tick;end endtask
 task get(input [5:0] a);begin address=a;read=1;tick;value=rd;read=0;tick;end endtask
 task check(input bit ok);begin if(!ok)$fatal(1,"PHYSICAL_SHELL_CONTRACT_FAIL");end endtask
 initial begin
  tick;reset_n=1;tick;get(22);check(value==32'h50525331);
  put(32,2);get(2);check(value==32'h41444431); // No simulation-loader side effect.
  put(16,1);repeat(5)tick;put(24,1);get(24);check(value==1);
  get(0);check(value==32'hdec0f001);put(24,2);repeat(12)tick;
  get(16);check(value[1] && !value[2]);put(16,0);get(20);check(value==1);
  put(19,32'h584f5231);put(16,1);repeat(5)tick;put(24,1);repeat(5)tick;put(24,2);repeat(12)tick;
  get(16);check(value[2] && value[0]);put(16,0);get(16);check(value[0]);
  $display("PASS PHYSICAL_SHELL_RTL host_handshake simulation_register_absent wrong_persona_isolated; NO_HARDWARE_EXECUTION");$finish;
 end
 initial begin #100000;$fatal(1,"TIMEOUT");end
endmodule
