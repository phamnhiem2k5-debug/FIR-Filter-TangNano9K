import streamlit as st
import numpy as np
from scipy import signal
from scipy.fft import fft, fftfreq
import matplotlib.pyplot as plt

# ==========================================
# 1. CẤU HÌNH GIAO DIỆN
# ==========================================
st.set_page_config(page_title="FIR DSP Master - Tang Nano 9K Edition", page_icon="📟", layout="wide")

st.title("📟 FIR Filter: Tối ưu hóa Tang Nano 9K (20 DSPs)")

st.sidebar.header("⚙️ Cấu hình Phần cứng (FPGA)")
# Cố định giới hạn cho Tang Nano 9K: 20 bộ nhân đối xứng = 39 Taps
MAX_ALLOWED_TAPS = 39 
st.sidebar.info(f"Giới hạn phần cứng: {MAX_ALLOWED_TAPS} Taps (20 DSPs)")

# ==========================================
# 2. NHẬP THÔNG SỐ & RÀNG BUỘC THÔNG MINH
# ==========================================
st.subheader("🛠️ Cấu hình Bộ lọc")
col_in1, col_in2 = st.columns(2)

with col_in1:
    fs = st.number_input("Fs (Hz) - Tần số lấy mẫu", value=8000, step=100)
    fp = st.slider("Fpass (Hz) - Dải thông", 100, int(fs/2 - 200), 1000)
    
    # Ràng buộc Delta F / Fs >= 0.0233 để A >= 21dB
    min_delta_f = int(0.0233 * fs) + 1
    fst = st.slider("Fstop (Hz) - Dải chặn", int(fp + min_delta_f), int(fs/2 - 50), int(fp + min_delta_f + 400))

with col_in2:
    # TỰ ĐỘNG TÍNH A để N luôn xấp xỉ 39 (Tối ưu tài nguyên)
    delta_f = fst - fp
    a_auto = (MAX_ALLOWED_TAPS * 14.36 * (delta_f / fs)) + 7.95
    # Giới hạn A trong khoảng thực tế 21 - 80dB
    a = max(21.0, min(80.0, a_auto))
    
    st.metric("Suy hao tính toán (A)", f"{a:.2f} dB", help="Tự động tính để N <= 39")
    bits = st.number_input("Word Length (Bits)", value=16, disabled=True)

st.markdown("### 🌊 Cấu hình Tín hiệu Test")
col_sig1, col_sig2 = st.columns(2)
with col_sig1:
    f_sig = st.number_input("Signal freq (Hz) - Sóng sạch", value=100)
with col_sig2:
    f_noise = st.number_input("Noise freq (Hz) - Sóng nhiễu", value=3000)

# ==========================================
# 🛡️ KIỂM TRA ĐIỀU KIỆN NYQUIST
# ==========================================
f_max_system = max(f_sig, f_noise)
if fs < 2 * f_max_system:
    st.error(f"❌ LỖI NYQUIST: Fs ({fs}Hz) phải lớn hơn 2 lần tần số cao nhất ({f_max_system}Hz)!")
    st.warning(f"👉 Vui lòng tăng Fs lên tối thiểu {2 * f_max_system + 1}Hz để tránh chồng phổ.")
    st.stop()

def float_to_hex2s(val, bits_len):
    return format(int(val) & ((1 << bits_len) - 1), f'0{bits_len//4}x')

# ==========================================
# # ==========================================
# 3. THIẾT KẾ & VẼ ĐÁP ỨNG TẦN SỐ (SYTHESIS RESPONSE)
# ==========================================
# Khởi tạo trạng thái thiết kế nếu chưa có
if 'design_done' not in st.session_state:
    st.session_state.design_done = False

