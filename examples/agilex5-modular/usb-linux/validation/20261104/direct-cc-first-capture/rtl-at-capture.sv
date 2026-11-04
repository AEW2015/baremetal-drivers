// Read-only HD3SS3220 diagnostic. The only transmitted byte is 0x8f:
// address 0x47 with READ set. No target register/configuration writes exist.
module cc_reader #(
    parameter integer TICK_CYCLES = 2500,  // 100 MHz: 10 kHz SCL, four phases/bit
    parameter integer MAX_CYCLES = 4000000,
    parameter integer IDLE_WAIT_CYCLES = 200000
) (
    input  wire clk,
    input  wire reset_n,
    input  wire trigger_toggle,
    input  wire [3:0] byte_select,
    input  wire [2:0] usb_inputs,  // fault_n, VBUS detector, Type-C ID
    inout  wire cc_scl,
    inout  wire cc_sda,
    output wire [31:0] status
);
    typedef enum logic [4:0] {
        IDLE, BUS_FREE, START, TX_SETUP, TX_RAISE, TX_HIGH,
        ACK_SETUP, ACK_RAISE, ACK_HIGH, RX_SETUP, RX_RAISE, RX_HIGH,
        MACK_SETUP, MACK_RAISE, MACK_HIGH, STOP_LOW, STOP_RAISE,
        STOP_HIGH, STOP_RELEASE
    } state_t;
    state_t state;
    logic scl_low, sda_low, busy, done, previous_trigger;
    logic [3:0] error_code;
    logic [2:0] bit_index;
    logic [3:0] byte_index;
    logic [6:0] shift_in;
    logic [7:0] received [0:10];
    localparam integer DIV_WIDTH = $clog2(TICK_CYCLES+1);
    localparam integer WATCH_WIDTH = $clog2(MAX_CYCLES+1);
    logic [DIV_WIDTH-1:0] divider;
    logic [WATCH_WIDTH-1:0] watchdog;
    logic [2:0] idle_ticks;
    // Both bus inputs and the existing USB indicator pins are asynchronous.
    (* altera_attribute = "-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *)
    logic [4:0] input_meta, input_sync;
    wire scl_in = input_sync[1];
    wire sda_in = input_sync[0];
    wire [7:0] address_read = 8'h8f;
    wire [7:0] selected = byte_select == 15 ? 8'hcc :
                          done && error_code == 0 && byte_select < 11 ? received[byte_select] : 8'h00;
    assign cc_scl = scl_low ? 1'b0 : 1'bz;
    assign cc_sda = sda_low ? 1'b0 : 1'bz;
    assign status = {done, busy, error_code, input_sync[4:2], scl_in, sda_in,
                     1'b0, 4'hc, 8'h00, selected};

    always_ff @(posedge clk) begin
        input_meta <= {usb_inputs, cc_scl, cc_sda};
        input_sync <= input_meta;
        if (!reset_n) begin
            state <= IDLE;
            scl_low <= 0;
            sda_low <= 0;
            busy <= 0;
            done <= 0;
            error_code <= 0;
            previous_trigger <= 0;
            divider <= 0;
            watchdog <= 0;
            idle_ticks <= 0;
            bit_index <= 7;
            byte_index <= 0;
            shift_in <= 0;
        end else begin
            previous_trigger <= trigger_toggle;
            if (busy) watchdog <= watchdog + 1'b1;
            if (divider == DIV_WIDTH'(TICK_CYCLES-1)) divider <= 0;
            else divider <= divider + 1'b1;
            // An expired transaction releases both wires. No forced STOP on a
            // busy/contended bus: another controller may own the transaction.
            if (busy && (watchdog == WATCH_WIDTH'(MAX_CYCLES-1) ||
                         (state == BUS_FREE && watchdog == WATCH_WIDTH'(IDLE_WAIT_CYCLES-1)))) begin
                error_code <= state == BUS_FREE ? 4'd2 : 4'd4;
                scl_low <= 0;
                sda_low <= 0;
                busy <= 0;
                done <= 1;
                state <= IDLE;
            end else if (state == IDLE && trigger_toggle != previous_trigger) begin
                busy <= 1;
                done <= 0;
                error_code <= 0;
                watchdog <= 0;
                idle_ticks <= 0;
                divider <= 0;
                state <= BUS_FREE;
            end else if (divider == DIV_WIDTH'(TICK_CYCLES-1)) begin
                case (state)
                    IDLE: begin scl_low <= 0; sda_low <= 0; end
                    BUS_FREE: begin
                        if (scl_in && sda_in) begin
                            if (idle_ticks == 3) begin sda_low <= 1; state <= START; end
                            else idle_ticks <= idle_ticks + 1'b1;
                        end else idle_ticks <= 0;
                    end
                    START: begin scl_low <= 1; bit_index <= 7; state <= TX_SETUP; end
                    TX_SETUP: begin sda_low <= !address_read[bit_index]; state <= TX_RAISE; end
                    TX_RAISE: begin scl_low <= 0; state <= TX_HIGH; end
                    TX_HIGH: if (scl_in) begin
                        if (address_read[bit_index] && !sda_in) begin
                            error_code <= 3; busy <= 0; done <= 1;
                            scl_low <= 0; sda_low <= 0; state <= IDLE;
                        end else begin
                            scl_low <= 1;
                            if (bit_index == 0) state <= ACK_SETUP;
                            else begin bit_index <= bit_index - 1'b1; state <= TX_SETUP; end
                        end
                    end
                    ACK_SETUP: begin sda_low <= 0; state <= ACK_RAISE; end
                    ACK_RAISE: begin scl_low <= 0; state <= ACK_HIGH; end
                    ACK_HIGH: if (scl_in) begin
                        scl_low <= 1;
                        if (sda_in) begin error_code <= 1; state <= STOP_LOW; end
                        else begin byte_index <= 0; bit_index <= 7; shift_in <= 0; state <= RX_SETUP; end
                    end
                    RX_SETUP: begin sda_low <= 0; state <= RX_RAISE; end
                    RX_RAISE: begin scl_low <= 0; state <= RX_HIGH; end
                    RX_HIGH: if (scl_in) begin
                        shift_in <= {shift_in[5:0], sda_in};
                        scl_low <= 1;
                        if (bit_index == 0) begin
                            received[byte_index] <= {shift_in[6:0], sda_in};
                            state <= MACK_SETUP;
                        end else begin bit_index <= bit_index - 1'b1; state <= RX_SETUP; end
                    end
                    MACK_SETUP: begin sda_low <= byte_index != 10; state <= MACK_RAISE; end
                    MACK_RAISE: begin scl_low <= 0; state <= MACK_HIGH; end
                    MACK_HIGH: if (scl_in) begin
                        if (byte_index == 10 && !sda_in) begin
                            error_code <= 3; busy <= 0; done <= 1;
                            scl_low <= 0; sda_low <= 0; state <= IDLE;
                        end else begin
                            scl_low <= 1;
                            if (byte_index == 10) state <= STOP_LOW;
                            else begin byte_index <= byte_index + 1'b1; bit_index <= 7; state <= RX_SETUP; end
                        end
                    end
                    STOP_LOW: begin scl_low <= 1; sda_low <= 1; state <= STOP_RAISE; end
                    STOP_RAISE: begin scl_low <= 0; state <= STOP_HIGH; end
                    STOP_HIGH: if (scl_in) begin sda_low <= 0; state <= STOP_RELEASE; end
                    STOP_RELEASE: if (scl_in && sda_in) begin busy <= 0; done <= 1; state <= IDLE; end
                    default: begin
                        scl_low <= 0; sda_low <= 0; busy <= 0; done <= 1;
                        error_code <= 5; state <= IDLE;
                    end
                endcase
            end
        end
    end
endmodule
