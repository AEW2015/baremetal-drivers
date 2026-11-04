// SPDX-License-Identifier: MIT-0
`timescale 1ns/1ps
module test_cc_reader;
    reg clk=0;
    always #5 clk=~clk;
    reg reset_n=0, trigger_toggle=0;
    reg [2:0] command=0;
    reg [3:0] byte_select=15;
    reg slave_sda_low=0, slave_scl_low=0;
    tri1 scl,sda;
    wire [31:0] status;
    assign scl=slave_scl_low?1'b0:1'bz;
    assign sda=slave_sda_low?1'b0:1'bz;
    cc_reader #(.ALLOW_MODE_WRITES(1'b1),.TICK_CYCLES(8),.MAX_CYCLES(12000),.IDLE_WAIT_CYCLES(500)) dut(
        .clk(clk),.reset_n(reset_n),.trigger_toggle(trigger_toggle),
        .command(command),.byte_select(byte_select),.usb_inputs(3'b101),.cc_scl(scl),.cc_sda(sda),.status(status));
    reg ro_trigger=0;
    tri1 ro_scl,ro_sda;
    wire [31:0] ro_status;
    cc_reader #(.TICK_CYCLES(8),.MAX_CYCLES(12000),.IDLE_WAIT_CYCLES(500)) readonly_dut(
        .clk(clk),.reset_n(reset_n),.trigger_toggle(ro_trigger),.command(3'd1),
        .byte_select(4'd15),.usb_inputs(3'b101),.cc_scl(ro_scl),.cc_sda(ro_sda),.status(ro_status));
    byte expected[0:10];
    integer slave_pointer=91; // Retained, initially nonzero: no reset-on-START shortcut.
    initial begin
        expected[0]=8'h32;expected[1]=8'h32;expected[2]=8'h33;expected[3]=8'h42;
        expected[4]=8'h53;expected[5]=8'h55;expected[6]=8'h54;expected[7]=0;
        expected[8]=0;expected[9]=8'h60;expected[10]=0;
    end
    task automatic launch;
        @(negedge clk);trigger_toggle=~trigger_toggle;
        wait(status[30]);
    endtask
    task automatic finish_case(input integer code);
        wait(status[31]);#20;
        if(status[30] || status[29:26] != code || scl!==1 || sda!==1)
            $fatal(1,"Unexpected completion: code=%0d status=%h scl=%b sda=%b",code,status,scl,sda);
    endtask
    task automatic address_phase(output byte address,input byte wanted);
        @(negedge sda);if(scl!==1)$fatal(1,"START with SCL low");
        address=0;
        repeat(8) begin @(posedge scl);address={address[6:0],sda};end
        if(address!=wanted)$fatal(1,"Unexpected address byte %h expected %h",address,wanted);
    endtask
    task automatic slave_reply(input bit stretch);
        byte address;
        address_phase(address,8'h8e);
        @(negedge scl);slave_sda_low=1;
        @(posedge scl);@(negedge scl);slave_sda_low=0;
        address=0;
        repeat(8)begin @(posedge scl);address={address[6:0],sda};end
        if(address!=0)$fatal(1,"Read pointer must be zero, got %h",address);
        slave_pointer=address;
        @(negedge scl);slave_sda_low=1;
        @(posedge scl);@(negedge scl);slave_sda_low=0;
        address_phase(address,8'h8f);
        @(negedge scl);slave_sda_low=1;
        @(posedge scl);@(negedge scl);slave_sda_low=0;
        for(integer index=0;index<11;index=index+1) begin
            for(integer bitno=7;bitno>=0;bitno=bitno-1) begin
                slave_sda_low=!expected[slave_pointer][bitno];
                if(stretch && index==2 && bitno==4) begin
                    slave_scl_low=1;repeat(80)@(negedge clk);slave_scl_low=0;
                end
                @(posedge scl);@(negedge scl);
            end
            slave_sda_low=0;
            @(posedge scl);
            if(sda !== (index==10))$fatal(1,"Wrong ACK at byte %0d",index);
            @(negedge scl);
            slave_pointer=slave_pointer+1;
        end
        @(posedge sda);if(scl!==1)$fatal(1,"STOP with SCL low");
    endtask
    task automatic slave_write(input byte expected_value);
        byte value;
        @(negedge sda);if(scl!==1)$fatal(1,"Write START with SCL low");
        for(integer index=0;index<3;index=index+1) begin
            value=0;
            repeat(8)begin @(posedge scl);value={value[6:0],sda};end
            if((index==0 && value!=8'h8e) || (index==1 && value!=8'h0a) || (index==2 && value!=expected_value))
                $fatal(1,"Write outside allowlist byte=%0d value=%h",index,value);
            if(index==2)expected[10]=value;
            @(negedge scl);slave_sda_low=1;
            @(posedge scl);@(negedge scl);slave_sda_low=0;
        end
        @(posedge sda);while(scl!==1)@(posedge sda);
    endtask
    initial begin
        #50;@(negedge clk);reset_n=1;
        fork launch();slave_reply(0);join
        finish_case(0);
        for(integer i=0;i<11;i=i+1)begin
            byte_select=i;#10;
            if(status[7:0]!==expected[i])$fatal(1,"Byte mismatch %0d %h",i,status);
        end
        $display("PASS CC_READ_ONLY: pointer zero, repeated START, 11 bytes, ACK/NACK and STOP");
        if(slave_pointer!=11)$fatal(1,"Slave did not retain pointer");
        fork launch();slave_reply(1);join
        finish_case(0);$display("PASS CC_CLOCK_STRETCH_AND_REPEATED_POINTER_RESET");
        launch();finish_case(1);$display("PASS CC_ADDRESS_NACK");
        slave_scl_low=1;launch();wait(status[31]);
        if(status[29:26]!=2 || dut.scl_low || dut.sda_low)$fatal(1,"Busy bus not released");
        slave_scl_low=0;#30;$display("PASS CC_BUSY_BUS_BOUND");
        fork
            launch();
            begin @(negedge sda);@(negedge scl);slave_sda_low=1;wait(status[31]);slave_sda_low=0;end
        join
        finish_case(3);$display("PASS CC_ARBITRATION_RELEASE");
        fork
            launch();
            begin @(negedge sda);@(negedge scl);slave_scl_low=1;wait(status[31]);
                if(status[29:26]!=4 || dut.scl_low || dut.sda_low)$fatal(1,"Watchdog did not release bus");
                slave_scl_low=0;end
        join
        #30;$display("PASS CC_WATCHDOG_RELEASE");
        byte_select=15;#10;if(status[7:0]!=8'hcc || status[19:16]!=4'hc)$fatal(1,"Signature mismatch");
        for(integer operation=1;operation<=4;operation=operation+1)begin
            command=3'(operation);
            fork
                launch();
                slave_write(operation==1?8'h01:operation==2?8'h21:operation==3?8'h20:8'h00);
            join
            finish_case(0);
            command=0;
            fork launch();slave_reply(0);join
            finish_case(0);byte_select=10;#10;
            if(status[7:0]!==expected[10])$fatal(1,"Mode readback mismatch");
        end
        $display("PASS CC_MODE_WRITE_ALLOWLIST: fixed address/register/four values");
        command=7;@(negedge clk);trigger_toggle=~trigger_toggle;repeat(4)@(negedge clk);finish_case(6);
        $display("PASS CC_INVALID_COMMAND_NO_BUS_ACTIVITY");
        ro_trigger=1;repeat(4)@(negedge clk);
        if(!ro_status[31] || ro_status[29:26]!=6 || ro_status[15] || ro_scl!==1 || ro_sda!==1)
            $fatal(1,"Read-only build accepted a write");
        $display("PASS CC_READONLY_BUILD_REJECTS_WRITES");
        $display("CC_READER_TEST_PASS");$finish;
    end
    initial begin #2000000;$fatal(1,"Testbench timeout");end
endmodule
