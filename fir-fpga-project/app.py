import streamlit as st
import numpy as np
from scipy import signal
from scipy.signal import find_peaks, chirp
from scipy.fft import fft, fftfreq
import matplotlib.pyplot as plt
import pandas as pd

# ==========================================
# CẤU HÌNH GIAO DIỆN
st.set_page_config(
    page_title="FPGA FIR Design & Verification",
    layout="wide"
)


st.markdown("""
<div style="
    text-align:center;
    padding:20px 0 25px 0;
">

<div style="
    display:inline-block;
    padding:6px 14px;
    border-radius:999px;
    background:#e8f2ff;
    color:#0b61c9;
    font-size:14px;
    font-weight:600;
    margin-bottom:10px;">
    Tang Nano 9K | FIR Kaiser
</div>

<h1 style="
    font-size:42px;
    font-weight:800;
    margin-bottom:8px;
    color:#202124;">
    FPGA FIR Design & Verification
</h1>

<div style="
    font-size:20px;
    color:#666;
    font-weight:400;">
    Thiết kế • Mô phỏng • Xác minh phần cứng
</div>

</div>
""", unsafe_allow_html=True)

st.markdown("""
<style>
    .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    h1, h2, h3 {letter-spacing: -0.02em;}
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e8e8e8;
        padding: 14px 16px;
        border-radius: 14px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }
</style>
""", unsafe_allow_html=True)

MAX_ALLOWED_TAPS = 39
st.sidebar.markdown(
    "**Luồng sử dụng:**\n"
    "1. Nhập thông số bộ lọc\n"
    "2. Nhấn **Kích hoạt Tính toán & Thiết kế Bộ lọc**\n"
    "3. Xem kết quả & tải file\n"
    "4. Nạp vào FPGA, lấy output\n"
    "5. Upload output để xác minh"
)


def float_to_hex2s(val, bits_len):
    return format(int(val) & ((1 << bits_len) - 1), f'0{bits_len//4}x')

# BLOCK 1 — CẤU HÌNH BỘ LỌC
# ==========================================

st.markdown("##  Bước 1 — Cấu hình Thông số Bộ lọc")
st.markdown("Nhập trực tiếp các giá trị tần số. Biểu đồ phân bổ băng thông sẽ tự động cập nhật theo thời gian thực.")

# ── Tính sơ bộ fs ở scope ngoài để col_right không bị NameError ─────────────
# Streamlit chạy tuần tự (col_left trước col_right) nhưng khai báo rõ ràng
# giúp linter và tránh lỗi nếu cấu trúc thay đổi sau này.
_fs_default = st.session_state.get('_fs_tmp', 8000)
fs  = _fs_default
fs2 = int(fs / 2)

# ── 2 cột chính: trái (inputs + bar) | phải (metrics + nút) ─────────────────
col_left, col_right = st.columns([3, 2], gap="large")

