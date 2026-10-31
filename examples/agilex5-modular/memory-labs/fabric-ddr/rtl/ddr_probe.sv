// SPDX-License-Identifier: MIT-0
// Single-beat AXI4 memory exerciser. The default address guard disables DMA.
// One clock domain; reset must be synchronized before entering this component.
module ddr_probe #(
    parameter logic [63:0] ALLOWED_BASE = 64'd0,
    parameter logic [63:0] ALLOWED_END = 64'd0,
    parameter integer MAX_WORDS = 65536,
    parameter integer WATCHDOG_CYCLES = 1024,
    parameter logic [2:0] AXPROT = 3'b000,
    parameter logic [7:0] AXUSER = 8'd0
) (
    input logic clk, reset,
    input logic [5:0] csr_address,
    input logic csr_read, csr_write,
    input logic [31:0] csr_writedata,
    input logic [3:0] csr_byteenable,
    output logic [31:0] csr_readdata,
    output logic irq,
    output logic [39:0] m_awaddr, m_araddr,
    output logic m_awid, m_arid,
    output logic [7:0] m_awlen, m_arlen,
    output logic [2:0] m_awsize, m_arsize,
    output logic [1:0] m_awburst, m_arburst,
    output logic [2:0] m_awprot, m_arprot,
    output logic [3:0] m_awcache, m_arcache,
    output logic [7:0] m_awuser, m_aruser,
    output logic m_awvalid, m_arvalid,
    input logic m_awready, m_arready,
    output logic [63:0] m_wdata,
    output logic [7:0] m_wstrb,
    output logic m_wlast, m_wvalid,
    input logic m_wready,
    input logic [1:0] m_bresp,
    input logic m_bid,
    input logic m_bvalid,
    output logic m_bready,
    input logic [63:0] m_rdata,
    input logic [1:0] m_rresp,
    input logic m_rid,
    input logic m_rlast, m_rvalid,
    output logic m_rready
);
    typedef enum logic [2:0] {IDLE, AW, WD, BR, AR, RD} phase_t;
    phase_t phase;
    logic [63:0] base, active_base, fail_address, expected_data, observed_data, cycles;
    logic [31:0] words, seed, active_words, active_seed, index_word, verified, wait_count;
    logic done, error, rejected, timed_out;
    logic [31:0] error_code;
    wire busy = phase != IDLE;
    wire [64:0] end_address = {1'b0,base} + ({33'd0,words} << 3);
    wire valid_range = ALLOWED_BASE < ALLOWED_END && base >= ALLOWED_BASE &&
        end_address <= {1'b0,ALLOWED_END} && end_address < 65'h10000000000 &&
        base[2:0] == 0 && words != 0 && words <= 32'(MAX_WORDS);
    wire [63:0] address_word = active_base + ({32'd0,index_word} << 3);
    function automatic [63:0] pattern(input [31:0] s, i);
        pattern = {s ^ i, s + i};
    endfunction
    function automatic [31:0] merge(input [31:0] old_value, new_value,
                                    input [3:0] enables);
        for (integer i=0;i<4;i=i+1)
            merge[i*8+:8] = enables[i] ? new_value[i*8+:8] : old_value[i*8+:8];
    endfunction
    assign m_awaddr=address_word[39:0];
    assign m_araddr=address_word[39:0];
    assign m_awlen=0; assign m_arlen=0;
    assign m_awid=0; assign m_arid=0;
    assign m_awsize=3; assign m_arsize=3;
    assign m_awburst=1; assign m_arburst=1;
    assign m_awprot=AXPROT; assign m_arprot=AXPROT;
    assign m_awcache=0; assign m_arcache=0;
    assign m_awuser=AXUSER; assign m_aruser=AXUSER;
    assign m_awvalid=phase==AW; assign m_arvalid=phase==AR;
    assign m_wvalid=phase==WD; assign m_wlast=1; assign m_wstrb=8'hff;
    assign m_wdata=pattern(active_seed,index_word);
    assign m_bready=phase==BR; assign m_rready=phase==RD;
    assign irq=done;

    // Timeout never withdraws an AXI request or abandons an accepted transfer.
    // Flag it immediately, drain that one transaction, then stop issuing work.
    task automatic stalled;
        if (wait_count < 32'(WATCHDOG_CYCLES)) wait_count <= wait_count+1;
        if (wait_count >= 32'(WATCHDOG_CYCLES-1)) begin
            timed_out<=1; error<=1; error_code<=4;
            fail_address<=address_word;
        end
    endtask
    always_ff @(posedge clk) begin
        if (reset) begin
            phase<=IDLE; base<=0; words<=0; seed<=0;
            active_base<=0; active_words<=0; active_seed<=0; index_word<=0;
            verified<=0; done<=0; error<=0; rejected<=0; timed_out<=0;
            fail_address<=0; expected_data<=0; observed_data<=0;
            cycles<=0; wait_count<=0; error_code<=0; csr_readdata<=0;
        end else begin
            if (busy) cycles<=cycles+1;
            if (csr_read) case (csr_address)
                0: csr_readdata<=32'h44445231;
                1: csr_readdata<=32'h00010000;
                2: csr_readdata<=0;
                3: csr_readdata<={27'd0,timed_out,rejected,error,done,busy};
                4: csr_readdata<=base[31:0];
                5: csr_readdata<=base[63:32];
                6: csr_readdata<=words;
                7: csr_readdata<=seed;
                8: csr_readdata<=verified;
                9: csr_readdata<=fail_address[31:0];
                10: csr_readdata<=fail_address[63:32];
                11: csr_readdata<=expected_data[31:0];
                12: csr_readdata<=expected_data[63:32];
                13: csr_readdata<=observed_data[31:0];
                14: csr_readdata<=observed_data[63:32];
                15: csr_readdata<=cycles[31:0];
                16: csr_readdata<=cycles[63:32];
                17: csr_readdata<=ALLOWED_BASE[31:0];
                18: csr_readdata<=ALLOWED_BASE[63:32];
                19: csr_readdata<=ALLOWED_END[31:0];
                20: csr_readdata<=ALLOWED_END[63:32];
                21: csr_readdata<=32'(WATCHDOG_CYCLES);
                22: csr_readdata<=error_code;
                default: csr_readdata<=0;
            endcase
            if (csr_write) begin
                if (busy) rejected<=1;
                else case (csr_address)
                    4: base[31:0]<=merge(base[31:0],csr_writedata,csr_byteenable);
                    5: base[63:32]<=merge(base[63:32],csr_writedata,csr_byteenable);
                    6: words<=merge(words,csr_writedata,csr_byteenable);
                    7: seed<=merge(seed,csr_writedata,csr_byteenable);
                    2: if (csr_byteenable[0]) begin
                        if (csr_writedata[1]) begin
                            done<=0; error<=0; rejected<=0; timed_out<=0; error_code<=0;
                        end
                        if (csr_writedata[0]) begin
                            verified<=0; cycles<=0; wait_count<=0; index_word<=0;
                            done<=0; error<=0; rejected<=0; timed_out<=0; error_code<=0;
                            fail_address<=0; expected_data<=0; observed_data<=0;
                            if (!valid_range) begin
                                done<=1; error<=1; rejected<=1; error_code<=1; fail_address<=base;
                            end else begin
                                active_base<=base; active_words<=words; active_seed<=seed;
                                phase<=AW;
                            end
                        end
                    end
                    default: ;
                endcase
            end
            case (phase)
                AW: if (m_awready) begin phase<=WD; wait_count<=0; end else stalled();
                WD: if (m_wready) begin phase<=BR; wait_count<=0; end else stalled();
                BR: if (m_bvalid) begin
                    wait_count<=0;
                    if (m_bresp!=0 || m_bid!=0 || timed_out) begin
                        error<=1; done<=1; phase<=IDLE;
                        if (!timed_out) begin error_code<=3; fail_address<=address_word; end
                    end else if (index_word+1==active_words) begin index_word<=0; phase<=AR; end
                    else begin index_word<=index_word+1; phase<=AW; end
                end else stalled();
                AR: if (m_arready) begin phase<=RD; wait_count<=0; end else stalled();
                RD: if (m_rvalid) begin
                    wait_count<=0;
                    if (m_rresp!=0 || m_rid!=0 || !m_rlast || timed_out || m_rdata!=pattern(active_seed,index_word)) begin
                        error<=1; done<=1; phase<=IDLE; fail_address<=address_word;
                        expected_data<=pattern(active_seed,index_word); observed_data<=m_rdata;
                        if (!timed_out) error_code<=m_rresp!=0 || m_rid!=0 || !m_rlast ? 3 : 2;
                    end else begin
                        verified<=verified+1;
                        if (index_word+1==active_words) begin done<=1; phase<=IDLE; end
                        else begin index_word<=index_word+1; phase<=AR; end
                    end
                end else stalled();
                default: ;
            endcase
        end
    end
endmodule
