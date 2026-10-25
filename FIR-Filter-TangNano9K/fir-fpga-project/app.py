import streamlit as st
import numpy as np
from scipy import signal
from scipy.signal import find_peaks, chirp
from scipy.fft import fft, fftfreq
import matplotlib.pyplot as plt
import pandas as pd

# ==========================================
# KHỞI TẠO SESSION STATE & CẤU HÌNH GIAO DIỆN
# ==========================================
st.set_page_config(page_title="FIR DSP Master - Tang Nano 9K Edition", page_icon="📟", layout="wide")

N_MAX_HW = 200
N_SAMPLES = 1000

def float_to_hex2s(val, bits_len):
    return format(int(val) & ((1 << bits_len) - 1), f'0{bits_len//4}x')

def format_sci_unicode(val):
    if val == 0:
        return "0"
    if 0.0001 <= abs(val) < 10000:
        return f"{val:.6f}".rstrip('0').rstrip('.')
    
    s = f"{val:.4e}"
    base, exp = s.split('e')
    exp_int = int(exp)
    
    superscripts = {
        '-': '⁻', '+': '⁺', '0': '⁰', '1': '¹', '2': '²', '3': '³', 
        '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'
    }
    exp_unicode = "".join(superscripts[c] for c in str(exp_int))
    base_clean = f"{float(base):.4f}".rstrip('0').rstrip('.')
    return f"{base_clean} × 10{exp_unicode}"

