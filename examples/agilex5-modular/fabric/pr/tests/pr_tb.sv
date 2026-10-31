`timescale 1ns/1ps
module pr_tb;
 reg clk=0,reset_n=0,read=0,write=0,busy=0,done=0,error=0,suppress=0;
 reg [5:0] address=0;reg [31:0] wd=0;reg [1:0] persona=1;
 wire [31:0] rd;wire frozen,rn;integer checks=0;reg [31:0] value,hb;
 always #5 clk=~clk;
 pr_model dut(.clk(clk),.reset_n(reset_n),.address(address),.read(read),.write(write),
  .writedata(wd),.byteenable(4'hf),.readdata(rd),.select_persona(persona),
  .pr_busy(busy),.pr_done(done),.pr_error(error),.suppress_reset(suppress),.frozen(frozen),.persona_reset_n(rn));
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 task put(input [5:0] a,input [31:0] v);begin address=a;wd=v;write=1;tick;write=0;tick;end endtask
 task get(input [5:0] a,output [31:0] v);begin address=a;read=1;tick;v=rd;read=0;tick;end endtask
 task check(input bit ok,input [511:0] label_text);begin if(!ok) $fatal(1,"FAIL %s",label_text);checks=checks+1;end endtask
 task freeze(input [31:0] expected);begin put(19,expected);put(16,1);repeat(5)tick;check(frozen,"ISOLATED");end endtask
 task load(input [1:0] mode,input bit fail_load);begin
  busy=1;repeat(5)tick;
  // Mimic undefined register state after PR in a FOUR-STATE simulator.
  dut.add_ip.a='x;dut.add_ip.b='x;dut.add_ip.result='x;dut.add_ip.sequence_count='x;
  dut.xor_ip.a='x;dut.xor_ip.b='x;dut.xor_ip.result='x;dut.xor_ip.sequence_count='x;
  persona=mode;busy=0;done=!fail_load;error=fail_load;tick;done=0;error=0;repeat(12)tick;
 end endtask
 task release_slot;begin get(16,value);check(value[1] && !value[2],"READY_AFTER_RESET_AND_ID");put(16,0);check(!frozen,"RELEASED");end endtask
 task math(input [31:0] expected);begin put(5,7);put(6,5);put(3,1);get(7,value);check(value===expected,"PERSONA_RESULT");end endtask
 initial begin
  tick;reset_n=1;tick;put(18,32'hcafe1234);get(17,hb);math(12);
  freeze(32'h584f5231);busy=1;get(7,value);check(value===32'hdec0f001,"UNKNOWN_OUTPUT_ISOLATED");busy=0;
  load(2,0);release_slot;get(8,value);check(value===0,"RESET_CLEARED_SEQUENCE");math(2);
  freeze(32'h41444431);load(1,1);put(16,0);check(frozen,"FAILED_LOAD_STAYS_ISOLATED");get(16,value);check(value[2],"FAILED_LOAD_LATCHED");
  load(1,0);release_slot;math(12);
  freeze(32'h584f5231);load(1,0);get(16,value);check(value[2] && frozen,"WRONG_PERSONA_REJECTED");
  load(2,0);release_slot;
  get(18,value);check(value===32'hcafe1234,"STATIC_SCRATCH_PRESERVED");get(17,value);check(value>hb,"STATIC_HEARTBEAT_CONTINUES");
  get(20,value);check(value==3,"SUCCESSFUL_SWAP_COUNT");
  freeze(32'h41444431);suppress=1;load(1,0);release_slot;get(8,value);
  check($isunknown(value),"MISSING_RESET_CONTROL_EXPOSES_UNKNOWN_REGISTERS");
  $display("PASS PR_FOUR_STATE checks=%0d ADD_XOR_ADD isolation failure recovery reset continuity",checks);$finish;
 end
 initial begin #100000;$fatal(1,"FAIL TIMEOUT");end
endmodule
