// Static, single-clock shell for the fixed-latency lab_ip Avalon-MM agent.
// No bursts, waitrequest or IRQ cross this boundary. Keep this instance OUTSIDE PR.
module pr_static (
 input wire clk, reset_n,
 input wire [5:0] address, input wire read, write,
 input wire [31:0] writedata, input wire [3:0] byteenable,
 output wire [31:0] readdata,
 output wire [3:0] region_address, output wire region_read, region_write,
 output wire [31:0] region_writedata, output wire [3:0] region_byteenable,
 input wire [31:0] region_readdata, output wire region_reset_n,
 input wire pr_busy, pr_done, pr_error,
 output wire frozen
);
 localparam RUN=4'd0,DRAIN=4'd1,FROZEN=4'd2,RST=4'd3,
            PROBE=4'd4,WAIT_ID=4'd5,CHECK_ID=4'd6,READY=4'd7,ERROR=4'd8;
 reg [3:0] state;
 reg [2:0] count;
 reg seen_busy, selected_region;
 reg [31:0] heartbeat,scratch,expected_id,observed_id,swaps,csr_data;
 wire access_ok = state==RUN && !pr_busy && !pr_error;
 assign frozen = !access_ok;
 assign region_reset_n = reset_n && state!=RST;
 assign region_address = state==PROBE ? 4'd2 : address[3:0];
 assign region_read = (access_ok && read && address<16) || state==PROBE;
 assign region_write = access_ok && write && address<16;
 assign region_writedata=writedata;
 assign region_byteenable=byteenable;
 // Registered region reads are returned directly after their clock edge.
 // Never expose changing/unknown PR outputs while isolated.
 assign readdata = selected_region ? (access_ok ? region_readdata : 32'hdec0f001) : csr_data;
 always @(posedge clk or negedge reset_n) begin
  if (!reset_n) begin
   state<=RUN;count<=0;seen_busy<=0;selected_region<=0;
   heartbeat<=0;scratch<=0;expected_id<=32'h41444431;observed_id<=0;swaps<=0;csr_data<=0;
  end else begin
   heartbeat<=heartbeat+1;
   if (read) begin
    selected_region<=address<16;
    case(address)
     16: csr_data<={20'b0,state,3'b0,(state==RST),seen_busy,(state==ERROR),(state==READY),frozen};
     17: csr_data<=heartbeat;
     18: csr_data<=scratch;
     19: csr_data<=expected_id;
     20: csr_data<=swaps;
     21: csr_data<=observed_id;
     22: csr_data<=32'h50525331; // PRS1 static ABI
     default: csr_data<=0;
    endcase
   end
   // Static control writes require full words, avoiding partial-command ambiguity.
   if (write && byteenable==15) begin
    if (address==18) scratch<=writedata;
    if (address==19 && (writedata==32'h41444431 || writedata==32'h584f5231)) expected_id<=writedata;
   end
   case(state)
    RUN: if (write && address==16 && byteenable==15 && writedata==1) begin state<=DRAIN;count<=2;seen_busy<=0;end
    DRAIN: if (count==0) state<=FROZEN;else count<=count-1'b1;
    FROZEN: begin
     if (pr_busy) seen_busy<=1;
     if (pr_done && seen_busy && !pr_busy) begin state<=RST;count<=3;end
    end
    RST: if (count==0) state<=PROBE;else count<=count-1'b1;
    PROBE: state<=WAIT_ID;
    WAIT_ID: begin observed_id<=region_readdata;state<=CHECK_ID;end
    CHECK_ID: if (observed_id==expected_id) state<=READY;else state<=ERROR;
    READY: if (write && address==16 && byteenable==15 && writedata==0) begin state<=RUN;swaps<=swaps+1;seen_busy<=0;end
    ERROR: if (pr_busy && !pr_error) begin state<=FROZEN;seen_busy<=1;end
    default: state<=ERROR;
   endcase
   // An unsolicited load or loader error must keep the boundary closed.
   if (pr_error || (pr_busy && state!=FROZEN && state!=ERROR)) state<=ERROR;
  end
 end
endmodule