defaults = {
    'fs_val': 8000, 'fp_val': 1000, 'fst_val': 1400, 'a_val': 60,
    'processing': False, 'design_done': False,
    'reset_triggered': False, 'switch_to_tab2': False, 'switch_to_tab3': False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state.get('reset_triggered', False):
    st.session_state.update({
        'fs_val': 8000, 'fp_val': 1000, 'fst_val': 1400, 'a_val': 60,
        'reset_triggered': False,
        'design_done': False,
    })

# ── THIẾT LẬP MÀU NÚT DYNAMIC ──
if st.session_state.get('processing'):
    btn_bg = "#64748b"
    btn_bg_hover = "#475569"
    btn_gradient = "linear-gradient(135deg, #64748b 0%, #475569 100%)"
    btn_shadow = "rgba(100, 116, 139, 0.2)"
elif st.session_state.get('design_done'):
    btn_bg = "#16a34a"
    btn_bg_hover = "#15803d"
    btn_gradient = "linear-gradient(135deg, #16a34a 0%, #15803d 100%)"
    btn_shadow = "rgba(22, 163, 74, 0.2)"
else:
    btn_bg = "#dc2626"
    btn_bg_hover = "#b91c1c"
    btn_gradient = "linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)"
    btn_shadow = "rgba(220, 38, 38, 0.2)"

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
    }

    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
        max-width: 1400px;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: -0.02em;
        color: #1e293b;
    }

    /* ── TAB STYLING ── */
    div[role="tablist"] {
        background: #f8fafc;
        border-radius: 14px 14px 0 0;
        border-bottom: 2px solid #e2e8f0;
        padding: 4px 8px 0 8px;
        gap: 8px;
        display: flex !important;
        justify-content: center !important;
    }

    button[data-baseweb="tab"],
    button[data-testid="stTab"] {
        font-family: 'Inter', sans-serif !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        color: #475569 !important;
        border-radius: 10px 10px 0 0 !important;
        padding: 12px 24px !important;
        border: none !important;
        background: transparent !important;
        transition: all 0.2s ease !important;
        letter-spacing: -0.01em;
        flex: 1 1 0% !important;
        text-align: center !important;
    }

    button[data-baseweb="tab"]:hover,
    button[data-testid="stTab"]:hover {
        color: #1d4ed8 !important;
        background: #eff6ff !important;
    }

    button[aria-selected="true"][data-baseweb="tab"],
    button[aria-selected="true"][data-testid="stTab"] {
        color: #1d4ed8 !important;
        font-weight: 700 !important;
        background: #ffffff !important;
        border-bottom: 2px solid #1d4ed8 !important;
        box-shadow: 0 -2px 8px rgba(29,78,216,0.08);
    }

    /* Đổi màu thanh trượt gạch chân của tab hoạt động từ đỏ sang xanh dương trên Streamlit Cloud */
    div[role="tablist"] > div {
        background-color: #1d4ed8 !important;
    }

    div[data-testid="stTabsContent"] {
        border: 1.5px solid #e2e8f0;
        border-top: none;
        border-radius: 0 0 14px 14px;
        padding: 24px 24px 28px 24px;
        background: #ffffff;
        box-shadow: 0 4px 24px rgba(0,0,0,0.04);
    }

    /* ── METRIC CARDS ── */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1.5px solid #e2e8f0;
        padding: 16px 20px !important;
        border-radius: 14px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 4px !important;
    }

    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.08);
    }

    div[data-testid="stMetricLabel"] > div {
        font-size: 12px !important;
        font-weight: 600 !important;
        color: #475569 !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    div[data-testid="stMetricValue"] > div {
        font-size: 22px !important;
        font-weight: 700 !important;
        color: #0f172a !important;
        letter-spacing: -0.03em;
        white-space: nowrap !important;
    }

    [data-testid="stWidgetLabel"] p, label {
        font-size: 15px !important;
        font-weight: 700 !important;
        color: #0f172a !important;
    }

    div[data-testid="stWidgetLabel"] em {
        font-size: 11px !important;
        font-weight: 400 !important;
        color: #64748b !important;
        font-style: normal !important;
        display: inline-block !important;
        margin-left: 8px !important;
    }

    /* ── CONTAINERS ── */
    div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] {
        padding: 0 !important;
    }

    /* ── BUTTONS ── */
    .stButton button {
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        transition: all 0.2s ease !important;
    }

    button[data-testid="baseButton-primary"],
    .stButton button[kind="primary"],
    .stButton button[data-testid="baseButton-primary"],
    div[data-testid="column"]:nth-of-type(2) button[data-testid="baseButton-primary"] {
        background: #1d4ed8 !important;
        background-color: #1d4ed8 !important;
        background-image: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(29,78,216,0.35) !important;
        font-size: 15px !important;
        padding: 12px 24px !important;
    }

    button[data-testid="baseButton-primary"]:hover,
    .stButton button[kind="primary"]:hover,
    .stButton button[data-testid="baseButton-primary"]:hover,
    div[data-testid="column"]:nth-of-type(2) button[data-testid="baseButton-primary"]:hover {
        background: #1e40af !important;
        background-color: #1e40af !important;
        background-image: linear-gradient(135deg, #1e40af 0%, #1d4ed8 100%) !important;
        box-shadow: 0 6px 20px rgba(29,78,216,0.45) !important;
        transform: translateY(-1px);
        color: white !important;
    }

    button:disabled {
        opacity: 0.38 !important;
        cursor: not-allowed !important;
    }

    /* ── EXPANDER ── */
    div[data-testid="stExpander"] {
        border: 1.5px solid #e2e8f0 !important;
        border-radius: 12px !important;
        overflow: hidden;
    }

    div[data-testid="stExpander"] summary {
        font-weight: 600 !important;
        color: #374151 !important;
        padding: 12px 16px !important;
        background: #f8fafc;
    }

    /* ── FILE UPLOADER ── */
    div[data-testid="stFileUploader"] {
        border: 2px dashed #cbd5e1 !important;
        border-radius: 14px !important;
        background: #f8fafc !important;
        transition: border-color 0.2s;
    }

    div[data-testid="stFileUploader"]:hover {
        border-color: #93c5fd !important;
        background: #eff6ff !important;
    }

    /* ── SECTION HEADERS ── */
    .section-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #eff6ff;
        color: #1d4ed8;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        border: 1px solid #bfdbfe;
        margin-bottom: 6px;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    /* ── DIVIDER ── */
    .section-divider {
        border: none;
        border-top: 1.5px solid #f1f5f9;
        margin: 20px 0;
    }

    /* ── STEP HEADING ── */
    .step-heading {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 14px;
    }

    .step-number {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background: linear-gradient(135deg, #1d4ed8, #3b82f6);
        color: white;
        font-weight: 800;
        font-size: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        box-shadow: 0 4px 10px rgba(29,78,216,0.3);
    }

    /* Responsive grid */
    @media (max-width: 768px) {
        div[role="tablist"] {
            overflow-x: auto;
            flex-wrap: nowrap;
        }
        div[data-testid="stTabsContent"] {
            padding: 14px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ── DYNAMIC BUTTON CSS ──
st.markdown(f"""
<style>
    button[data-testid="baseButton-primary"],
    .stButton button[kind="primary"],
    .stButton button[data-testid="baseButton-primary"],
    div[data-testid="column"]:nth-of-type(2) button[data-testid="baseButton-primary"] {{
        background: {btn_bg} !important;
        background-color: {btn_bg} !important;
        background-image: {btn_gradient} !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 14px {btn_shadow} !important;
        font-size: 15px !important;
        font-weight: 700 !important;
        padding: 12px 24px !important;
    }}

    button[data-testid="baseButton-primary"]:hover,
    .stButton button[kind="primary"]:hover,
    .stButton button[data-testid="baseButton-primary"]:hover,
    div[data-testid="column"]:nth-of-type(2) button[data-testid="baseButton-primary"]:hover {{
        background: {btn_bg_hover} !important;
        background-color: {btn_bg_hover} !important;
        background-image: {btn_gradient} !important;
        box-shadow: 0 6px 20px {btn_shadow} !important;
        transform: translateY(-1px);
        color: white !important;
        font-weight: 700 !important;
    }}
</style>
""", unsafe_allow_html=True)

# ── HEADER ──────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; padding: 6px 0 18px 0;">
    <h1 style="font-family:'Inter',sans-serif; font-size:34px; font-weight:700; color:#0f172a;
               margin:0; letter-spacing:-0.04em; line-height:1.1;">
        FPGA FIR Design &amp; Verification
    </h1>
</div>
""", unsafe_allow_html=True)



# ── AUTO-SWITCH JS ──────────────────────────────────────
if st.session_state.get('switch_to_tab2', False):
    st.session_state['switch_to_tab2'] = False
    st.markdown("""
    <script>
    (function() {
        sessionStorage.setItem("active_tab_index", 1);
        function switchTab(idx) {
            var tabs = document.querySelectorAll('button[data-baseweb="tab"]');
            if (tabs.length > idx) { tabs[idx].click(); return true; }
            return false;
        }
        var attempts = 0;
        var t = setInterval(function() {
            if (switchTab(1) || ++attempts > 20) clearInterval(t);
        }, 150);
    })();
    </script>
    """, unsafe_allow_html=True)

if st.session_state.get('switch_to_tab3', False):
    st.session_state['switch_to_tab3'] = False
    st.markdown("""
    <script>
    (function() {
        sessionStorage.setItem("active_tab_index", 3);
        function switchTab(idx) {
            var tabs = document.querySelectorAll('button[data-baseweb="tab"]');
            if (tabs.length > idx) { tabs[idx].click(); return true; }
            return false;
        }
        var attempts = 0;
        var t = setInterval(function() {
            if (switchTab(3) || ++attempts > 20) clearInterval(t);
        }, 150);
    })();
    </script>
    """, unsafe_allow_html=True)

# ── TAB TRACKING JS ─────────────────────────────────────
st.markdown("""
<script>
(function() {
    // Lưu tab đang active vào sessionStorage khi user click
    function attachTabListeners() {
        var tabs = document.querySelectorAll('button[data-baseweb="tab"]');
        tabs.forEach(function(tab, index) {
            if (!tab.dataset.tracked) {
                tab.dataset.tracked = "true";
                tab.addEventListener('click', function() {
                    sessionStorage.setItem("active_tab_index", index);
                });
            }
        });
    }

    // Khôi phục tab đã lưu sau rerun
    function restoreTab() {
        var storedIndex = sessionStorage.getItem("active_tab_index");
        if (storedIndex === null) return false;
        var activeIdx = parseInt(storedIndex);
        var tabs = document.querySelectorAll('button[data-baseweb="tab"]');
        if (tabs.length === 0) return false;
        var activeTab = document.querySelector('button[data-baseweb="tab"][aria-selected="true"]');
        var currentIdx = Array.from(tabs).indexOf(activeTab);
        if (currentIdx !== activeIdx && tabs[activeIdx]) {
            tabs[activeIdx].click();
            attachTabListeners();
            return true;
        }
        attachTabListeners();
        return true;
    }

    // Thử khôi phục nhiều lần sau mỗi rerun (file upload gây rerun chậm hơn)
    var attempts = 0;
    var maxAttempts = 40;
    var interval = setInterval(function() {
        if (restoreTab() || ++attempts >= maxAttempts) {
            clearInterval(interval);
        }
    }, 100);

    // Dùng MutationObserver để detect khi Streamlit render xong tabs mới
    var observer = new MutationObserver(function() {
        attachTabListeners();
        restoreTab();
    });
    observer.observe(document.body, { childList: true, subtree: true });
})();
</script>
""", unsafe_allow_html=True)

# ==========================================
# MAIN TABS
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "  Thiết kế",
    "  Mô phỏng bộ lọc bằng python",
    "  Tạo tín hiệu thử nghiệm và đóng gói tệp",
    "  Kiểm chứng thực nghiệm",
])

# ╔══════════════════════════════════════════════════════╗
# ║  TAB 1 — THIẾT KẾ                                   ║
# ╚══════════════════════════════════════════════════════╝
with tab1:
    st.markdown("""
    <div class="step-heading">
        <div class="step-number">1</div>
        <div>
            <div style="font-size:22px; font-weight:700; color:#0f172a; letter-spacing:-0.02em;">Thông số thiết kế</div>
            <div style="font-size:13px; color:#334155; margin-top:1px; font-weight:500;">Nhập các tham số để thiết kế bộ lọc FIR Lowpass bằng cửa sổ Kaiser</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Tính toán phụ trợ ──
    fs_cur  = st.session_state['fs_val']
    fs2_cur = int(fs_cur / 2)
    min_delta_f = int((21 - 8) * (fs_cur / 2) / (2.285 * 2 * np.pi * (N_MAX_HW - 1))) + 1 if fs2_cur > 0 else 1

    # ── Layout 2 cột: bên trái inputs, bên phải sidebar thông số ──
    col_left, col_right = st.columns([3, 1], gap="large")

    with col_left:
        with st.container(border=True):


            fs = st.number_input(
                "Tần số lấy mẫu Fs (Hz)",
                min_value=0, max_value=192000,
                key='fs_val', step=100,
                disabled=True,
                help="Tần số lấy mẫu cố định."
            )
            fs2 = int(fs / 2)
            min_delta_f = int((21 - 8) * (fs / 2) / (2.285 * 2 * np.pi * (N_MAX_HW - 1))) + 1 if fs2 > 0 else 1

            max_fp = max(0, fs2 - 200)
            if st.session_state['fp_val'] > max_fp:
                st.session_state['fp_val'] = max_fp

            fp = st.number_input(
                f"Tần số biên dải thông Fp (Hz)   _(100 – {fs2 - 200} Hz)_",
                min_value=0, max_value=max_fp,
                key='fp_val', step=10,
                disabled=st.session_state.design_done,
                help=f"Tần số cao nhất được giữ lại. Tối đa = Fs/2 − 200 = {fs2 - 200} Hz"
            )

            fst_min = int(fp + min_delta_f)
            fst_max = max(0, fs2 - 50)
            if st.session_state['fst_val'] > fst_max:
                st.session_state['fst_val'] = fst_max

            fst = st.number_input(
                f"Tần số biên dải chặn Fstop (Hz)   _({fst_min} – {fst_max} Hz)_",
                min_value=0, max_value=fst_max,
                key='fst_val', step=10,
                disabled=st.session_state.design_done,
                help=f"Tần số bắt đầu bị triệt tiêu. Tối thiểu = Fp + Δf_min = {fst_min} Hz"
            )

            a = st.slider(
                "Suy hao dải chặn yêu cầu As (dB)",
                min_value=0, max_value=80,
                key='a_val', step=1,
                disabled=st.session_state.design_done,
                help="Giới hạn thực tế tối đa là 80 dB đối với Q15."
            )

            # ── Validation ──
            errors = []
            if fs <= 0:    errors.append("Tần số lấy mẫu Fs phải lớn hơn 0.")
            if fp <= 0:    errors.append("Tần số biên dải thông Fp phải lớn hơn 0.")
            if fst <= 0:   errors.append("Tần số biên dải chặn Fstop phải lớn hơn 0.")
            if a < 21:     errors.append("Suy hao As phải từ 21 dB trở lên để dùng cửa sổ Kaiser.")
            if fs2 > 0:
                if fp >= fs2:  errors.append(f"Fp ({fp} Hz) phải nhỏ hơn Fs/2 ({fs2} Hz).")
                if fst >= fs2: errors.append(f"Fstop ({fst} Hz) phải nhỏ hơn Fs/2 ({fs2} Hz).")
            if fst <= fp:  errors.append(f"Fstop ({fst} Hz) phải lớn hơn Fp ({fp} Hz).")
            for e in errors:
                st.error(e)

            delta_f = fst - fp
            pct_bw  = delta_f / fs2 * 100 if fs2 > 0 else 0.0

            if delta_f < 200 and not errors:
                st.warning("⚠️ Dải chuyển tiếp quá hẹp — suy hao thực tế có thể thấp hơn lý thuyết.")

            # ── Bandwidth bar ──
            if not errors and fs2 > 0:
                pass_pct  = fp      / fs2 * 100
                trans_pct = delta_f / fs2 * 100
                stop_pct  = max(0, 100 - pass_pct - trans_pct)

                label_pass  = "Dải thông"       if pass_pct  >= 6 else ""
                label_trans = "Dải chuyển tiếp" if trans_pct >= 6 else ""
                label_stop  = "Dải chặn"        if stop_pct  >= 6 else ""

                pass_fs  = "12px" if pass_pct  >= 10 else "9px"
                trans_fs = "12px" if trans_pct >= 10 else "9px"
                stop_fs  = "12px" if stop_pct  >= 10 else "9px"

                st.markdown(f"""
                <div style="margin-top:16px;">
                    <div style="font-size:13px; color:#0f172a; font-weight:700; letter-spacing:0.05em; text-transform:uppercase; margin-bottom:8px;">
                        Phân bổ băng thông tần số
                    </div>
                    <div style="display:flex; height:32px; border-radius:10px; overflow:hidden; border:1.5px solid #e2e8f0; box-shadow:0 2px 6px rgba(0,0,0,0.05);">
                        <div style="width:{pass_pct:.1f}%; background:linear-gradient(135deg,#bbf7d0,#86efac); display:flex; align-items:center;
                                    justify-content:center; font-size:{pass_fs}; font-weight:800; color:#166534;">{label_pass}</div>
                        <div style="width:{trans_pct:.1f}%; background:linear-gradient(135deg,#fef3c7,#fde68a); display:flex; align-items:center;
                                    justify-content:center; font-size:{trans_fs}; font-weight:800; color:#92400e;">{label_trans}</div>
                        <div style="width:{stop_pct:.1f}%; background:linear-gradient(135deg,#fecaca,#fca5a5); display:flex; align-items:center;
                                    justify-content:center; font-size:{stop_fs}; font-weight:800; color:#991b1b;">{label_stop}</div>
                    </div>
                    <div style="position:relative; height:22px; font-size:12px; color:#0f172a; margin-top:4px;">
                        <span style="position:absolute; left:0; transform:translateX(-50%); font-weight:700; font-size:12px; white-space:nowrap !important;">0</span>
                        <span style="position:absolute; left:{pass_pct:.1f}%; transform:translateX(-50%); font-size:12px; color:#16a34a; font-weight:800; white-space:nowrap !important;">Fp</span>
                        <span style="position:absolute; left:{(pass_pct+trans_pct):.1f}%; transform:translateX(-50%); font-size:12px; color:#dc2626; font-weight:800; white-space:nowrap !important;">Fst</span>
                        <span style="position:absolute; right:0; transform:translateX(50%); font-weight:700; font-size:12px; white-space:nowrap !important;">Fs/2</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    with col_right:
        with st.container(border=True):
            st.markdown("""
            <div style="font-size:13px; font-weight:700; color:#475569; text-transform:uppercase;
                        letter-spacing:0.06em; margin-bottom:12px;">📊 Kết quả ước tính</div>
            """, unsafe_allow_html=True)

            delta_f_r = fst - fp
            if delta_f_r > 0 and fs2 > 0 and a >= 21:
                width_norm = delta_f_r / fs2
                n_calc, beta_calc = signal.kaiserord(float(a), width_norm)
                if n_calc % 2 == 0:
                    n_calc += 1
            else:
                n_calc, beta_calc = 0, 0.0

            n_display = f"{n_calc}" if n_calc > 0 else "—"
            gd_display = f"{(n_calc - 1) // 2}" if n_calc > 0 else "—"
            beta_display = f"{beta_calc:.4f}" if beta_calc > 0 else "—"

            st.metric("Số Tap bộ lọc", n_display,
                      help=f"N = {n_calc} (lẻ, Type I). Giới hạn HW: {N_MAX_HW} taps.")
            if n_calc > N_MAX_HW:
                st.error(f"N={n_calc} > {N_MAX_HW} taps!")

            st.metric("Trễ nhóm", f"{gd_display} mẫu",
                      help="(N−1)/2 mẫu — Bộ lọc tuyến tính pha Type I")
            st.metric("β Kaiser", beta_display,
                      help="Tham số hình dạng cửa sổ Kaiser")

    # ── Button row ──
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    btn_col1, btn_col2 = st.columns([1, 2])
    with btn_col1:
        if st.button("🔄 Nhập thông số mới", use_container_width=True,
                     disabled=not st.session_state.design_done,
                     help="Mở khóa các trường nhập liệu để điều chỉnh thông số"):
            st.session_state['design_done'] = False
            st.rerun()

    input_valid = len(errors) == 0
    if st.session_state['processing']:
        btn_label = "⏳ Đang tính toán..."
    elif st.session_state.design_done:
        btn_label = "✅ Tính toán hoàn tất"
    else:
        btn_label = "✨ Kích hoạt Tính toán & Thiết kế Bộ lọc"
    with btn_col2:
        if st.button(
            btn_label,
            type="primary", use_container_width=True,
            disabled=not input_valid or st.session_state['processing'],
            help="Tính toán hệ số bộ lọc FIR Kaiser và tạo tín hiệu test"
        ):
            st.session_state['processing'] = True
            st.rerun()

    # ── Processing block ──
    if st.session_state['processing']:
        try:
            with st.spinner("⏳ Đang tính toán..."):
                width = (fst - fp) / (fs / 2)
                n, beta = signal.kaiserord(float(a), width)
                if n % 2 == 0:
                    n += 1

                if n > N_MAX_HW:
                    st.error(f"N = {n} vượt quá N_MAX_HW = {N_MAX_HW}. Tăng Δf hoặc giảm A.")
                    st.stop()

                bits = 16
                h = signal.firwin(n, (fp + fst) / 2, window=('kaiser', beta), fs=fs)
                scale = 2 ** (bits - 1) - 1
                hq = np.clip(np.round(h * scale), -scale, scale).astype(int)

                hq_padded = np.zeros(N_MAX_HW, dtype=int)
                hq_padded[:n] = hq

                t = np.linspace(0, N_SAMPLES / fs, N_SAMPLES, endpoint=False)
                sig_raw = 0.5 * chirp(t, f0=0, f1=fs/2, t1=t[-1], method='linear')
                f_inst = (fs / 2) * (t / t[-1])
                clean_sig_raw = np.where(f_inst <= fp, sig_raw, 0.0)

                sig_q       = np.clip(np.round(sig_raw       * scale), -scale, scale).astype(int)
                clean_sig_q = np.clip(np.round(clean_sig_raw * scale), -scale, scale).astype(int)

                st.session_state.update({
                    'hq': hq, 'hq_padded': hq_padded, 'sig_q': sig_q, 'clean_sig_q': clean_sig_q,
                    'n': n, 'fs': fs, 'fp': fp, 'fst': fst,
                    'bits': bits, 'a': a, 'beta': beta, 'h_float': h, 'design_done': True,
                    'switch_to_tab2': True,
                })
        finally:
            st.session_state['processing'] = False
        st.rerun()




# ╔══════════════════════════════════════════════════════╗
# ║  TAB 2 — MÔ PHỎNG                                   ║
# ╚══════════════════════════════════════════════════════╝
with tab2:
    if not st.session_state.design_done:
        st.markdown("""
        <div style="text-align:center; padding:60px 20px;">
            <div style="font-size:56px; margin-bottom:16px;">📊</div>
            <div style="font-size:22px; font-weight:800; color:#1e293b; margin-bottom:8px;">Chưa có dữ liệu mô phỏng</div>
            <div style="font-size:15px; color:#64748b;">Vui lòng hoàn thành bước thiết kế ở tab <strong>🎛️ THIẾT KẾ</strong>
            <br>và nhấn <strong>"Kích hoạt Tính toán"</strong> để tiếp tục.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        n       = st.session_state['n']
        h       = st.session_state['h_float']
        fs_val  = st.session_state['fs']
        fp_val  = st.session_state['fp']
        fst_val = st.session_state['fst']
        a_val   = st.session_state['a']
        bits    = st.session_state['bits']

        # ══ PHẦN 1 — ĐÁP ỨNG TẦN SỐ ══════════════════════
        st.markdown("""
        <div class="step-heading">
            <div class="step-number">2</div>
            <div style="font-size:22px; font-weight:700; color:#0f172a; letter-spacing:-0.02em;">
                Đáp ứng tần số của bộ lọc
            </div>
        </div>
        """, unsafe_allow_html=True)

        w_rad, hh = signal.freqz(h, worN=8000)
        hh_mag    = np.abs(hh)
        w         = w_rad * fs_val / (2 * np.pi)

        M       = len(h) - 1
        hh_real = np.real(hh * np.exp(1j * w_rad * M / 2))

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

        with st.container(border=True):
            col_plot1, col_plot2 = st.columns(2)

            with col_plot1:
                hh_dB = 20 * np.log10(np.maximum(hh_mag, 1e-10))
                pb_max_dB = 20 * np.log10(max(pb_max, 1e-10))
                pb_min_dB = 20 * np.log10(max(pb_min, 1e-10))
                delta2_dB = 20 * np.log10(delta2) if delta2 > 0 else -100
                fc_dB     = 20 * np.log10(1 / np.sqrt(2))

                y_db_top    = pb_max_dB + 5
                y_db_bottom = min(-a_val - 15, -60)
                y_range_db  = y_db_top - y_db_bottom

                fig_db, ax_db = plt.subplots(1, 1, figsize=(11, 6))
                fig_db.subplots_adjust(left=0.12, right=0.96, top=0.88, bottom=0.24)
                ax_db.set_title("Đáp ứng biên độ bộ lọc trên thang đo logarit (dB)")

                ax_db.plot(w, hh_dB, color='black', linewidth=2, zorder=5)
                ax_db.axhline(pb_max_dB, color='green', linewidth=0.9, linestyle='--')
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
                ax_db.text(min(arrow_x * 1.03, fs_val/2 * 0.95),
                           (pb_max_dB + (-a_val)) / 2,
                           f'A = {a_val:.2f} dB',
                           color='red', fontsize=9, va='center', fontweight='bold')

                pass_pct_db  = fp_val             / (fs_val/2) * 100
                trans_pct_db = (fst_val - fp_val) / (fs_val/2) * 100
                label_y_db   = (y_db_top + y_db_bottom) / 2

                ax_db.text(fp_val / 2,               label_y_db,
                           'Dải thông' if pass_pct_db > 8 else '',
                           color='green', fontsize=10, ha='center', va='center', style='italic')
                ax_db.text((fp_val + fst_val) / 2,   label_y_db,
                           'Dải chuyển tiếp' if trans_pct_db > 8 else '',
                           color='gray',  fontsize=10, ha='center', va='center', style='italic')
                ax_db.text((fst_val + fs_val/2) / 2, label_y_db,
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
                    (fp_val,  'Fp', f'{fp_val:.0f} Hz',  'green'),
                    (fc_val,  'Fc', f'{fc_val:.0f} Hz',  'black'),
                    (fst_val, 'Fstop', f'{fst_val:.0f} Hz', 'red'),
                ]):
                    ax_db.text(xpos, y_sym_db + y_offsets[i], sym,
                               color=col, fontsize=9,   ha='center', va='top', clip_on=False)
                    ax_db.text(xpos, y_hz_db  + y_offsets[i], hz_str,
                               color=col, fontsize=7.5, ha='center', va='top', clip_on=False)

                ax_db.text(fs_val/2 * 0.985, y_sym_db, 'π',
                           color='black', fontsize=11, fontweight='bold', ha='center', va='top', clip_on=False)

                ax_db.set_xlim([0, fs_val / 2])
                ax_db.set_ylim([y_db_bottom, y_db_top])
                ax_db.set_ylabel('Biên độ (dB)', fontsize=11)
                ax_db.grid(True, alpha=0.20, linestyle='--')
                ax_db.spines['top'].set_visible(False)
                ax_db.spines['right'].set_visible(False)
                st.pyplot(fig_db)

            with col_plot2:
                y_top    = pb_max + 0.15
                y_bottom = -delta2 * 8.0
                y_range  = y_top - y_bottom

                fig_res, ax_res = plt.subplots(1, 1, figsize=(11, 6))
                fig_res.subplots_adjust(left=0.12, right=0.96, top=0.88, bottom=0.24)
                ax_res.set_title("Đáp ứng biên độ bộ lọc trên thang đo tuyến tính |H(e^jω)|")

                ax_res.set_xlim([0, fs_val / 2])
                ax_res.set_ylim([y_bottom, y_top])
                ax_res.plot(w, hh_mag, color='black', linewidth=2, zorder=5)
                ax_res.axhline(0, color='black', linewidth=0.8)

                ax_res.vlines(fp_val,  y_bottom, y_top-0.05, colors='green', linestyles='--', linewidth=1.3)
                ax_res.vlines(fc_val,  y_bottom, y_top-0.05, colors='black', linestyles='--', linewidth=1.3)
                ax_res.vlines(fst_val, y_bottom, y_top-0.05, colors='red',   linestyles='--', linewidth=1.3)

                pass_pct_plot  = fp_val              / (fs_val/2) * 100
                trans_pct_plot = (fst_val - fp_val)  / (fs_val/2) * 100
                stop_pct_plot  = (fs_val/2 - fst_val)/ (fs_val/2) * 100

                ax_res.text(fp_val * 0.42, pb_max * 0.30,
                            'Dải thông' if pass_pct_plot > 8 else '',
                            color='green', fontsize=10, ha='center', style='italic')
                ax_res.text((fp_val + fst_val) / 2, pb_max * 0.65,
                            'Dải chuyển tiếp' if trans_pct_plot > 8 else '',
                            color='black', fontsize=10, ha='center', style='italic')
                ax_res.text((fst_val + fs_val/2) / 2, pb_max * 0.30,
                            'Dải chặn' if stop_pct_plot > 8 else '',
                            color='red', fontsize=10, ha='center', style='italic')

                ax_res.set_xticks([fp_val, fc_val, fst_val])
                ax_res.set_xticklabels(['', '', ''])
                ax_res.tick_params(axis='x', length=0)

                y_sym = y_bottom - y_range * 0.040
                y_hz  = y_bottom - y_range * 0.090
                step  = y_range * 0.055
                min_gap_pct = (fst_val - fp_val) / (fs_val / 2) * 100
                y_offsets   = [0, -step, -step*2] if min_gap_pct < 10 else [0, 0, 0]

                for i, (xpos, sym, hz_str, col) in enumerate([
                    (fp_val,  'Fp', f'{fp_val:.0f} Hz',  'green'),
                    (fc_val,  'Fc', f'{fc_val:.0f} Hz',  'black'),
                    (fst_val, 'Fstop', f'{fst_val:.0f} Hz', 'red'),
                ]):
                    ax_res.text(xpos, y_sym + y_offsets[i], sym,
                                color=col, fontsize=9,   ha='center', va='top', clip_on=False)
                    ax_res.text(xpos, y_hz  + y_offsets[i], hz_str,
                                color=col, fontsize=7.5, ha='center', va='top', clip_on=False)
                ax_res.text(fs_val/2 * 0.985, y_sym, 'π', color='gray', fontsize=9, ha='center', va='top', clip_on=False)

                ax_res.set_ylabel(r'$|H(e^{j\omega})|$', fontsize=11)
                ax_res.grid(False)
                ax_res.spines['top'].set_visible(False)
                ax_res.spines['right'].set_visible(False)
                st.pyplot(fig_res)

        # ── Expander: Ripple chi tiết ──
        with st.expander("🔍 Xem thêm: Phân tích chi tiết độ gợn sóng (ripple) trên các dải", expanded=False):
            fig2, (ax_pb, ax_sb) = plt.subplots(1, 2, figsize=(14, 5))
            fig2.subplots_adjust(left=0.08, right=0.97, top=0.85, bottom=0.15, wspace=0.35)
            fig2.suptitle("Phân tích chi tiết độ gợn sóng (ripple) trên các dải")

            pb_margin = (pb_top - pb_bot) * 3.0
            ax_pb.plot(pass_w, real_pass, color='#2ecc71', linewidth=1.5)
            ax_pb.hlines(pb_top, 0, fp_val, colors='green', linestyles='--', linewidth=1.0,
                         label=f'1+δ₁ = {pb_top:.5f}')
            ax_pb.hlines(pb_bot, 0, fp_val, colors='green', linestyles='--', linewidth=1.0,
                         label=f'1-δ₁ = {pb_bot:.5f}')
            ax_pb.axhline(1.0, color='black', linewidth=0.8, linestyle=':')
            ax_pb.fill_between(pass_w, real_pass, 1.0, where=(real_pass > 1.0), color='#2ecc71', alpha=0.22)
            ax_pb.fill_between(pass_w, real_pass, 1.0, where=(real_pass < 1.0), color='#e67e22', alpha=0.18)
            ax_pb.set_xlim([0, fp_val])
            ax_pb.set_ylim([1.0 - pb_margin, 1.0 + pb_margin])
            ax_pb.set_title('Chi tiết độ gợn dải thông', fontsize=11, fontweight='bold', color='green', pad=10)
            ax_pb.set_xlabel('Tần số (Hz)', fontsize=9)
            ax_pb.set_ylabel('Biên độ Tuyến tính', fontsize=9)
            ax_pb.tick_params(labelsize=8)
            ax_pb.legend(fontsize=8, loc='upper right', framealpha=0.8)
            ax_pb.grid(True, alpha=0.25, linestyle='--')
            ax_pb.spines['top'].set_visible(False)
            ax_pb.spines['right'].set_visible(False)
            ann_x = pass_w[len(pass_w) // 4]
            ax_pb.annotate('', xy=(ann_x, pb_top), xytext=(ann_x, pb_bot),
                           arrowprops=dict(arrowstyle='<->', color='gray', lw=1.0))

            sb_margin = max(abs(sb_top), abs(sb_bot)) * 3.5
            ax_sb.plot(stop_w, real_stop, color='black', linewidth=1.5)
            ax_sb.hlines(sb_top, fst_val, fs_val/2, colors='red', linestyles='--', linewidth=1.0,
                         label=f'+δ₂ = {sb_top:.5f}')
            ax_sb.hlines(sb_bot, fst_val, fs_val/2, colors='red', linestyles='--', linewidth=1.0,
                         label=f'-δ₂ = {sb_bot:.5f}')
            ax_sb.axhline(0, color='black', linewidth=0.8)
            ax_sb.fill_between(stop_w, real_stop, 0, where=(real_stop > 0), color='#3498db', alpha=0.20)
            ax_sb.fill_between(stop_w, real_stop, 0, where=(real_stop < 0), color='#e74c3c', alpha=0.20)
            ax_sb.set_xlim([fst_val, fs_val / 2])
            ax_sb.set_ylim([-sb_margin, sb_margin])
            ax_sb.set_title('Chi tiết độ gợn dải chặn', fontsize=11, fontweight='bold', color='red', pad=10)
            ax_sb.set_xlabel('Tần số (Hz)', fontsize=9)
            ax_sb.set_ylabel('Biên độ Tuyến tính', fontsize=9)
            ax_sb.tick_params(labelsize=8)
            ax_sb.legend(fontsize=8, loc='upper right', framealpha=0.8)
            ax_sb.grid(True, alpha=0.25, linestyle='--')
            ax_sb.spines['top'].set_visible(False)
            ax_sb.spines['right'].set_visible(False)
            st.pyplot(fig2)
# ╔══════════════════════════════════════════════════════╗
# ║  TAB 3 — TẠO TÍN HIỆU THỬ & ĐÓNG GÓI TỆP            ║
# ╚══════════════════════════════════════════════════════╝
with tab3:
    if not st.session_state.design_done:
        st.markdown("""
        <div style="text-align:center; padding:60px 20px;">
            <div style="font-size:56px; margin-bottom:16px;">📦</div>
            <div style="font-size:22px; font-weight:800; color:#1e293b; margin-bottom:8px;">Chưa có dữ liệu tín hiệu thử nghiệm</div>
            <div style="font-size:15px; color:#64748b;">Vui lòng hoàn thành bước thiết kế ở tab <strong>🎛️ Thiết kế </strong>
            <br>và nhấn <strong>"Kích hoạt Tính toán"</strong> để tiếp tục.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        n       = st.session_state['n']
        fs_val  = st.session_state['fs']
        bits    = st.session_state['bits']

        # ══ PHẦN 2 — TÍN HIỆU TEST ════════════════════════
        st.markdown("""
        <div class="step-heading">
            <div class="step-number">3</div>
            <div style="font-size:22px; font-weight:700; color:#0f172a; letter-spacing:-0.02em;">
                Kích hoạt tín hiệu thử nghiệm
            </div>
        </div>
        """, unsafe_allow_html=True)

        sig_q_plot       = st.session_state['sig_q']
        clean_sig_q_plot = st.session_state['clean_sig_q']
        scale_plot       = 2 ** (bits - 1) - 1
        fs_plot          = fs_val

        t_plot           = np.arange(len(sig_q_plot)) / fs_plot
        sig_float_plot   = sig_q_plot / scale_plot
        clean_float_plot = clean_sig_q_plot / scale_plot
        zoom_sig         = min(len(sig_float_plot), N_SAMPLES)

        with st.container(border=True):
            col_sig1, col_sig2 = st.columns(2)

            with col_sig1:
                fig_sig_in, ax_sig_in = plt.subplots(figsize=(11, 5.5))
                ax_sig_in.plot(t_plot[:zoom_sig], sig_float_plot[:zoom_sig],
                               color='#3498db', linewidth=1.2)
                ax_sig_in.set_ylabel("Biên độ (V)")
                ax_sig_in.set_xlabel("Thời gian (s)")
                ax_sig_in.set_title("Tín hiệu đầu vào quét tần số (0-Fs/2)")
                ax_sig_in.grid(True, alpha=0.3, linestyle='--')
                ax_sig_in.spines['top'].set_visible(False)
                ax_sig_in.spines['right'].set_visible(False)
                st.pyplot(fig_sig_in)

            with col_sig2:
                dirac_float = np.zeros(zoom_sig)
                dirac_float[0] = 1.0
                fig_sig_out, ax_sig_out = plt.subplots(figsize=(11, 5.5))
                ax_sig_out.plot(t_plot[:zoom_sig], dirac_float,
                                color='#2ecc71', linewidth=1.2)
                ax_sig_out.set_ylabel("Biên độ (V)")
                ax_sig_out.set_xlabel("Thời gian (s)")
                ax_sig_out.set_title("Tín hiệu xung Dirac đầu vào")
                ax_sig_out.grid(True, alpha=0.3, linestyle='--')
                ax_sig_out.spines['top'].set_visible(False)
                ax_sig_out.spines['right'].set_visible(False)
                st.pyplot(fig_sig_out)

        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

        # ══ PHẦN 3 — XUẤT FILE ════════════════════════════
        st.markdown("""
        <div class="step-heading">
            <div class="step-number">4</div>
            <div style="font-size:22px; font-weight:700; color:#0f172a; letter-spacing:-0.02em;">
                Đóng gói và xuất tệp cấu hình hệ thống
            </div>
        </div>
        """, unsafe_allow_html=True)

        scale_val = 2 ** (bits - 1) - 1

        sig_q_full = np.zeros(N_SAMPLES, dtype=int)
        sig_q_full[:len(st.session_state['sig_q'])] = st.session_state['sig_q']
        hex_input_chirp = "\n".join([float_to_hex2s(v, bits) for v in sig_q_full])

        dirac_q = [0] * N_SAMPLES
        dirac_q[0] = scale_val
        hex_input_dirac = "\n".join([float_to_hex2s(v, bits) for v in dirac_q])

        hq_padded_export = st.session_state.get('hq_padded', st.session_state['hq'])
        hex_coeffs = "\n".join([float_to_hex2s(v, bits) for v in hq_padded_export])
        vh_config  = (
            f"parameter N_MAX_HW  = {N_MAX_HW};   // Kích thước thanh ghi dịch (cố định trong FPGA)\n"
            f"parameter N_ACTIVE  = {n};   // Số tap thực tế Kaiser (gửi qua UART)\n"
            f"parameter N_SAMPLES = {N_SAMPLES};  // Số mẫu tín hiệu test\n"
            f"// beta = {st.session_state.get('beta', 0):.4f}\n"
            f"// As   = {st.session_state['a']:.1f} dB\n"
            f"// Fp   = {st.session_state['fp']} Hz, Fstop= {st.session_state['fst']} Hz\n"
            f"// Fs   = {st.session_state['fs']} Hz, Bits = {bits}"
        )

        import base64
        b64_coeff = base64.b64encode(hex_coeffs.encode('utf-8')).decode('utf-8')
        b64_chirp = base64.b64encode(hex_input_chirp.encode('utf-8')).decode('utf-8')
        b64_dirac = base64.b64encode(hex_input_dirac.encode('utf-8')).decode('utf-8')
        b64_vh    = base64.b64encode(vh_config.encode('utf-8')).decode('utf-8')

        with st.container(border=True):
            st.markdown(f"""<div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:8px;">
<!-- Card 1: coeff.hex -->
<a href="data:text/plain;base64,{b64_coeff}" download="coeff.hex" style="text-decoration:none; color:inherit;">
    <div style="background:#f8fafc; border:1.5px solid #e2e8f0; border-radius:10px; padding:16px 20px; display:flex; align-items:center; gap:12px; transition:all 0.2s ease-in-out; cursor:pointer;"
         onmouseover="this.style.borderColor='#1d4ed8'; this.style.backgroundColor='#eff6ff'; this.style.transform='translateY(-1px)';" 
         onmouseout="this.style.borderColor='#e2e8f0'; this.style.backgroundColor='#f8fafc'; this.style.transform='none';">
        <span style="font-size:24px;">💾</span>
        <div style="flex-grow:1;">
            <div style="font-weight:700; color:#0f172a; font-size:14px; display:flex; justify-content:space-between; align-items:center;">
                <span>coeff.hex</span>
                <span style="font-size:11px; color:#1d4ed8; font-weight:600; background:#dbeafe; padding:2px 8px; border-radius:12px;">📥 Tải về ({len(hq_padded_export)} hệ số)</span>
            </div>
            <div style="color:#475569; font-size:12px; margin-top:2px;">Hệ số bộ lọc (ROM)</div>
        </div>
    </div>
</a>

<!-- Card 2: input_chirp.hex -->
<a href="data:text/plain;base64,{b64_chirp}" download="input_chirp.hex" style="text-decoration:none; color:inherit;">
    <div style="background:#f8fafc; border:1.5px solid #e2e8f0; border-radius:10px; padding:16px 20px; display:flex; align-items:center; gap:12px; transition:all 0.2s ease-in-out; cursor:pointer;"
         onmouseover="this.style.borderColor='#1d4ed8'; this.style.backgroundColor='#eff6ff'; this.style.transform='translateY(-1px)';" 
         onmouseout="this.style.borderColor='#e2e8f0'; this.style.backgroundColor='#f8fafc'; this.style.transform='none';">
        <span style="font-size:24px;">💾</span>
        <div style="flex-grow:1;">
            <div style="font-weight:700; color:#0f172a; font-size:14px; display:flex; justify-content:space-between; align-items:center;">
                <span>input_chirp.hex</span>
                <span style="font-size:11px; color:#1d4ed8; font-weight:600; background:#dbeafe; padding:2px 8px; border-radius:12px;">📥 Tải về</span>
            </div>
            <div style="color:#475569; font-size:12px; margin-top:2px;">ROM tín hiệu Chirp đầu vào (KEY2 thả)</div>
        </div>
    </div>
</a>

<!-- Card 3: input_dirac.hex -->
<a href="data:text/plain;base64,{b64_dirac}" download="input_dirac.hex" style="text-decoration:none; color:inherit;">
    <div style="background:#f8fafc; border:1.5px solid #e2e8f0; border-radius:10px; padding:16px 20px; display:flex; align-items:center; gap:12px; transition:all 0.2s ease-in-out; cursor:pointer;"
         onmouseover="this.style.borderColor='#1d4ed8'; this.style.backgroundColor='#eff6ff'; this.style.transform='translateY(-1px)';" 
         onmouseout="this.style.borderColor='#e2e8f0'; this.style.backgroundColor='#f8fafc'; this.style.transform='none';">
        <span style="font-size:24px;">💾</span>
        <div style="flex-grow:1;">
            <div style="font-weight:700; color:#0f172a; font-size:14px; display:flex; justify-content:space-between; align-items:center;">
                <span>input_dirac.hex</span>
                <span style="font-size:11px; color:#1d4ed8; font-weight:600; background:#dbeafe; padding:2px 8px; border-radius:12px;">📥 Tải về</span>
            </div>
            <div style="color:#475569; font-size:12px; margin-top:2px;">ROM tín hiệu Dirac đầu vào (KEY2 nhấn)</div>
        </div>
    </div>
</a>

<!-- Card 4: taps_config.vh -->
<a href="data:text/plain;base64,{b64_vh}" download="taps_config.vh" style="text-decoration:none; color:inherit;">
    <div style="background:#f8fafc; border:1.5px solid #e2e8f0; border-radius:10px; padding:16px 20px; display:flex; align-items:center; gap:12px; transition:all 0.2s ease-in-out; cursor:pointer;"
         onmouseover="this.style.borderColor='#1d4ed8'; this.style.backgroundColor='#eff6ff'; this.style.transform='translateY(-1px)';" 
         onmouseout="this.style.borderColor='#e2e8f0'; this.style.backgroundColor='#f8fafc'; this.style.transform='none';">
        <span style="font-size:24px;">📄</span>
        <div style="flex-grow:1;">
            <div style="font-weight:700; color:#0f172a; font-size:14px; display:flex; justify-content:space-between; align-items:center;">
                <span>taps_config.vh</span>
                <span style="font-size:11px; color:#1d4ed8; font-weight:600; background:#dbeafe; padding:2px 8px; border-radius:12px;">📥 Tải về</span>
            </div>
            <div style="color:#475569; font-size:12px; margin-top:2px;">Khai báo tham số phần cứng Verilog</div>
        </div>
    </div>
</a>
</div>""", unsafe_allow_html=True)




# ╔══════════════════════════════════════════════════════╗
# ║  TAB 4 — KIỂM CHỨNG THỰC NGHIỆM                    ║
# ╚══════════════════════════════════════════════════════╝
with tab4:
    st.markdown("""
    <div class="step-heading">
        <div class="step-number">5</div>
        <div>
            <div style="font-size:22px; font-weight:700; color:#0f172a; letter-spacing:-0.02em;">
                Kiểm chứng FIR trên FPGA theo miền thời gian và miền tần số
            </div>
            <div style="font-size:13px; color:#334155; margin-top:2px; font-weight:500;">
                So sánh kết quả thực nghiệm từ FPGA với mô phỏng Python và tín hiệu tham chiếu.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.design_done:
        st.markdown("""
        <div style="background:#fffbeb; border:1.5px solid #fde68a; border-radius:12px; padding:16px 20px;
                    display:flex; align-items:center; gap:12px; margin-bottom:20px;">
            <span style="font-size:24px;">⚠️</span>
            <div>
                <div style="font-weight:700; color:#92400e;">Chưa có thiết kế</div>
                <div style="color:#b45309; font-size:13px;">Vui lòng hoàn thành <strong>Tab THIẾT KẾ</strong> trước khi kiểm chứng.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        Q_IN  = st.session_state['bits'] - 1
        Q_OUT = Q_IN * 2
        hq    = st.session_state['hq']
        sig_q = st.session_state['sig_q']
        a_target = st.session_state.get('a', 30)
        fs_val   = st.session_state['fs']
        fp_val   = st.session_state['fp']
        fst_val  = st.session_state['fst']
        h        = st.session_state['h_float']
        n        = st.session_state['n']

        def decode_hex_output(uploaded_file):
            content  = uploaded_file.getvalue().decode().splitlines()
            out_raw  = [int(x.strip(), 16) for x in content if x.strip()]
            out_data = []
            for v in out_raw:
                v_41 = v & ((1 << 41) - 1)
                out_data.append(v_41 - (1 << 41) if v_41 >= (1 << 40) else v_41)
            return np.array(out_data)

        col_chirp, col_dirac = st.columns(2, gap="large")

        with col_chirp:
            # ── LUỒNG 1: CHIRP ──────────────────────────────────
            st.markdown("""
            <div style="border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px 16px; margin: 16px 0 12px 0; background-color: #f8fafc;">
                <div style="font-size: 14px; font-weight: 700; color: #0f172a; margin-bottom: 4px;">
                    TEST 1 – Chirp: Kiểm chứng miền thời gian
                </div>
                <div style="font-size: 12px; color: #64748b; font-weight: 400;">
                    Đánh giá đầu ra FIR theo từng mẫu khi xử lý tín hiệu Chirp.
                </div>
            </div>
            """, unsafe_allow_html=True)

            def _on_chirp_upload():
                st.session_state['switch_to_tab3'] = True

            uploaded_chirp = st.file_uploader(
                "📂 Tải lên tệp kết quả output_chirp.hex",
                type=["hex"], key="chirp",
                help="File hex 41-bit two's complement từ FPGA",
                on_change=_on_chirp_upload
            )

            if uploaded_chirp and st.session_state.design_done:
                out_data_chirp   = decode_hex_output(uploaded_chirp)
                if len(out_data_chirp) != N_SAMPLES:
                    st.warning(f"Số mẫu nhận được: {len(out_data_chirp)} (kỳ vọng {N_SAMPLES})")
                fpga_chirp_float = out_data_chirp / (1 << Q_OUT)

                y_python_full    = np.convolve(sig_q, hq)
                python_float_raw = y_python_full / (1 << Q_OUT)
                scale_val        = (1 << Q_IN) - 1
                clean_ideal      = st.session_state['clean_sig_q'] / scale_val

                python_aligned = python_float_raw[:N_SAMPLES]
                fpga_aligned   = fpga_chirp_float[:N_SAMPLES]

                # ── HÌNH 1: FPGA vs Python (không bù delay) ──────────
                min_len_1 = min(len(fpga_aligned), len(python_aligned))
                fpga_c1   = fpga_aligned[:min_len_1]
                python_c1 = python_aligned[:min_len_1]

                error_c1   = fpga_c1 - python_c1
                mse_c1     = np.mean(error_c1 ** 2) if min_len_1 > 0 else 0
                max_err_c1 = np.max(np.abs(error_c1)) if min_len_1 > 0 else 0

                st.markdown("<div style='text-align:center; font-weight:700; font-size:15px; margin:8px 0;'>So sánh đầu ra Chirp giữa FPGA và Python</div>", unsafe_allow_html=True)
                with st.container(border=True):
                    col_m1, col_m2 = st.columns(2)
                    col_m1.metric("MSE giữa FPGA và Python", format_sci_unicode(mse_c1),
                                  help=f"Giá trị đầy đủ: {mse_c1:.12f}")
                    col_m2.metric("Max Error giữa FPGA và Python", format_sci_unicode(max_err_c1),
                                  help=f"Giá trị đầy đủ: {max_err_c1:.10f}")

                    fig_c1, ax_c1 = plt.subplots(figsize=(10, 4))
                    ax_c1.plot(python_c1, color='black', linewidth=2.5,
                               label='Đầu ra mô phỏng Python')
                    ax_c1.plot(fpga_c1, color='#1f77b4', linewidth=1.8,
                               linestyle='--', label='Đầu ra thực nghiệm từ FPGA')
                    ax_c1.set_xlabel("Số mẫu")
                    ax_c1.set_ylabel("Biên độ (V)")
                    ax_c1.legend(loc='upper right')
                    ax_c1.grid(True, alpha=0.3, linestyle='--')
                    ax_c1.spines['top'].set_visible(False)
                    ax_c1.spines['right'].set_visible(False)
                    st.pyplot(fig_c1, use_container_width=True)

                    df_c1 = pd.DataFrame({
                        'Sample_Index':         np.arange(min_len_1),
                        'Golden_Python':        python_c1,
                        'FPGA_Output':          fpga_c1,
                        'Error_FPGA_vs_Python': error_c1
                    })
                    st.download_button(
                        "📥 Xuất bảng dữ liệu so sánh FPGA vs Python (CSV)",
                        df_c1.to_csv(index=False).encode('utf-8'),
                        'output_chirp_fpga_vs_python.csv', 'text/csv', use_container_width=True
                    )

                # ── HÌNH 2: FPGA vs Lý tưởng (có bù delay) ───────────
                st.markdown("<div style='text-align:center; font-weight:700; font-size:15px; margin:8px 0;'>So sánh đầu từ FPGA với đầu ra lý tưởng sau lọc</div>", unsafe_allow_html=True)
                with st.container(border=True):
                    theory_delay = (n - 1) // 2

                    # Thuật toán quét MSE tối thiểu để tìm trễ thực tế tối ưu
                    best_delay = 0
                    min_mse = float('inf')
                    for d in range(151):
                        compare_len_test = N_SAMPLES - d
                        if compare_len_test > 50:
                            err = fpga_aligned[d : d + compare_len_test] - clean_ideal[:compare_len_test]
                            mse = np.mean(err ** 2)
                            if mse < min_mse:
                                min_mse = mse
                                best_delay = d

                    # Hiển thị kết quả delay ngắn gọn
                    col_delay1, col_delay2 = st.columns(2)
                    col_delay1.metric(
                        "Trễ nhóm thực tế",
                        f"{best_delay} mẫu",
                        help=f"Sai số bình phương trung bình (MSE) nhỏ nhất tại delay này: {min_mse:.4e}"
                    )
                    col_delay2.metric(
                        "Trễ nhóm lý thuyết",
                        f"{theory_delay} mẫu",
                        help=f"Tính từ bộ lọc {n} taps: (N-1)/2 = {theory_delay}"
                    )
                    st.markdown(f"<div style='text-align:center; font-size:13px; color:#64748b; margin-top:4px;'>MSE nhỏ nhất tại delay = {best_delay} mẫu: <b>{min_mse:.6f}</b></div>", unsafe_allow_html=True)

                    # Vẽ đồ thị RAW không căn chỉnh delay
                    plot_len = min(len(fpga_aligned), len(clean_ideal))
                    fig_c2, ax_c2 = plt.subplots(figsize=(10, 4))
                    ax_c2.plot(clean_ideal[:plot_len], color='#2ecc71', linewidth=3, alpha=0.7,
                               label='Tín hiệu mong muốn lý tưởng')
                    ax_c2.plot(fpga_aligned[:plot_len], color='#1f77b4', linewidth=1.8,
                               linestyle='--', label='Đầu ra thực nghiệm từ FPGA')
                    ax_c2.set_xlabel("Số mẫu")
                    ax_c2.set_ylabel("Biên độ (V)")
                    ax_c2.legend(loc='upper right')
                    ax_c2.grid(True, alpha=0.3, linestyle='--')
                    ax_c2.spines['top'].set_visible(False)
                    ax_c2.spines['right'].set_visible(False)
                    st.pyplot(fig_c2, use_container_width=True)

                    # CSV xuất theo delay tối ưu (có bù)
                    compare_len = N_SAMPLES - best_delay
                    if compare_len > 0:
                        fpga_c2    = fpga_aligned[best_delay : best_delay + compare_len]
                        clean_c2   = clean_ideal[:compare_len]
                        error_clean = fpga_c2 - clean_c2
                        df_c2 = pd.DataFrame({
                            'Sample_Index':        np.arange(compare_len),
                            'Clean_Target':        clean_c2,
                            'FPGA_Output':         fpga_c2,
                            'Error_FPGA_vs_Ideal': error_clean
                        })
                        st.download_button(
                            "📥 Xuất bảng dữ liệu so sánh FPGA vs Bộ lọc lý tưởng (CSV)",
                            df_c2.to_csv(index=False).encode('utf-8'),
                            'output_chirp_fpga_vs_ideal.csv', 'text/csv', use_container_width=True
                        )

        with col_dirac:
            # ── LUỒNG 2: DIRAC ──────────────────────────────────
            st.markdown("""
            <div style="border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px 16px; margin: 16px 0 12px 0; background-color: #f8fafc;">
                <div style="font-size: 14px; font-weight: 700; color: #0f172a; margin-bottom: 4px;">
                    TEST 2 – Dirac: Kiểm chứng đáp ứng xung và tần số
                </div>
                <div style="font-size: 12px; color: #64748b; font-weight: 400;">
                    Dùng xung Dirac để thu đáp ứng xung và suy ra đáp ứng tần số của bộ lọc FIR.
                </div>
            </div>
            """, unsafe_allow_html=True)

            def _on_dirac_upload():
                st.session_state['switch_to_tab3'] = True

            uploaded_dirac = st.file_uploader(
                "📂 Tải lên tệp kết quả output_dirac.hex",
                type=["hex"], key="dirac",
                help="File hex 41-bit two's complement từ FPGA (chế độ Dirac)",
                on_change=_on_dirac_upload
            )

            if uploaded_dirac and st.session_state.design_done:
                out_data_dirac   = decode_hex_output(uploaded_dirac)
                if len(out_data_dirac) != N_SAMPLES:
                    st.warning(f"Số mẫu Dirac nhận được: {len(out_data_dirac)} (kỳ vọng {N_SAMPLES})")
                fpga_dirac_float = out_data_dirac / (1 << Q_OUT)

                # ── Chuẩn bị dữ liệu chung ──────────────────────────
                # h[n] gốc lý tưởng (chưa lượng tử hóa), đệm 0 cho đủ 200 mẫu
                h_ideal        = st.session_state['h_float']
                h_ideal_padded = np.zeros(N_MAX_HW)
                h_ideal_padded[:len(h_ideal)] = h_ideal
                n_h            = N_MAX_HW                               # luôn là 200
                # Output FPGA sau Dirac cũng là h[n] thực nghiệm
                fpga_h         = fpga_dirac_float[:n_h]


                st.markdown("<div style='text-align:center; font-weight:700; font-size:15px; margin:8px 0;'>Đáp ứng tần số bộ lọc FIR thực nghiệm từ FPGA (thang đo dB)</div>", unsafe_allow_html=True)
                with st.container(border=True):
                    fc_val = (fp_val + fst_val) / 2
                    N_fft = len(fpga_dirac_float)
                    xf    = fftfreq(N_fft, 1/fs_val)[:N_fft//2]

                    # Đáp ứng tần số Python: dùng signal.freqz như ở bước mô phỏng Tab 2
                    w_hz, H_python_cplx = signal.freqz(h, worN=N_fft//2, fs=fs_val)
                    H_python_dB = 20 * np.log10(np.abs(H_python_cplx) + 1e-10)

                    # Đáp ứng FPGA: FFT của output_dirac
                    H_fpga_dB   = 20 * np.log10(np.abs(fft(fpga_dirac_float, n=N_fft)[:N_fft//2]) + 1e-10)

                    fig2, ax2 = plt.subplots(figsize=(10, 5))
                    fig2.subplots_adjust(left=0.12, right=0.96, top=0.88, bottom=0.24)

                    pb_max_dB = 0.0
                    y_db_top    = pb_max_dB + 5
                    y_db_bottom = min(-a_target - 15, -60)
                    y_range_db  = y_db_top - y_db_bottom

                    ax2.plot(xf, H_fpga_dB, color='#1d4ed8', linewidth=1.6,
                               label="FFT(output_dirac) — FPGA (Thực nghiệm)")
                    ax2.hlines(-a_target, fst_val, fs_val/2, colors='red', linestyles='--',
                               linewidth=0.9, label=f"Ngưỡng suy hao ({-a_target:.1f} dB)")

                    ax2.vlines(fp_val,  y_db_bottom, y_db_top, colors='green', linestyles='--', linewidth=1.3)
                    ax2.vlines(fc_val,  y_db_bottom, y_db_top, colors='black', linestyles='--', linewidth=1.3)
                    ax2.vlines(fst_val, y_db_bottom, y_db_top, colors='red',   linestyles='--', linewidth=1.3)

                    pass_pct_db  = fp_val             / (fs_val/2) * 100
                    trans_pct_db = (fst_val - fp_val) / (fs_val/2) * 100
                    label_y_db   = (y_db_top + y_db_bottom) / 2

                    ax2.text(fp_val / 2,               label_y_db,
                               'Dải thông' if pass_pct_db > 8 else '',
                               color='green', fontsize=10, ha='center', va='center', style='italic')
                    ax2.text((fp_val + fst_val) / 2,   label_y_db,
                               'Dải chuyển tiếp' if trans_pct_db > 8 else '',
                               color='gray',  fontsize=10, ha='center', va='center', style='italic')
                    ax2.text((fst_val + fs_val/2) / 2, label_y_db,
                               'Dải chặn',
                               color='red',   fontsize=10, ha='center', va='center', style='italic')

                    ax2.set_xticks([fp_val, fc_val, fst_val])
                    ax2.set_xticklabels(['', '', ''])
                    ax2.tick_params(axis='x', length=0)

                    y_sym_db    = y_db_bottom - y_range_db * 0.040
                    y_hz_db     = y_db_bottom - y_range_db * 0.090
                    step_db     = y_range_db * 0.055
                    min_gap_pct = (fst_val - fp_val) / (fs_val / 2) * 100
                    y_offsets   = [0, -step_db, -step_db*2] if min_gap_pct < 10 else [0, 0, 0]

                    for i, (xpos, sym, hz_str, col) in enumerate([
                        (fp_val,  'Fp', f'{fp_val:.0f} Hz',  'green'),
                        (fc_val,  'Fc', f'{fc_val:.0f} Hz',  'black'),
                        (fst_val, 'Fstop', f'{fst_val:.0f} Hz', 'red'),
                    ]):
                        ax2.text(xpos, y_sym_db + y_offsets[i], sym,
                                   color=col, fontsize=9,   ha='center', va='top', clip_on=False)
                        ax2.text(xpos, y_hz_db  + y_offsets[i], hz_str,
                                   color=col, fontsize=7.5, ha='center', va='top', clip_on=False)
                    ax2.text(fs_val/2 * 0.985, y_sym_db, 'π', color='gray', fontsize=9, ha='center', va='top', clip_on=False)

                    ax2.set_xlim([0, fs_val / 2])
                    ax2.set_ylim([y_db_bottom, y_db_top])
                    ax2.set_ylabel('Biên độ (dB)', fontsize=11)
                    ax2.legend(loc='upper right', frameon=True)
                    ax2.grid(True, alpha=0.20, linestyle='--')
                    ax2.spines['top'].set_visible(False)
                    ax2.spines['right'].set_visible(False)
                    st.pyplot(fig2, use_container_width=True)

                st.markdown("<div style='text-align:center; font-weight:700; font-size:15px; margin:8px 0;'>Đáp ứng tần số bộ lọc FIR thực nghiệm từ FPGA (thang đo tuyến tính)</div>", unsafe_allow_html=True)
                with st.container(border=True):
                    fc_val = (fp_val + fst_val) / 2
                    H_fpga_linear = np.abs(fft(fpga_dirac_float, n=N_fft)[:N_fft//2])

                    fig3, ax3 = plt.subplots(figsize=(10, 5))
                    fig3.subplots_adjust(left=0.12, right=0.96, top=0.88, bottom=0.24)

                    y_top    = 1.15
                    y_bottom = -0.1
                    y_range  = y_top - y_bottom

                    ax3.set_xlim([0, fs_val / 2])
                    ax3.set_ylim([y_bottom, y_top])

                    ax3.plot(xf, H_fpga_linear, color='#1d4ed8', linewidth=1.6, zorder=5,
                             label="FFT(output_dirac) — FPGA (Thực nghiệm)")
                    ax3.axhline(0, color='black', linewidth=0.8)

                    ax3.vlines(fp_val,  y_bottom, y_top-0.05, colors='green', linestyles='--', linewidth=1.3)
                    ax3.vlines(fc_val,  y_bottom, y_top-0.05, colors='black', linestyles='--', linewidth=1.3)
                    ax3.vlines(fst_val, y_bottom, y_top-0.05, colors='red',   linestyles='--', linewidth=1.3)

                    pass_pct_plot  = fp_val              / (fs_val/2) * 100
                    trans_pct_plot = (fst_val - fp_val)  / (fs_val/2) * 100
                    stop_pct_plot  = (fs_val/2 - fst_val)/ (fs_val/2) * 100

                    ax3.text(fp_val * 0.42, 0.30,
                             'Dải thông' if pass_pct_plot > 8 else '',
                             color='green', fontsize=10, ha='center', style='italic')
                    ax3.text((fp_val + fst_val) / 2, 0.65,
                             'Dải chuyển tiếp' if trans_pct_plot > 8 else '',
                             color='black', fontsize=10, ha='center', style='italic')
                    ax3.text((fst_val + fs_val/2) / 2, 0.30,
                             'Dải chặn' if stop_pct_plot > 8 else '',
                             color='red', fontsize=10, ha='center', style='italic')

                    ax3.set_xticks([fp_val, fc_val, fst_val])
                    ax3.set_xticklabels(['', '', ''])
                    ax3.tick_params(axis='x', length=0)

                    y_sym = y_bottom - y_range * 0.040
                    y_hz  = y_bottom - y_range * 0.090
                    step  = y_range * 0.055
                    min_gap_pct = (fst_val - fp_val) / (fs_val / 2) * 100
                    y_offsets   = [0, -step, -step*2] if min_gap_pct < 10 else [0, 0, 0]

                    for i, (xpos, sym, hz_str, col) in enumerate([
                        (fp_val,  'Fp', f'{fp_val:.0f} Hz',  'green'),
                        (fc_val,  'Fc', f'{fc_val:.0f} Hz',  'black'),
                        (fst_val, 'Fstop', f'{fst_val:.0f} Hz', 'red'),
                    ]):
                        ax3.text(xpos, y_sym + y_offsets[i], sym,
                                 color=col, fontsize=9,   ha='center', va='top', clip_on=False)
                        ax3.text(xpos, y_hz  + y_offsets[i], hz_str,
                                 color=col, fontsize=7.5, ha='center', va='top', clip_on=False)
                    ax3.text(fs_val/2 * 0.985, y_sym, 'π', color='gray', fontsize=9, ha='center', va='top', clip_on=False)

                    ax3.set_ylabel(r'$|H(f)|$', fontsize=11)
                    ax3.legend(loc='upper right', frameon=True)
                    ax3.grid(False)
                    ax3.spines['top'].set_visible(False)
                    ax3.spines['right'].set_visible(False)
                    st.pyplot(fig3, use_container_width=True)

                # ── Chỉ số sai lệch ─────────────────────────────────
                mask_pass = (w_hz <= fp_val)
                mask_stop = (w_hz >= fst_val) & (w_hz <= fs_val/2)

                H_fpga_linear = np.abs(fft(fpga_dirac_float, n=N_fft)[:N_fft//2])
                ep_val = np.max(np.abs(H_fpga_linear[mask_pass] - 1.0)) if mask_pass.any() else 0.0
                es_val = np.max(H_fpga_linear[mask_stop]) if mask_stop.any() else 0.0

                col_d1, col_d2 = st.columns(2)
                col_d1.metric("Gợn cực đại dải thông (Ep)", format_sci_unicode(ep_val),
                              help="Độ gợn sóng cực đại trong dải thông (tuyến tính) so với mức lý tưởng 1.0.")
                col_d2.metric("Đỉnh rò cực đại dải chặn (Es)", format_sci_unicode(es_val),
                              help="Mức đỉnh rò rỉ lớn nhất trong dải chặn (tuyến tính).")

                st.download_button(
                    "📥 Xuất kết quả H(f) lý thuyết và FPGA (CSV)",
                    pd.DataFrame({
                        'Frequency_Hz':        xf,
                        'Python_Magnitude_dB': H_python_dB,
                        'FPGA_Magnitude_dB':   H_fpga_dB,
                    }).to_csv(index=False).encode('utf-8'),
                    'output_hf.csv', 'text/csv', use_container_width=True,
                    help="Dữ liệu so sánh đáp ứng tần số H(f) giữa thực tế FPGA và lý thuyết."
                )

# ── Sidebar info ────────────────────────────────────────
st.sidebar.markdown("""
<div style="text-align:center; margin-bottom:16px;">
    <div style="font-size:28px; margin-bottom:6px;">📟</div>
    <div style="font-weight:800; font-size:14px; color:#1e293b;">Tang Nano 9K</div>
    <div style="font-size:12px; color:#334155; font-weight:500;">FIR DSP Master</div>
</div>
""", unsafe_allow_html=True)
st.sidebar.markdown("---")
st.sidebar.markdown(f"**⚠️ Giới hạn phần cứng:** `{N_MAX_HW} Taps tối đa`\n*(1 DSP MAC, serial MAC)*")
st.sidebar.markdown("---")
st.sidebar.markdown(
    "**📋 Luồng sử dụng:**\n"
    "1. 🎛️ Nhập thông số bộ lọc\n"
    "2. ✨ Kích hoạt Tính toán\n"
    "3. 📊 Xem kết quả & tải file\n"
    "4. 🔌 Nạp vào FPGA, lấy output\n"
    "5. 🔬 Upload kết quả kiểm chứng"
)

if st.session_state.design_done:
    st.sidebar.markdown("---")
    st.sidebar.success(f"✅ Thiết kế: N={st.session_state.get('n','?')} taps | β={st.session_state.get('beta',0):.3f}")