if st.button("✨ Tổng hợp & Thiết kế Bộ lọc", type="primary", use_container_width=True):
    width = (fst - fp) / (fs / 2)
    n_ideal, beta = signal.kaiserord(a, width)
    if n_ideal % 2 == 0: n_ideal += 1
    
    # Chốt chặn cuối cùng theo phần cứng
    n = min(n_ideal, MAX_ALLOWED_TAPS)

    # Thiết kế hệ số
    h = signal.firwin(n, (fp + fst)/2, window=('kaiser', beta), fs=fs)
    scale = 2**(bits - 1) - 1
    hq = np.clip(np.round(h * scale), -scale, scale).astype(int)

    # Tạo tín hiệu test
    t = np.arange(0, 1000/fs, 1/fs)
    sig_raw = 0.5 * np.sin(2 * np.pi * f_sig * t) + 0.5 * np.sin(2 * np.pi * f_noise * t)
    sig_q = np.clip(np.round(sig_raw * scale), -scale, scale).astype(int)
    clean_sig_q = np.clip(np.round(0.5 * np.sin(2 * np.pi * f_sig * t) * scale), -scale, scale).astype(int)

    # Lưu mọi kết quả vào session_state
    st.session_state.update({
        'hq': hq, 'sig_q': sig_q, 'clean_sig_q': clean_sig_q,
        'n': n, 'fs': fs, 'bits': bits, 'f_sig': f_sig, 'f_noise': f_noise, 'a': a,
        'h_float': h, 'design_done': True
    })

