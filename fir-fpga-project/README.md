# 📟 FIR Filter DSP Master - Tang Nano 9K

Dự án thiết kế và kiểm chứng bộ lọc FIR trên phần cứng FPGA Gowin Tang Nano 9K.

## 📌 Tổng quan
Dự án này sử dụng Streamlit để tạo giao diện thiết kế bộ lọc, tự động tính toán hệ số Kaiser Window và xuất file `.hex` cho mô phỏng Vivado/Gowin.

## 🛠 Thông số kỹ thuật
- **Số Tap tối đa:** 39 (Tối ưu cho 20 bộ nhân DSP).
- **Cửa sổ:** Kaiser (Tự động tính Beta theo A và Delta F).
- **Độ phân giải:** 16-bit (Hệ số/Dữ liệu), 38-bit (Bộ cộng tích lũy).

## 🚀 Hướng dẫn chạy nhanh
1. Truy cập vào Link Web (Streamlit Cloud).
2. Nhập các thông số `Fs`, `Fpass`, `Fstop`.
3. Tải file `coeff.hex` và `input.hex` về máy.
4. Chạy mô phỏng trên FPGA và lấy file `output.hex`.
5. Upload ngược lại lên mục **Verify** để kiểm tra sai số.

## 📁 Danh sách file
- `app.py`: Mã nguồn ứng dụng Web.
- `requirements.txt`: Các thư viện Python cần thiết.
- `README.md`: Tài liệu hướng dẫn này.