// 64-byte, 32-bit Avalon-MM register agent. address is a WORD address.
// Single clock, fixed one-cycle registered reads, no bursts or waitrequest.
module lab_ip # (parameter integer MODE = 1) (
    input wire clk, reset_n,
    input wire [3:0] avs_address,
    input wire avs_read, avs_write,
    input wire [31:0] avs_writedata,
    input wire [3:0] avs_byteenable,
    output reg [31:0] avs_readdata
);
    reg [31:0] a, b, result, sequence_count;
    reg done, rejected, quiesce;
    wire [31:0] persona_result, persona_id;
    // The introductory PR recipe partitions this entire lab_ip instance.
    // Partitioning only u_persona is a later conduit-isolation exercise.
    lab_persona #(.MODE(MODE)) u_persona (
        .a(a), .b(b), .result(persona_result), .persona_id(persona_id));
    function automatic [31:0] merge_bytes(input [31:0] old_value, new_value,
                                         input [3:0] enables);
        integer i;
        begin
            merge_bytes = old_value;
            for (i=0;i<4;i=i+1)
                if (enables[i]) merge_bytes[i*8+:8] = new_value[i*8+:8];
        end
    endfunction
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            a<=0; b<=0; result<=0; sequence_count<=0;
            done<=0; rejected<=0; quiesce<=0; avs_readdata<=0;
        end else begin
            if (avs_read) begin
                case (avs_address)
                    0: avs_readdata<=32'h4c414231; // LAB1
                    1: avs_readdata<=32'h00010000; // ABI 1.0
                    2: avs_readdata<=quiesce ? 32'b0 : persona_id;
                    3: avs_readdata<={30'b0,quiesce,1'b0};
                    4: avs_readdata<={29'b0,rejected,quiesce,done};
                    5: avs_readdata<=a;
                    6: avs_readdata<=b;
                    7: avs_readdata<=result;
                    8: avs_readdata<=sequence_count;
                    default: avs_readdata<=0;
                endcase
            end
            if (avs_write) begin
                case (avs_address)
                    3: if (avs_byteenable[0]) begin
                        quiesce<=avs_writedata[1];
                        if (avs_writedata[0]) begin
                            if (quiesce || avs_writedata[1]) rejected<=1;
                            else begin
                                result<=persona_result;
                                sequence_count<=sequence_count+1;
                                done<=1;
                            end
                        end
                    end
                    4: if (avs_byteenable[0]) begin
                        if (avs_writedata[0]) done<=0;
                        if (avs_writedata[2]) rejected<=0;
                    end
                    5: a<=merge_bytes(a,avs_writedata,avs_byteenable);
                    6: b<=merge_bytes(b,avs_writedata,avs_byteenable);
                    default: ; // Read-only and reserved writes ignored.
                endcase
            end
        end
    end
endmodule