# ==========================================
# 4. HIỂN THỊ KẾT QUẢ & XUẤT FILE (KHỐI NÀY SẼ GIỮ HÌNH)
# ==========================================
if st.session_state.design_done:
    # Lấy dữ liệu từ bộ nhớ ra
    n = st.session_state['n']
    h = st.session_state['h_float']
    fs_val = st.session_state['fs']
    a_val = st.session_state['a']

    # Vẽ đồ thị đáp ứng tần số
    st.subheader("📊 Đáp ứng tần số Bộ lọc (Magnitude Response)")
    w, hh = signal.freqz(h, worN=8000, fs=fs_val)
    
    fig_res, ax_res = plt.subplots(figsize=(12, 4))
    ax_res.plot(w, 20 * np.log10(np.abs(hh) + 1e-10), color='#3498db', linewidth=2)
    ax_res.axvline(fp, color='green', linestyle='--', alpha=0.5, label='Fpass')
    ax_res.axvline(fst, color='red', linestyle='--', alpha=0.5, label='Fstop')
    ax_res.set_ylim([-a_val - 20, 5])
    ax_res.set_ylabel("Biên độ (dB)")
    ax_res.set_xlabel("Tần số (Hz)")
    ax_res.grid(True, alpha=0.2)
    ax_res.legend()
    st.pyplot(fig_res)

    st.success(f"✅ Đã tối ưu cho Tang Nano 9K: {n} Taps | DSPs sử dụng: 20 bộ.")
    
    st.subheader("📥 Tải tệp tin nạp cho phần cứng")
    c1, c2, c3 = st.columns(3)
    
    # Logic download buttons
    hex_coeffs = "\n".join([float_to_hex2s(v, st.session_state['bits']) for v in st.session_state['hq']])
    hex_input = "\n".join([float_to_hex2s(v, st.session_state['bits']) for v in st.session_state['sig_q']])
    vh_config = f"parameter TAPS = {n};"

    c1.download_button("1. coeff.hex", hex_coeffs, "coeff.hex")
    c2.download_button("2. input.hex", hex_input, "input.hex")
    c3.download_button("3. taps_config.vh", vh_config, "taps_config.vh")

    # Tiếp tục phần Verify phía dưới...
    # ==========================================
    # 5. VERIFY (CHUẨN Q-FORMAT & BÙ TRỄ)
    # ==========================================
    st.markdown("---")
    st.header("🔍 Xác minh độ chính xác phần cứng (Verify)")
    uploaded = st.file_uploader("📤 Tải lên file output.hex từ Vivado (Biến data_out 38-bit)", type=["hex"])

    if uploaded:
        # A. ĐỌC FILE & DECODE 38-BIT (Chống sai dấu)
        content = uploaded.getvalue().decode().splitlines()
        out_raw = [int(x.strip(), 16) for x in content if x.strip()]

        out_data = []
        for v in out_raw:
            v_38 = v & ((1 << 38) - 1)
            if v_38 >= (1 << 37):
                out_data.append(v_38 - (1 << 38))
            else:
                out_data.append(v_38)
        out_data = np.array(out_data) # Đây là kết quả tích lũy Q30 của FPGA

        # B. THIẾT LẬP THÔNG SỐ TOÁN HỌC
        Q_IN = st.session_state['bits'] - 1   # Ví dụ 15
        Q_OUT = Q_IN * 2                      # Ví dụ 30 (Vì Q15 * Q15 = Q30)
        
        hq = st.session_state['hq']
        sig_q = st.session_state['sig_q']
        clean_sig_q = st.session_state['clean_sig_q']
        
        # Bù Group Delay
        delay = (len(hq) - 1) // 2

        # C. XỬ LÝ FPGA (Cắt delay & Chuyển về Float)
        out_data_delayed = out_data[delay:] 
        fpga_float = out_data_delayed / (1 << Q_OUT)

        # D. XỬ LÝ PYTHON GOLDEN (Mô phỏng y hệt FPGA)
        y_python_full = np.convolve(sig_q, hq) 
        y_python_delayed = y_python_full[delay : delay + len(out_data_delayed)]
        python_float = y_python_delayed / (1 << Q_OUT)
        
        # Sóng hiển thị
        clean_sig_float = clean_sig_q[:len(out_data_delayed)] / (1 << Q_IN)
        noisy_sig_float = sig_q[:len(out_data_delayed)] / (1 << Q_IN)

        # E. CHẤM ĐIỂM (FPGA so với PYTHON GOLDEN)
        error = fpga_float - python_float
        mse = np.mean(error**2)
        max_err = np.max(np.abs(error))

        col_m1, col_m2 = st.columns(2)
        col_m1.metric("MSE (Sai số trung bình)", f"{mse:.12f}")
        col_m2.metric("Max Error (Độ lệch lớn nhất)", f"{max_err:.10f}")

        if max_err < 1e-4: 
            st.success("🎯 TUYỆT VỜI! Mạch FPGA chạy chuẩn xác đến từng bit so với Python.")
        else:
            st.warning("⚠️ LỆCH KẾT QUẢ! Kiểm tra lại file coeff.hex hoặc khai báo bit trong Verilog.")

        # F. VẼ ĐỒ THỊ 3 ĐƯỜNG
        st.subheader(f"📈 So sánh Tín hiệu (Chuẩn hóa Float biên độ 1.0)")
        zoom = min(len(fpga_float), 400)
        
        fig, ax = plt.subplots(figsize=(14, 6))
        ax.plot(noisy_sig_float[:zoom], color='gray', alpha=0.3, label='1. Đầu vào (Nhiễu)')
        ax.plot(clean_sig_float[:zoom], color='#2ecc71', linewidth=3, label='2. Lý thuyết (Sóng 100Hz mong muốn)')
        ax.plot(fpga_float[:zoom], color='#e74c3c', linewidth=2, linestyle='--', label='3. Thực tế FPGA (Đã bù pha & Scale)')
        
        ax.set_title(f"KIỂM CHỨNG KẾT QUẢ: FPGA (Q{Q_OUT}) vs LÝ THUYẾT", fontweight='bold')
        ax.set_xlabel("Mẫu dữ liệu (Samples)")
        ax.set_ylabel("Biên độ (Float)")
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3, linestyle='--')
        st.pyplot(fig)

        # ==========================================
        # ==========================================
        # G. PHÂN TÍCH PHỔ TOÀN DIỆN (ADAPTIVE FFT)
        # ==========================================
        with st.expander("📊 Phân tích Phổ Tần Số (Bản gốc cho mọi trường hợp)", expanded=True):
            # 1. Chuẩn bị dữ liệu
            N = len(fpga_float)
            fs_val = st.session_state['fs']
            f_s = st.session_state['f_sig']
            f_n = st.session_state['f_noise']
            a_target = st.session_state.get('a', 30)
            
            # Tính FFT thô (Không dùng Window để soi đúng thực tế)
            xf = fftfreq(N, 1/fs_val)[:N//2]
            yf_in = fft(noisy_sig_float[:N])
            yf_out = fft(fpga_float[:N])
            
            # Chuyển sang dB
            mag_in = 20 * np.log10(np.abs(yf_in[:N//2]) + 1e-10)
            mag_out = 20 * np.log10(np.abs(yf_out[:N//2]) + 1e-10)
            
            # 2. CHUẨN HÓA THÔNG MINH
            # Lấy đỉnh của tín hiệu vào làm mốc 0dB
            peak_ref = np.max(mag_in)
            mag_in -= peak_ref
            mag_out -= peak_ref

            # 3. THIẾT LẬP ĐỒ THỊ TỰ THÍCH NGHI
            fig_fft, ax_fft = plt.subplots(figsize=(14, 6))
            
            # Vẽ phổ
            ax_fft.plot(xf, mag_in, color='gray', alpha=0.4, label="Phổ Input (Trước lọc)")
            ax_fft.plot(xf, mag_out, color='#e74c3c', linewidth=1.5, label="Phổ FPGA Output (Sau lọc)")
            
            # Kẻ đường giới hạn A thiết kế (Quan trọng để soi lỗi)
            ax_fft.axhline(-a_target, color='blue', linestyle='--', linewidth=2, 
                           label=f"Ngưỡng chặn lý thuyết (-{a_target:.1f} dB)")
            
            # Đánh dấu các cột tần số
            ax_fft.axvline(f_s, color='green', linestyle=':', alpha=0.8, label=f"Sóng sạch ({f_s}Hz)")
            ax_fft.axvline(f_n, color='black', linestyle=':', alpha=0.8, label=f"Sóng nhiễu ({f_n}Hz)")
            
            # --- TỰ ĐỘNG CẤU HÌNH TRỤC ---
            # Trục Y: Luôn bao quát từ +5dB xuống thấp hơn mức chặn 20dB
            y_min = -max(a_target + 30, 60) # Tối thiểu nhìn xuống -60dB
            ax_fft.set_ylim([y_min, 10])
            
            # Trục X: Tự động zoom vào vùng có tín hiệu để dễ nhìn
            x_limit = min(fs_val/2, max(f_s, f_n) * 1.5)
            ax_fft.set_xlim([0, x_limit])
            
            # 4. TRANG TRÍ CHUYÊN NGHIỆP
            ax_fft.set_title(f"FFT VERIFICATION (N={st.session_state.get('n', '??')}) - RAW DATA", fontweight='bold')
            ax_fft.set_xlabel("Tần số (Hz)")
            ax_fft.set_ylabel("Biên độ phổ chuẩn hóa (dB)")
            ax_fft.legend(loc='upper right', frameon=True, shadow=True)
            ax_fft.grid(True, which='both', linestyle='--', alpha=0.5)
            
            # Thêm chú thích giá trị thực tế tại điểm nhiễu
            # Tìm biên độ thực tế tại tần số nhiễu để so sánh
            idx_noise = np.argmin(np.abs(xf - f_n))
            actual_atten = mag_out[idx_noise]
            ax_fft.annotate(f'Thực tế tại f_noise: {actual_atten:.2f} dB', 
                            xy=(f_n, actual_atten), xytext=(f_n, actual_atten+10),
                            arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=5))

            st.pyplot(fig_fft)