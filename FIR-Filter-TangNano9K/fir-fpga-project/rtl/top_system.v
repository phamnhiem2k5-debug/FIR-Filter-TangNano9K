`timescale 1ns / 1ps

// =============================================================================
// THAM SỐ HỆ THỐNG
// N_MAX_HW = 200  : Thanh ghi dịch cố định (1 DSP MAC, serial)
//                   Phải đồng bộ với N_MAX_HW trong app.py
// N_ACTIVE        : Số tap thực tế Kaiser (do Python quyết định)
//                   Python gửi đúng N_MAX_HW = 200 hệ số qua UART
//                   (N_ACTIVE tap thực + 200-N_ACTIVE số 0 padding)
// =============================================================================

// =============================================================================
// MODULE 1: BAUDRATE GENERATOR (Tạo nhịp 9600 x 16 cho UART)
// =============================================================================
module bau_gen (
    input  wire clk, rst,
    output reg  enable_16x
);
    // Tính toán: 27,000,000 / (9600 * 16) = 175.78 -> Dùng 175
    reg [7:0] count;
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            count <= 0;
            enable_16x <= 0;
        end else begin
            if (count == 8'd175) begin
                count <= 0;
                enable_16x <= 1'b1;
            end else begin
                count <= count + 1'b1;
                enable_16x <= 1'b0;
            end
        end
    end
endmodule

// =============================================================================
// MODULE 2: SYNCHRONIZER (Chống hiện tượng bất định cho tín hiệu RX)
// =============================================================================
module synchronizer (
    input  wire clk, rst,
    input  wire d_in,
    output reg  d_out
);
    reg q1;
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            q1 <= 1'b1;
            d_out <= 1'b1;
        end else begin
            q1 <= d_in;
            d_out <= q1;
        end
    end
endmodule

// =============================================================================
// MODULE 3: UART RECEIVER (Nhận 8-bit dữ liệu từ PC)
// =============================================================================
module uart_rx (
    input  wire       clk, rst,
    input  wire       rx_pin,
    input  wire       enable_16x,
    output reg  [7:0] d_out,
    output reg        valid_out
);
    reg [2:0] state;
    reg [3:0] sample_cnt;
    reg [2:0] bit_cnt;
    reg [7:0] shift_reg;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            state <= 0; sample_cnt <= 0; bit_cnt <= 0;
            shift_reg <= 0; valid_out <= 0; d_out <= 0;
        end else begin
            valid_out <= 0;
            if (enable_16x) begin
                case (state)
                    3'd0: if (!rx_pin) begin state <= 3'd1; sample_cnt <= 4'd1; end
                    3'd1: if (sample_cnt == 4'd7) begin
                            if (!rx_pin) begin state <= 3'd2; sample_cnt <= 0; bit_cnt <= 0; end
                            else state <= 3'd0;
                          end else sample_cnt <= sample_cnt + 1;
                    3'd2: if (sample_cnt == 4'd15) begin
                            sample_cnt <= 0;
                            shift_reg <= {rx_pin, shift_reg[7:1]};
                            if (bit_cnt == 3'd7) state <= 3'd3; else bit_cnt <= bit_cnt + 1;
                          end else sample_cnt <= sample_cnt + 1;
                    3'd3: if (sample_cnt == 4'd15) begin
                            state <= 3'd4; d_out <= shift_reg; valid_out <= 1'b1;
                          end else sample_cnt <= sample_cnt + 1;
                    3'd4: state <= 3'd0;
                endcase
            end
        end
    end
endmodule

// =============================================================================
// MODULE 4: BYTE PACKER (Gộp 2 byte 8-bit thành 1 word 16-bit)
// =============================================================================
module byte_packer (
    input  wire        clk, rst,
    input  wire [7:0]  d_in,
    input  wire        valid_in,
    output reg  [15:0] d_out,
    output reg         valid_out
);
    reg [7:0] temp_high;
    reg state;
    always @(posedge clk or posedge rst) begin
        if (rst) begin state <= 0; valid_out <= 0; d_out <= 0; end
        else begin
            valid_out <= 0;
            if (valid_in) begin
                if (state == 0) begin temp_high <= d_in; state <= 1; end
                else begin d_out <= {temp_high, d_in}; valid_out <= 1'b1; state <= 0; end
            end
        end
    end
endmodule

// =============================================================================
// MODULE 5: COEFF LOADER — THAY ĐỔI: 39 → 200 tap
// ĐÃ SỬA:
//   [5:0] coeff_addr → [7:0]  (cần 8-bit để địa chỉ 0..199)
//   [5:0] coeff_cnt  → [7:0]
//   coeff_cnt == 38  → coeff_cnt == 8'd199  (luôn nạp 200 hệ số)
//   Python gửi đúng 200 hệ số (N_ACTIVE thực + 200-N_ACTIVE số 0)
// =============================================================================
module coeff_loader (
    input  wire        clk, rst,
    input  wire [15:0] packer_data,
    input  wire        packer_valid,
    output reg  [15:0] coeff_data,
    output reg  [7:0]  coeff_addr,    // ← ĐÃ SỬA: [5:0] → [7:0]
    output reg         coeff_we,
    output reg         coeffs_loaded
);
    reg [7:0] coeff_cnt;              // ← ĐÃ SỬA: [5:0] → [7:0]
    always @(posedge clk or posedge rst) begin
        if (rst) begin coeff_cnt <= 0; coeffs_loaded <= 0; coeff_we <= 0; end
        else begin
            coeff_we <= 0;
            if (!coeffs_loaded && packer_valid) begin
                coeff_data <= packer_data;
                coeff_addr <= coeff_cnt;
                coeff_we   <= 1'b1;
                if (coeff_cnt == 8'd199) coeffs_loaded <= 1'b1;  // ← ĐÃ SỬA: 38 → 199
                else coeff_cnt <= coeff_cnt + 1;
            end
        end
    end
endmodule

// =============================================================================
// MODULE 6: ROM CONTROLLER (Điều phối việc đọc dữ liệu x(n)) — KHÔNG ĐỔI
// =============================================================================
module rom_controller (
    input  wire       clk, rst,
    input  wire       coeffs_loaded,
    input  wire       fir_busy,
    input  wire       fifo_tx_full,
    output reg [9:0]  rom_addr,
    output reg        fir_x_valid
);
    reg [1:0] state;
    reg       done;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            state       <= 0;
            rom_addr    <= 0;
            fir_x_valid <= 0;
            done        <= 0;
        end
        else if (coeffs_loaded && !done) begin
            case (state)
                2'd0: if (!fir_busy && !fifo_tx_full) begin
                          fir_x_valid <= 1'b1;
                          state       <= 2'd1;
                      end

                2'd1: begin
                          fir_x_valid <= 1'b0;
                          if (rom_addr == 10'd999) begin
                              done <= 1'b1;
                          end else begin
                              rom_addr <= rom_addr + 1;
                          end
                          state <= 2'd2;
                      end

                2'd2: if (!fir_busy) state <= 2'd0;
            endcase
        end
    end
endmodule

// =============================================================================
// MODULE 7: ROM X(N) (Chứa 1000 mẫu tín hiệu đầu vào) — KHÔNG ĐỔI
// =============================================================================
module rom_chirp (
    input  wire        clk,
    input  wire [9:0]  addr,
    output reg  [15:0] d_out
);
    reg [15:0] mem [0:999];
    initial $readmemh("input_chirp.hex", mem);
    always @(posedge clk)
        d_out <= mem[addr];
endmodule

module rom_dirac (
    input  wire        clk,
    input  wire [9:0]  addr,
    output reg  [15:0] d_out
);
    reg [15:0] mem [0:999];
    initial $readmemh("input_dirac.hex", mem);
    always @(posedge clk)
        d_out <= mem[addr];
endmodule

module rom_xn (
    input  wire        clk,
    input  wire [9:0]  addr,
    input  wire        mode,      // 0=chirp, 1=dirac
    output wire [15:0] d_out
);
    wire [15:0] d_chirp;
    wire [15:0] d_dirac;

    rom_chirp u_chirp (.clk(clk), .addr(addr), .d_out(d_chirp));
    rom_dirac u_dirac (.clk(clk), .addr(addr), .d_out(d_dirac));

    assign d_out = (mode == 0) ? d_chirp : d_dirac;
endmodule

// =============================================================================
// MODULE 8: FIR FILTER — THAY ĐỔI: 39 → 200 tap
// ĐÃ SỬA:
//   [5:0] coeff_addr → [7:0]
//   h_ram [0:38]     → [0:199]   (200 hệ số, 200×16=3200 FF)
//   x_shift [0:38]   → [0:199]   (200 thanh ghi dịch, 200×16=3200 FF)
//   [5:0] mac_cnt    → [7:0]
//   mac_cnt == 38    → mac_cnt == 8'd199
//   for i = 38..0   → for i = 199..0
//   Bộ tích lũy: [38:0] → [40:0] (mở rộng 2 bit để an toàn với 200 tap)
//     Lý do: max_acc = 200 × 32767² ≈ 2^37.6 → cần 39-bit signed
//             Dùng 41-bit để có thêm 1-bit headroom
// =============================================================================
module fir_filter (
    input  wire        clk, rst,
    input  wire [15:0] coeff_data,
    input  wire [7:0]  coeff_addr,    // ← ĐÃ SỬA: [5:0] → [7:0]
    input  wire        coeff_we,
    input  wire [15:0] x_data,
    input  wire        x_valid,
    output reg  [40:0] y_data,        // ← ĐÃ SỬA: [38:0] → [40:0]
    output reg         y_valid,
    output reg         fir_busy
);
    reg signed [15:0] h_ram   [0:199];  // ← ĐÃ SỬA: [0:38] → [0:199]
    always @(posedge clk) if (coeff_we) h_ram[coeff_addr] <= coeff_data;

    reg signed [15:0] x_shift [0:199];  // ← ĐÃ SỬA: [0:38] → [0:199]
    reg [7:0]  mac_cnt;                 // ← ĐÃ SỬA: [5:0]  → [7:0]
    reg signed [40:0] acc;              // ← ĐÃ SỬA: [38:0] → [40:0]
    reg [1:0]  state;
    integer i;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            fir_busy <= 0; y_valid <= 0; state <= 0;
            for (i = 0; i <= 199; i = i + 1) x_shift[i] <= 0;  // ← ĐÃ SỬA: 38→199
        end else begin
            y_valid <= 0;
            case (state)
                0: if (x_valid) begin
                    fir_busy <= 1'b1;
                    for (i = 199; i > 0; i = i - 1)   // ← ĐÃ SỬA: 38→199
                        x_shift[i] <= x_shift[i-1];
                    x_shift[0] <= x_data; acc <= 0; mac_cnt <= 0; state <= 1;
                end
                1: begin
                    acc <= acc + (x_shift[mac_cnt] * h_ram[mac_cnt]);
                    if (mac_cnt == 8'd199) state <= 2;  // ← ĐÃ SỬA: 38→199
                    else mac_cnt <= mac_cnt + 1;
                end
                2: begin y_data <= acc; y_valid <= 1'b1; fir_busy <= 0; state <= 0; end
            endcase
        end
    end
endmodule

// =============================================================================
// MODULE 9: FIFO BUFFER — THAY ĐỔI: WIDTH 39→41
// =============================================================================
module fifo_buffer #(parameter WIDTH = 41, DEPTH = 1024) (  // ← ĐÃ SỬA: WIDTH 39→41
    input  wire             clk, rst,
    input  wire             w_i, rd_i,
    input  wire [WIDTH-1:0] d_in,
    output reg  [WIDTH-1:0] d_out,
    output wire             full, empty_o
);
    reg [WIDTH-1:0] mem [0:DEPTH-1];
    reg [9:0] wr_ptr, rd_ptr;
    reg [10:0] count;
    assign full = (count == DEPTH);
    assign empty_o = (count == 0);
    always @(posedge clk or posedge rst) begin
        if (rst) begin wr_ptr <= 0; rd_ptr <= 0; count <= 0; end
        else begin
            if (w_i && !full) begin mem[wr_ptr] <= d_in; wr_ptr <= (wr_ptr == DEPTH-1) ? 0 : wr_ptr + 1; end
            if (rd_i && !empty_o) begin d_out <= mem[rd_ptr]; rd_ptr <= (rd_ptr == DEPTH-1) ? 0 : rd_ptr + 1; end
            case ({w_i && !full, rd_i && !empty_o})
                2'b10: count <= count + 1;
                2'b01: count <= count - 1;
            endcase
        end
    end
endmodule

// =============================================================================
// MODULE 10: UNBYTE PACKER — THAY ĐỔI: 39→41 bit, 5→6 byte
// 41-bit word → 6 bytes (byte_cnt 0..5)
// Byte 0: bit[40:33], Byte 1: [32:25], ... Byte 5: [7:0] (chỉ dùng bit [7:0])
// Thực tế dùng 48-bit buffer để dễ xử lý (pad 7 bit MSB = 0)
// =============================================================================
module unbyte_packer (
    input  wire        clk, rst,
    input  wire [40:0] d_in,       // ← ĐÃ SỬA: [38:0] → [40:0]
    input  wire        empty_i,
    output reg         rd_e,
    input  wire        flash_o,
    output reg  [7:0]  d_out,
    output reg         valid_out
);
    reg [47:0] buffer;             // ← ĐÃ SỬA: [39:0] → [47:0] (6 byte aligned)
    reg [2:0]  byte_cnt;
    reg [2:0]  state;
    always @(posedge clk or posedge rst) begin
        if (rst) begin rd_e <= 0; valid_out <= 0; state <= 0; byte_cnt <= 0; end
        else begin
            rd_e <= 0; valid_out <= 0;
            case (state)
                0: if (!empty_i) begin rd_e <= 1'b1; state <= 1; end
                1: state <= 2;
                2: begin buffer <= {7'b0, d_in}; byte_cnt <= 0; state <= 3; end  // 48-bit = 7'b0 + 41-bit
                3: begin d_out <= buffer[47:40]; valid_out <= 1'b1; state <= 4; end
                4: if (flash_o) begin
                    if (byte_cnt == 5) state <= 0;              // ← ĐÃ SỬA: 4→5 (6 bytes)
                    else begin buffer <= buffer << 8; byte_cnt <= byte_cnt + 1; state <= 3; end
                end
            endcase
        end
    end
endmodule

// =============================================================================
// MODULE 11: UART TRANSMITTER — KHÔNG ĐỔI
// =============================================================================
module uart_tx (
    input  wire       clk, rst,
    input  wire [7:0] d_in,
    input  wire       valid_in,
    input  wire       enable_16x,
    output reg        tx_pin,
    output reg        flash_o
);
    reg [2:0] state;
    reg [3:0] bit_cnt, sample_cnt;
    reg [7:0] shift_reg;
    reg tx_busy;

    always @(posedge clk or posedge rst) begin
        if (rst) begin state <= 0; tx_pin <= 1; flash_o <= 0; tx_busy <= 0; sample_cnt <= 0; end
        else begin
            flash_o <= 0;
            if (valid_in && !tx_busy) begin shift_reg <= d_in; tx_busy <= 1; state <= 1; sample_cnt <= 0; end

            if (enable_16x && tx_busy) begin
                if (sample_cnt < 15) sample_cnt <= sample_cnt + 1;
                else begin
                    sample_cnt <= 0;
                    case (state)
                        1: begin tx_pin <= 0; state <= 2; bit_cnt <= 0; end
                        2: begin
                            tx_pin <= shift_reg[0]; shift_reg <= {1'b0, shift_reg[7:1]};
                            if (bit_cnt == 7) state <= 3; else bit_cnt <= bit_cnt + 1;
                        end
                        3: begin tx_pin <= 1; state <= 4; end
                        4: begin tx_busy <= 0; flash_o <= 1; state <= 0; end
                    endcase
                end
            end
        end
    end
endmodule

// =============================================================================
// MODULE 12: TOP SYSTEM — THAY ĐỔI: cập nhật độ rộng wire coeff_addr và y_data
// =============================================================================
module top_system (
    input  wire clk_27mhz,
    input  wire rst_n,
    input  wire key2,
    input  wire rx_pin,
    output wire tx_pin,
    output wire led_done,
    output wire led_mode
);
    wire rst = ~rst_n;

    // ── DEBOUNCE + TOGGLE MODE ──────────────────────────────────────
    reg        key2_d1, key2_d2;
    reg [19:0] db_cnt;
    reg        key2_stable, key2_prev;
    reg        mode;

    always @(posedge clk_27mhz or posedge rst) begin
        if (rst) begin
            key2_d1 <= 1'b1; key2_d2 <= 1'b1;
            db_cnt <= 0; key2_stable <= 1'b1; key2_prev <= 1'b1;
            mode <= 1'b0;
        end else begin
            key2_d1 <= key2;
            key2_d2 <= key2_d1;
            if (key2_d2 != key2_stable) begin
                if (db_cnt == 20'd999_999) begin key2_stable <= key2_d2; db_cnt <= 0; end
                else db_cnt <= db_cnt + 1;
            end else db_cnt <= 0;
            key2_prev <= key2_stable;
            if (key2_prev == 1'b1 && key2_stable == 1'b0) mode <= ~mode;
        end
    end

    assign led_mode = ~mode;
    // ───────────────────────────────────────────────────────────────

    wire enable_uart, rx_sync;
    wire [7:0]  w_rx_data, w_unbyte_data;
    wire        w_rx_valid, w_unbyte_valid, w_uart_tx_flash;
    wire [15:0] w_packer_data, w_coeff_data, w_rom_data;
    wire        w_packer_valid, w_coeff_we, w_coeffs_loaded, w_fir_x_valid, w_fir_busy;
    wire [7:0]  w_coeff_addr;    // ← ĐÃ SỬA: [5:0] → [7:0]
    wire [9:0]  w_rom_addr;
    wire [40:0] w_fir_y_data;    // ← ĐÃ SỬA: [38:0] → [40:0]
    wire [40:0] w_fifo_tx_data;  // ← ĐÃ SỬA: [38:0] → [40:0]
    wire        w_fir_y_valid, w_fifo_tx_full, w_fifo_tx_empty, w_unbyte_rd_e;

    assign led_done = ~w_coeffs_loaded;

    bau_gen        u_bau  (.clk(clk_27mhz), .rst(rst), .enable_16x(enable_uart));
    synchronizer   u_sync (.clk(clk_27mhz), .rst(rst), .d_in(rx_pin), .d_out(rx_sync));
    uart_rx        u_urx  (.clk(clk_27mhz), .rst(rst), .rx_pin(rx_sync), .enable_16x(enable_uart), .d_out(w_rx_data), .valid_out(w_rx_valid));
    byte_packer    u_pack (.clk(clk_27mhz), .rst(rst), .d_in(w_rx_data), .valid_in(w_rx_valid), .d_out(w_packer_data), .valid_out(w_packer_valid));
    coeff_loader   u_ldr  (.clk(clk_27mhz), .rst(rst), .packer_data(w_packer_data), .packer_valid(w_packer_valid), .coeff_data(w_coeff_data), .coeff_addr(w_coeff_addr), .coeff_we(w_coeff_we), .coeffs_loaded(w_coeffs_loaded));
    rom_controller u_ctrl (.clk(clk_27mhz), .rst(rst), .coeffs_loaded(w_coeffs_loaded), .fir_busy(w_fir_busy), .fifo_tx_full(w_fifo_tx_full), .rom_addr(w_rom_addr), .fir_x_valid(w_fir_x_valid));
    rom_xn         u_rom  (.clk(clk_27mhz), .addr(w_rom_addr), .mode(mode), .d_out(w_rom_data));
    fir_filter     u_fir  (.clk(clk_27mhz), .rst(rst), .coeff_data(w_coeff_data), .coeff_addr(w_coeff_addr), .coeff_we(w_coeff_we), .x_data(w_rom_data), .x_valid(w_fir_x_valid), .y_data(w_fir_y_data), .y_valid(w_fir_y_valid), .fir_busy(w_fir_busy));
    fifo_buffer    u_fifo (.clk(clk_27mhz), .rst(rst), .w_i(w_fir_y_valid), .rd_i(w_unbyte_rd_e), .d_in(w_fir_y_data), .d_out(w_fifo_tx_data), .full(w_fifo_tx_full), .empty_o(w_fifo_tx_empty));
    unbyte_packer  u_unb  (.clk(clk_27mhz), .rst(rst), .d_in(w_fifo_tx_data), .empty_i(w_fifo_tx_empty), .rd_e(w_unbyte_rd_e), .flash_o(w_uart_tx_flash), .d_out(w_unbyte_data), .valid_out(w_unbyte_valid));
    uart_tx        u_utx  (.clk(clk_27mhz), .rst(rst), .d_in(w_unbyte_data), .valid_in(w_unbyte_valid), .enable_16x(enable_uart), .tx_pin(tx_pin), .flash_o(w_uart_tx_flash));

endmodule