# ════════════════════════════════════════════════════════════════════════════
# CỘT TRÁI — Fs, Fpass, Fstop, thanh băng thông, validation
# ════════════════════════════════════════════════════════════════════════════
with col_left:

    fs = st.number_input(
        "Fs (Hz) — Tần số lấy mẫu vật lý",
        min_value=4000, max_value=192000, value=8000, step=100,
        help="Thông thường: 8 000 / 44 100 / 48 000 Hz"
    )
    st.session_state['_fs_tmp'] = fs  # cache cho lần re-run tiếp theo

    fs2         = int(fs / 2)
    min_delta_f = int(0.0233 * fs) + 1

    fp = st.number_input(
        f"Fpass (Hz) — Tần số cắt dải thông   _(Cho phép: 100 – {fs2 - 200} Hz)_",
        min_value=100, max_value=fs2 - 200, value=min(1000, fs2 - 200),
        step=10,
        help=f"Tần số cao nhất còn được giữ lại. Tối đa = fs/2 − 200 = {fs2 - 200} Hz"
    )

    fst_min     = int(fp + min_delta_f)
    fst_max     = fs2 - 50
    fst_default = min(int(fp + min_delta_f + 400), fst_max)

    fst = st.number_input(
        f"Fstop (Hz) — Tần số cắt dải chặn   _(Cho phép: {fst_min} – {fst_max} Hz)_",
        min_value=fst_min, max_value=fst_max,
        value=max(fst_min, min(fst_default, fst_max)),
        step=10,
        help=f"Tần số bắt đầu vùng bị triệt tiêu. Tối thiểu = Fpass + Δf_min = {fst_min} Hz"
    )

    # Validation
    errors = []
    if fp >= fs2:
        errors.append(f"Fpass ({fp} Hz) phải nhỏ hơn fs/2 ({fs2} Hz).")
    if fst >= fs2:
        errors.append(f"Fstop ({fst} Hz) phải nhỏ hơn fs/2 ({fs2} Hz).")
    if fst <= fp:
        errors.append(f"Fstop ({fst} Hz) phải lớn hơn Fpass ({fp} Hz).")
    for e in errors:
        st.error(e)

    delta_f = fst - fp
    if delta_f < 200 and not errors:
        st.warning("Dải chuyển tiếp quá hẹp — suy hao thực tế sẽ thấp hơn thiết kế.")

    # ── Thanh băng thông ──────────────────────────────────────────────────────
    if not errors:
        pass_pct  = fp      / fs2 * 100
        trans_pct = delta_f / fs2 * 100
        stop_pct  = max(0, 100 - pass_pct - trans_pct)

        label_pass  = "Dải thông"       if pass_pct  > 12 else ""
        label_trans = "Dải chuyển tiếp" if trans_pct > 10 else ""
        label_stop  = "Dải chặn"        if stop_pct  > 12 else ""

        fpass_fs = max(8, min(11, int(pass_pct  * 1.8)))
        fstop_fs = max(8, min(11, int(trans_pct * 1.8)))

        fstop_pct  = pass_pct + trans_pct
        gap_to_end = 100 - fstop_pct          # % còn lại từ Fstop → fs/2
        gap_fp_fst = fstop_pct - pass_pct     # % khoảng cách Fpass → Fstop

        # Thanh rộng ~600px → 1% ≈ 6px; label "Fstop XXXX Hz" ≈ 75px ≈ 12.5%
        # label "fs/2 XXXX Hz" ≈ 65px ≈ 10.8%  →  cần tổng ~23% để không đè
        LABEL_HALF   = 7.5   # nửa chiều rộng label Fstop (%)
        END_LABEL_W  = 11.0  # chiều rộng label fs/2 (%)
        FPASS_HALF   = 7.0   # nửa chiều rộng label Fpass (%)

        # Fstop đè fs/2 khi khoảng cách < tổng nửa 2 label
        fstop_row2 = gap_to_end < (LABEL_HALF + END_LABEL_W)
        # Fpass đè Fstop khi khoảng cách < tổng nửa 2 label
        fpass_row2 = gap_fp_fst < (FPASS_HALF + LABEL_HALF)

        label_row_height = "36px" if (fstop_row2 or fpass_row2) else "20px"
        fstop_top  = "18px" if fstop_row2 else "0"
        fpass_top  = "18px" if fpass_row2 else "0"

        bar_html = (
            '<div style="margin-top:8px;">'
            '<div style="font-size:12px;color:gray;margin-bottom:6px;">'
            f'Phân bổ băng thông (0 Hz → {fs2} Hz)'
            '</div>'
            '<div style="display:flex;height:28px;border-radius:8px;overflow:hidden;border:0.5px solid #ddd;">'
            f'<div style="width:{pass_pct:.1f}%;background:#EAF3DE;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:500;color:#3B6D11;">{label_pass}</div>'
            f'<div style="width:{trans_pct:.1f}%;background:#F1EFE8;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:500;color:#5F5E5A;">{label_trans}</div>'
            f'<div style="width:{stop_pct:.1f}%;background:#FCEBEB;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:500;color:#A32D2D;">{label_stop}</div>'
            '</div>'
            f'<div style="position:relative;height:{label_row_height};font-size:11px;color:gray;margin-top:4px;">'
            '<span style="position:absolute;left:0;top:0;">0 Hz</span>'
            f'<span style="position:absolute;left:{pass_pct:.1f}%;top:{fpass_top};transform:translateX(-50%);'
            f'font-size:{fpass_fs}px;color:#3B6D11;font-weight:500;">Fpass {fp} Hz</span>'
            f'<span style="position:absolute;left:{fstop_pct:.1f}%;top:{fstop_top};transform:translateX(-50%);'
            f'font-size:{fstop_fs}px;color:#A32D2D;font-weight:500;">Fstop {fst} Hz</span>'
            f'<span style="position:absolute;right:0;top:0;">fs/2 {fs2} Hz</span>'
            '</div>'
            '</div>'
        )
        st.markdown(bar_html, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# CỘT PHẢI — Metric cards + nút kích hoạt
# ════════════════════════════════════════════════════════════════════════════
with col_right:
    delta_f = fst - fp
    a_auto  = (MAX_ALLOWED_TAPS * 14.36 * (delta_f / fs)) + 7.95
    a       = max(21.0, a_auto)
    bits    = 16

    st.markdown(f"""
<style>
.metric-card {{
    background: var(--background-color, #ffffff);
    border: 0.5px solid #e8e8e8;
    border-radius: 14px;
    padding: 18px 20px;
    margin-bottom: 10px;
}}
.metric-label {{
    font-size: 13px;
    color: gray;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 5px;
}}
.metric-value {{
    font-size: 28px;
    font-weight: 500;
    line-height: 1.2;
}}
</style>

<div class="metric-card">
  <div class="metric-label">
    Mức suy hao stopband tối thiểu mong muốn (A)
    <span title="Tính theo công thức Kaiser từ Δf và số Taps"
          style="cursor:help;color:#bbb;font-size:12px;">ⓘ</span>
  </div>
  <div class="metric-value">{a:.2f} dB</div>
</div>

<div class="metric-card">
  <div class="metric-label">
    Số Tap bộ lọc
    <span title="Cố định theo giới hạn 20 DSP của Tang Nano 9K"
          style="cursor:help;color:#bbb;font-size:12px;">ⓘ</span>
  </div>
  <div class="metric-value">{MAX_ALLOWED_TAPS}</div>
</div>

<div class="metric-card">
  <div class="metric-label">Độ rộng bit hệ số</div>
  <div class="metric-value">16-bit Q15</div>
</div>
""", unsafe_allow_html=True)



# ── Nút kích hoạt full-width, chính giữa trang ───────────────────────────────
st.markdown("")
input_valid = len(errors) == 0
activate = st.button(
    "✨ Kích hoạt Tính toán & Thiết kế Bộ lọc",
    type="primary",
    use_container_width=True,
    disabled=not input_valid
)

# ════════════════════════════════════════════════════════════════════════════
# XỬ LÝ SAU KHI BẤM NÚT
# ════════════════════════════════════════════════════════════════════════════
if 'design_done' not in st.session_state:
    st.session_state.design_done = False

if activate:
    width = (fst - fp) / (fs / 2)
    _, beta = signal.kaiserord(a, width)
    n = MAX_ALLOWED_TAPS

    h = signal.firwin(n, (fp + fst) / 2, window=('kaiser', beta), fs=fs)
    scale = 2 ** (bits - 1) - 1
    hq = np.clip(np.round(h * scale), -scale, scale).astype(int)

    t = np.arange(0, 200 / fs, 1 / fs)
    clean_sig_raw = 0.5 * chirp(t, f0=0, f1=fp, t1=t[-1], method='linear')
    noise_sig_raw = 0.5 * chirp(t, f0=fst, f1=fs / 2, t1=t[-1], method='linear')
    sig_raw = clean_sig_raw + noise_sig_raw

    sig_q       = np.clip(np.round(sig_raw       * scale), -scale, scale).astype(int)
    clean_sig_q = np.clip(np.round(clean_sig_raw * scale), -scale, scale).astype(int)

    st.session_state.update({
        'hq': hq, 'sig_q': sig_q, 'clean_sig_q': clean_sig_q,
        'n': n, 'fs': fs, 'fp': fp, 'fst': fst,
        'bits': bits, 'a': a, 'h_float': h, 'design_done': True
    })


# ==========================================
# BLOCK 2 — KẾT QUẢ THIẾT KẾ BỘ LỌC
# ==========================================
if st.session_state.design_done:
    n       = st.session_state['n']
    h       = st.session_state['h_float']
    fs_val  = st.session_state['fs']
    fp_val  = st.session_state['fp']
    fst_val = st.session_state['fst']
    a_val   = st.session_state['a']

    st.markdown("---")
    st.markdown("##  Bước 2 — Đáp ứng lý thuyết của Bộ lọc")


    w_rad, hh = signal.freqz(h, worN=8000)
    hh_mag    = np.abs(hh)
    w         = w_rad * fs_val / (2 * np.pi)

    M        = len(h) - 1
    hh_real  = np.real(hh * np.exp(1j * w_rad * M / 2))

    pass_mask = w <= fp_val
    stop_mask = w >= fst_val
    pb_max  = np.max(hh_mag[pass_mask])
    pb_min  = np.min(hh_mag[pass_mask])
    delta2  = np.max(np.abs(hh_mag[stop_mask]))
    fc_val  = (fp_val + fst_val) / 2

    real_pass = hh_real[pass_mask]
    real_stop = hh_real[stop_mask]
    stop_w    = w[stop_mask]
    pass_w    = w[pass_mask]

    pb_max_idx, _ = find_peaks( real_pass, prominence=1e-6)
    pb_min_idx, _ = find_peaks(-real_pass, prominence=1e-6)
    pb_top = real_pass[pb_max_idx].max() if len(pb_max_idx) > 0 else np.max(real_pass)
    pb_bot = real_pass[pb_min_idx].min() if len(pb_min_idx) > 0 else np.min(real_pass)

    sb_max_idx, _ = find_peaks( real_stop, prominence=1e-6)
    sb_min_idx, _ = find_peaks(-real_stop, prominence=1e-6)
    sb_top = real_stop[sb_max_idx].max() if len(sb_max_idx) > 0 else np.max(real_stop)
    sb_bot = real_stop[sb_min_idx].min() if len(sb_min_idx) > 0 else np.min(real_stop)
     # --- 2b. Đáp ứng biên độ theo thang dB ---
    st.markdown("### Đáp ứng biên độ lý thuyết trên thang dB")

    hh_dB = 20 * np.log10(np.maximum(hh_mag, 1e-10))

    pb_max_dB  = 20 * np.log10(max(pb_max, 1e-15))
    pb_min_dB  = 20 * np.log10(max(pb_min, 1e-15))
    delta2_dB  = 20 * np.log10(delta2) if delta2 > 0 else -100
    fc_dB      = 20 * np.log10(1 / np.sqrt(2))

    y_db_top    = pb_max_dB + 5
    y_db_bottom = min(-a_val - 15, -60)
    y_range_db  = y_db_top - y_db_bottom

    fig_db, ax_db = plt.subplots(1, 1, figsize=(13, 5))
    fig_db.subplots_adjust(left=0.10, right=0.97, top=0.88, bottom=0.22)

    ax_db.plot(w, hh_dB, color='black', linewidth=2, zorder=5)
    ax_db.axhline(pb_max_dB, color='green', linewidth=0.9, linestyle='--')
    ax_db.axhline(fc_dB,     color='black', linewidth=0.9, linestyle='--')
    ax_db.axhline(pb_min_dB, color='green', linewidth=0.9, linestyle=':')

    stop_dB   = hh_dB[stop_mask]
    stop_w_db = w[stop_mask]
    sb_peaks_idx, _ = find_peaks(stop_dB, prominence=1)
    if len(sb_peaks_idx) > 0:
        first_peak_dB = stop_dB[sb_peaks_idx[0]]
        first_peak_w  = stop_w_db[sb_peaks_idx[0]]
    else:
        first_peak_dB = delta2_dB
        first_peak_w  = fst_val + (fs_val/2 - fst_val) * 0.05

    ax_db.hlines(-a_val, fst_val, fs_val/2, colors='red', linewidth=0.9, linestyles='--')
    ax_db.vlines(fp_val,  y_db_bottom, y_db_top, colors='green', linestyles='--', linewidth=1.3)
    ax_db.vlines(fc_val,  y_db_bottom, y_db_top, colors='black', linestyles='--', linewidth=1.3)
    ax_db.vlines(fst_val, y_db_bottom, y_db_top, colors='red',   linestyles='--', linewidth=1.3)

    arrow_x = (fst_val + fs_val / 2) / 2
    ax_db.annotate('', xy=(arrow_x, -a_val),
                   xytext=(arrow_x, pb_max_dB),
                   arrowprops=dict(arrowstyle='<->', color='red', lw=1.2))
    label_y = pb_max_dB + (-a_val - pb_max_dB) * 0.25
    
    ax_db.text(
               min(arrow_x * 1.03, fs_val/2 * 0.95),
               label_y,
               f'A = {a_val:.2f} dB',
               color='red',
               fontsize=9,
               va='center',
               fontweight='bold')

    pass_pct_db  = fp_val             / (fs_val/2) * 100
    trans_pct_db = (fst_val - fp_val) / (fs_val/2) * 100
    label_y_db   = (y_db_top + y_db_bottom) / 2

    ax_db.text(fp_val / 2,                label_y_db,
               'Dải thông' if pass_pct_db > 8 else '',
               color='green', fontsize=10, ha='center', va='center', style='italic')
    ax_db.text((fp_val + fst_val) / 2,    label_y_db,
               'Dải chuyển tiếp' if trans_pct_db > 8 else '',
               color='gray',  fontsize=10, ha='center', va='center', style='italic')
    ax_db.text((fst_val + fs_val/2) / 2,  label_y_db,
               'Dải chặn',
               color='red',   fontsize=10, ha='center', va='center', style='italic')

    y_sym_db    = y_db_bottom - y_range_db * 0.040
    y_hz_db     = y_db_bottom - y_range_db * 0.090
    step_db     = y_range_db * 0.055
    min_gap_pct = (fst_val - fp_val) / (fs_val / 2) * 100
    y_offsets   = [0, -step_db, -step_db*2] if min_gap_pct < 10 else [0, 0, 0]

    ax_db.set_xticks([fp_val, fc_val, fst_val])
    ax_db.set_xticklabels(['', '', ''])
    ax_db.tick_params(axis='x', length=0)

    for i, (xpos, sym, hz_str, col) in enumerate([
        (fp_val,  'fp', f'{fp_val:.0f} Hz',  'green'),
        (fc_val,  'fc', f'{fc_val:.0f} Hz',  'black'),
        (fst_val, 'fs', f'{fst_val:.0f} Hz', 'red'),
    ]):
        ax_db.text(xpos, y_sym_db + y_offsets[i], sym,
                   color=col, fontsize=9,   ha='center', va='top', clip_on=False)
        ax_db.text(xpos, y_hz_db  + y_offsets[i], hz_str,
                   color=col, fontsize=7.5, ha='center', va='top', clip_on=False)

    

    y0_frac_db = (0 - y_db_bottom) / y_range_db
    

    ax_db.set_xlim([0, fs_val / 2])
    ax_db.set_ylim([y_db_bottom, y_db_top])
    ax_db.set_ylabel('Biên độ (dB)', fontsize=11)
    ax_db.set_xlabel('Tần số (Hz)', fontsize=11, labelpad=35)
    ax_db.set_title(f"",
                    fontweight='bold', fontsize=10)
    ax_db.grid(True, alpha=0.20, linestyle='--')
    ax_db.spines['top'].set_visible(False)
    ax_db.spines['right'].set_visible(False)
    st.pyplot(fig_db)


    # --- 2a. Đáp ứng tần số |H| ---
    st.markdown("### Đáp ứng biên độ trên thang đo tuyến tính")

    y_top    = pb_max + 0.15
    y_bottom = -delta2 * 8.0
    y_range  = y_top - y_bottom

    fig_res, ax_res = plt.subplots(1, 1, figsize=(13, 5))
    fig_res.subplots_adjust(left=0.10, right=0.97, top=0.88, bottom=0.22)

    ax_res.set_xlim([0, fs_val / 2])
    ax_res.set_ylim([y_bottom, y_top])

    ax_res.plot(w, hh_mag, color='black', linewidth=2, zorder=5)
    ax_res.axhline(0, color='black', linewidth=0.8)

    ax_res.axhline( delta2, color='red',   linewidth=0.8, linestyle='--')
    ax_res.axhline(-delta2, color='red',   linewidth=0.8, linestyle='--')
    ax_res.axhline( pb_max, color='green', linewidth=0.8, linestyle='--')
    ax_res.axhline( pb_min, color='green', linewidth=0.8, linestyle='--')

    ax_res.vlines(fp_val,  y_bottom, y_top-0.05, colors='green', linestyles='--', linewidth=1.3)
    ax_res.vlines(fc_val,  y_bottom, y_top-0.05, colors='black', linestyles='--', linewidth=1.3)
    ax_res.vlines(fst_val, y_bottom, y_top-0.05, colors='red',   linestyles='--', linewidth=1.3)

    pass_pct_plot  = fp_val              / (fs_val/2) * 100
    trans_pct_plot = (fst_val - fp_val)  / (fs_val/2) * 100
    stop_pct_plot  = (fs_val/2 - fst_val)/ (fs_val/2) * 100

    label_y_pass  = pb_max * 0.30
    label_y_trans = pb_max * 0.65
    label_y_stop  = pb_max * 0.30

    ax_res.text(fp_val * 0.42,
                label_y_pass,
                'Dải thông' if pass_pct_plot > 8 else '',
                color='green', fontsize=10, ha='center', style='italic')
    ax_res.text((fp_val + fst_val) / 2,
                label_y_trans,
                'Dải chuyển tiếp' if trans_pct_plot > 8 else '',
                color='black', fontsize=10, ha='center', style='italic')
    ax_res.text((fst_val + fs_val/2) / 2,
                label_y_stop,
                'Dải chặn' if stop_pct_plot > 8 else '',
                color='red', fontsize=10, ha='center', style='italic')

    ox      = -fs_val * 0.028
    offset  = y_range * 0.035
    ax_res.text(ox,  delta2 + offset, ' δ₂', color='red',   fontsize=8,   ha='right', va='bottom')
    ax_res.text(ox, -delta2 - offset, '-δ₂', color='red',   fontsize=8,   ha='right', va='top')

    pb_gap = pb_max - pb_min
    label_offset = max(offset, pb_gap * 0.1)
    ax_res.text(ox, pb_max + label_offset, '1+δ₁', color='green', fontsize=7.5, ha='right', va='bottom')
    ax_res.text(ox, pb_min - label_offset, '1-δ₁', color='green', fontsize=7.5, ha='right', va='top')

    ax_res.set_xticks([fp_val, fc_val, fst_val])
    ax_res.set_xticklabels(['', '', ''])
    ax_res.tick_params(axis='x', length=0)

    y_sym = y_bottom - y_range * 0.040
    y_hz  = y_bottom - y_range * 0.090
    step  = y_range * 0.055

    min_gap_pct = (fst_val - fp_val) / (fs_val / 2) * 100
    y_offsets   = [0, -step, -step*2] if min_gap_pct < 10 else [0, 0, 0]

    for i, (xpos, sym, hz_str, col) in enumerate([
        (fp_val,  'ωp', f'{fp_val:.0f} Hz',  'green'),
        (fc_val,  'ωc', f'{fc_val:.0f} Hz',  'black'),
        (fst_val, 'ωs', f'{fst_val:.0f} Hz', 'red'),
    ]):
        ax_res.text(xpos, y_sym + y_offsets[i], sym,
                    color=col, fontsize=9,   ha='center', va='top', clip_on=False)
        ax_res.text(xpos, y_hz  + y_offsets[i], hz_str,
                    color=col, fontsize=7.5, ha='center', va='top', clip_on=False)
    ax_res.text(fs_val/2 * 0.985, y_sym, 'π', color='gray', fontsize=9, ha='center', va='top', clip_on=False)
    y0_frac = (0 - y_bottom) / y_range
    ax_res.annotate('ω', xy=(1.012, y0_frac), xycoords='axes fraction',
                    fontsize=13, fontstyle='italic', color='#333', va='center', annotation_clip=False)

    ax_res.set_ylabel(r'$|H(e^{j\omega})|$', fontsize=11)
    ax_res.set_title(f"",
                     fontweight='bold', fontsize=10)
    ax_res.grid(False)
    ax_res.spines['top'].set_visible(False)
    ax_res.spines['right'].set_visible(False)
    with st.expander("Xem thêm: đáp ứng tuyến tính |H(e^jω)|", expanded=False):
        st.pyplot(fig_res)
    

    # ==========================================
    # BLOCK 3 — TÍN HIỆU TEST
    # ==========================================
    st.markdown("---")
    st.markdown("##  Bước 3 — Xem trước Tín hiệu Thử nghiệm")
    st.info(
        f"**Tín hiệu dải thông:** Chirp tuyến tính từ **0 Hz → {fp_val} Hz**\n\n"
        f"**Tín hiệu dải chặn:** Chirp tuyến tính từ **{fst_val} Hz → {int(fs_val/2)} Hz**"
    )

    sig_q_plot       = st.session_state['sig_q']
    clean_sig_q_plot = st.session_state['clean_sig_q']
    scale_plot       = 2 ** (st.session_state['bits'] - 1) - 1
    fs_plot          = st.session_state['fs']

    t_plot           = np.arange(len(sig_q_plot)) / fs_plot
    sig_float_plot   = sig_q_plot / scale_plot
    clean_float_plot = clean_sig_q_plot / scale_plot
    noise_float_plot = sig_float_plot - clean_float_plot
    zoom_sig         = min(len(sig_float_plot), 500)

    fig_sig, axes = plt.subplots(3, 1, figsize=(14, 8), sharex=True)
    fig_sig.suptitle(" ", fontweight='bold', fontsize=13)

    axes[0].plot(t_plot[:zoom_sig], sig_float_plot[:zoom_sig],
                 color='#3498db', linewidth=1.2, label='Tổng hợp')
    axes[0].set_ylabel("Biên độ (V)")
    axes[0].set_title("Tín hiệu Đầu vào")
    axes[0].legend(loc='upper right')
    axes[0].grid(True, alpha=0.3, linestyle='--')

    axes[1].plot(t_plot[:zoom_sig], clean_float_plot[:zoom_sig],
                 color='#2ecc71', linewidth=1.2, label='')
    axes[1].set_ylabel("Biên độ (V)")
    axes[1].set_title("Tín hiệu dải thông")
    axes[1].legend(loc='upper right')
    axes[1].grid(True, alpha=0.3, linestyle='--')

    axes[2].plot(t_plot[:zoom_sig], noise_float_plot[:zoom_sig],
                 color='#e74c3c', linewidth=1.2, label='Tín hiệu dải chặn')
    axes[2].set_ylabel("Biên độ (V)")
    axes[2].set_xlabel("Thời gian (s)")
    axes[2].set_title("Tín hiệu dải chặn")
    axes[2].legend(loc='upper right')
    axes[2].grid(True, alpha=0.3, linestyle='--')

    plt.tight_layout()
    with st.expander("Xem dạng sóng chirp / dải thông / dải chặn", expanded=False):
        st.pyplot(fig_sig)

    # ==========================================
    # BLOCK 4 — XUẤT FILE & NẠP PHẦN CỨNG
    # ==========================================
    st.markdown("---")
    st.markdown("##  Bước 4 — Đóng gói & Xuất Tệp tin Cấu hình Hệ thống")
    st.markdown(
        " **1. coeff.hex** — Hệ số bộ lọc\n\n"
        " **2. input_chirp.hex** — ROM tín hiệu Chirp \n\n"
        " **3. input_dirac.hex** — ROM tín hiệu Dirac \n\n"
        " **4. taps_config.vh** — Khai báo tham số Verilog"
    )

    scale_val = 2 ** (st.session_state['bits'] - 1) - 1

    # Chirp 1000 mẫu (pad thêm zero nếu sig_q < 1000)
    sig_q_full = np.zeros(1000, dtype=int)
    sig_q_full[:len(st.session_state['sig_q'])] = st.session_state['sig_q']
    hex_input_chirp = "\n".join([float_to_hex2s(v, st.session_state['bits']) for v in sig_q_full])

    # Dirac 1000 mẫu
    dirac_q = [0] * 1000
    dirac_q[0] = scale_val
    hex_input_dirac = "\n".join([float_to_hex2s(v, st.session_state['bits']) for v in dirac_q])

    hex_coeffs = "\n".join([float_to_hex2s(v, st.session_state['bits']) for v in st.session_state['hq']])
    vh_config  = f"parameter TAPS = {n};"

    c1, c2, c3, c4 = st.columns(4)
    c1.download_button(" coeff.hex",       hex_coeffs,      "coeff.hex",       use_container_width=True)
    c2.download_button(" input_chirp.hex", hex_input_chirp, "input_chirp.hex", use_container_width=True)
    c3.download_button(" input_dirac.hex", hex_input_dirac, "input_dirac.hex", use_container_width=True)
    c4.download_button(" taps_config.vh",  vh_config,       "taps_config.vh",  use_container_width=True)

    st.info(
        "**Quy trình nạp FPGA:**\n\n"
        "- **Lần 1 (Chirp):** Thả KEY2 → nhấn KEY1 Reset → chạy script → lưu `output_chirp.hex`\n"
        "- **Lần 2 (Dirac):** Nhấn giữ KEY2 → nhấn KEY1 Reset → chạy script → lưu `output_dirac.hex`"
    )


# ==========================================
# ==========================================
# BLOCK 5 — XÁC MINH KẾT QUẢ FPGA
# ==========================================
st.markdown("---")
st.markdown("## Bước 5 — Xác minh FPGA so với Tín hiệu Dải thông")

if st.session_state.design_done:
    Q_IN  = st.session_state['bits'] - 1   # 15
    Q_OUT = Q_IN * 2                        # 30
    hq    = st.session_state['hq']
    sig_q = st.session_state['sig_q']
    clean_sig_q = st.session_state['clean_sig_q']   # tín hiệu dải thông thuần
    a_target = st.session_state.get('a', 30)
    fs_val   = st.session_state['fs']
    fp_val   = st.session_state['fp']
    fst_val  = st.session_state['fst']
    h        = st.session_state['h_float']
    n        = st.session_state['n']
    scale_val = 2 ** (st.session_state['bits'] - 1) - 1

    def decode_hex_output(uploaded_file):
        """Giải mã file hex 39-bit two's complement → float array"""
        content  = uploaded_file.getvalue().decode().splitlines()
        out_raw  = [int(x.strip(), 16) for x in content if x.strip()]
        out_data = []
        for v in out_raw:
            v_39 = v & ((1 << 39) - 1)
            out_data.append(v_39 - (1 << 39) if v_39 >= (1 << 38) else v_39)
        return np.array(out_data)

    # ── LUỒNG 1: CHIRP ────────────────────────────────────────────────
    st.markdown("### Luồng 1 — Xác minh Khả năng Lọc")
    st.markdown("Chạy FPGA với **input_chirp.hex** , upload kết quả:")
    uploaded_chirp = st.file_uploader("output_chirp.hex", type=["hex"], key="chirp")

    if uploaded_chirp:
        out_data_chirp   = decode_hex_output(uploaded_chirp)
        if len(out_data_chirp) != 1000:
            st.warning(f"Số mẫu Chirp nhận được = {len(out_data_chirp)}, kỳ vọng 1000 mẫu.")

        fpga_chirp_float = out_data_chirp / (1 << Q_OUT)

        # ── Reference: tín hiệu dải thông thuần (không phải Python convolution) ──
        # clean_sig_q là Q15, cần scale về float cùng đơn vị với FPGA output (Q30)
        # FPGA output = tích chập Q15 * Q15 → Q30 → chia (1<<30)
        # clean_sig đơn vị V → giữ nguyên float
        clean_float_ref = clean_sig_q / scale_val   # float [-1, 1]

        delay = st.slider(
            "Pipeline delay",
            min_value=0, max_value=20, value=1, step=1,
            help="Tăng nếu FPGA trễ so với tín hiệu tham chiếu"
        )

        fpga_aligned = fpga_chirp_float[delay:]
        ref_aligned  = clean_float_ref[:len(fpga_aligned)]

        min_len  = min(len(fpga_aligned), len(ref_aligned))
        fpga_c   = fpga_aligned[:min_len]
        ref_c    = ref_aligned[:min_len]
        error_c  = fpga_c - ref_c
        mse_c    = np.mean(error_c ** 2)
        max_err_c = np.max(np.abs(error_c))

        # ── Metrics ──────────────────────────────────────────────────────────
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("MSE (FPGA vs Dải thông)", f"{mse_c:.6f}")
        col_m2.metric("Max Error", f"{max_err_c:.6f}")

        # Ngưỡng pass: sai số tối đa < biên độ dải chặn lý thuyết
        # (bộ lọc tốt thì residual ≈ mức suy hao dải chặn)
        pass_threshold = 10 ** (-a_target / 20) * 0.5 + 0.02   # biên độ tương đương dB
        if max_err_c < pass_threshold:
            st.success(f"")
        else:
            st.error(
                f""
                ""
            )

        # ── Đồ thị so sánh ───────────────────────────────────────────────────
        zoom_c = min(min_len, 400)
        fig_c, axes_c = plt.subplots(1, 1, figsize=(14, 5))
                
        fig_c.suptitle(" FPGA Output và Tín hiệu Dải thông ",
                        fontweight='bold', fontsize=12)

        axes_c.plot(ref_c[:zoom_c],  color='#2ecc71', linewidth=2.0,
                       label='Tín hiệu dải thông (tham chiếu)')
        axes_c.plot(fpga_c[:zoom_c], color='#1f77b4', linewidth=1.5,
                       linestyle='--', label='FPGA Output (sau lọc)')
        axes_c.set_ylabel("Biên độ (V)")
        axes_c.legend(loc='upper right')
        axes_c.grid(True, alpha=0.3, linestyle='--')
        axes_c.spines['top'].set_visible(False)
        axes_c.spines['right'].set_visible(False)

        plt.tight_layout()
        st.pyplot(fig_c)

        st.download_button(
            " Xuất output chi tiết",
            pd.DataFrame({
                'Sample_Index':     np.arange(min_len),
                'FPGA_Float':       fpga_c,
                'CleanSig_Float':   ref_c,
                'Error':            error_c
            }).to_csv(index=False).encode('utf-8'),
            'output_chirp.csv', 'text/csv', use_container_width=True
        )

    # ── LUỒNG 2: DIRAC ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("###  Luồng 2 — Đáp ứng Tần số Thực nghiệm")
    st.markdown("Chạy FPGA với **input_dirac.hex**, upload kết quả:")
    uploaded_dirac = st.file_uploader(" output_dirac.hex", type=["hex"], key="dirac")

    if uploaded_dirac:
        out_data_dirac   = decode_hex_output(uploaded_dirac)
        if len(out_data_dirac) != 1000:
            st.warning(f"Số mẫu Dirac nhận được = {len(out_data_dirac)}, kỳ vọng 1000 mẫu.")
        fpga_dirac_float = out_data_dirac / (1 << Q_OUT)

        
            
            

        with st.expander(" |H(f)| thực nghiệm FPGA", expanded=True):
            N_d = len(fpga_dirac_float)
            xf  = fftfreq(N_d, 1/fs_val)[:N_d//2]

            H_f_complex      = fft(fpga_dirac_float)[:N_d//2]
            H_f_experimental = 20 * np.log10(np.abs(H_f_complex) + 1e-15)

            fig_fft, ax_fft = plt.subplots(figsize=(14, 6))
            ax_fft.plot(w, hh_dB, color='#2ecc71', linewidth=2,
                        linestyle='--', label="|H(f)| Lý thuyết Python")
            ax_fft.plot(xf, H_f_experimental, color="#1f77b4", linewidth=1.6,
                        label="|H(f)| thực nghiệm FPGA (Dirac)")
            ax_fft.hlines(-a_target, fst_val, fs_val/2,
                          colors='red', linestyles='--', linewidth=1.6,
                          label=f"Ngưỡng chặn (−{a_target:.1f} dB)")
            ax_fft.axvspan(0,       fp_val,   alpha=0.08, color='green')
            ax_fft.axvspan(fst_val, fs_val/2, alpha=0.08, color='red')
            ax_fft.set_ylim([-max(a_target + 30, 60), 10])
            ax_fft.set_xlim([0, fs_val/2])
            ax_fft.set_title(f"",
                             fontweight='bold')
            ax_fft.set_xlabel("Tần số (Hz)")
            ax_fft.set_ylabel("Độ lớn (dB)")
            ax_fft.legend(loc='upper right', frameon=True)
            ax_fft.grid(True, which='both', linestyle='--', alpha=0.5)

            mask_stop = (xf >= fst_val) & (xf <= fs_val/2)
            if mask_stop.any():
                actual_atten = np.mean(H_f_experimental[mask_stop])
                mid_stop     = (fst_val + fs_val/2) / 2
                worst_case    = np.max(H_f_experimental[mask_stop]) 
                atten_db      = 0 - worst_case   
                ax_fft.annotate(
                    f'Suy hao worst case: {atten_db:.1f} dB',
                    xy=(mid_stop, worst_case),
                    xytext=(mid_stop, worst_case + 14),
                    arrowprops=dict(facecolor='#1f77b4', shrink=0.05, width=1, headwidth=5),
                    fontsize=9, color='#1f77b4')
                 # Hiển thị metric bên dưới đồ thị
                col1, col2 = st.columns(2)
                col1.metric("Suy hao worst case (đỉnh cao nhất)", f"{atten_db:.1f} dB")
                col2.metric("Suy hao trung bình dải chặn",        f"{0 - actual_atten:.1f} dB")
                            
            st.pyplot(fig_fft)

        st.download_button(
            " Xuất output chi tiết",
            pd.DataFrame({
                'Sample_Index':     np.arange(N_d),
                'FPGA_Dirac_Float': fpga_dirac_float,
            }).to_csv(index=False).encode('utf-8'),
            'output_dirac.csv', 'text/csv', use_container_width=True
        )

else:
    st.info("⬆️ Vui lòng hoàn thành Bước 1 và nhấn **Kích hoạt Tính toán & Thiết kế Bộ lọc** trước.")
