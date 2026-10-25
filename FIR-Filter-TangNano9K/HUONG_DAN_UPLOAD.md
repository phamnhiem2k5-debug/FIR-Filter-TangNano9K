# Hướng dẫn chạy và đưa project lên GitHub

## 1. Giải nén

Giải nén file ZIP. Em sẽ có thư mục `FIR-Filter-TangNano9K` với code, ảnh trích từ báo cáo, báo cáo PDF và hướng dẫn.

File Python và RTL được giữ nguyên nội dung đã gửi. Các file dữ liệu mẫu và hai script hỗ trợ được tạo thêm; chúng không phải kết quả mới đo từ FPGA.

## 2. Upload vào repository hiện có

1. Mở repository `FIR-Filter-TangNano9K` của em trên GitHub.
2. Đứng ở trang ngoài cùng của repository, không đứng bên trong `fir-fpga-project`.
3. Chọn **Add file → Upload files**.
4. Mở thư mục đã giải nén và kéo **các file, thư mục bên trong** lên: `README.md`, `fir-fpga-project`, `docs`, `reports`, `scripts`, `sim` và file hướng dẫn này.
5. Không kéo cả thư mục bọc `FIR-Filter-TangNano9K` vào repo cùng tên, để tránh bị lồng thêm một cấp.
6. Đọc lại danh sách thay đổi. Ghi commit: `Add FIR RTL, documentation, report figures, and example data`.
7. Chọn **Commit changes** trên nhánh đang sử dụng, thông thường là `main`.

Nếu GitHub hỏi ghi đè `README.md`, bản mới là README đã tổng hợp từ các tài liệu em gửi. Riêng `app.py`, hãy so sánh nếu em đã sửa code trên GitHub sau lần gửi cho mình. Không ghi đè một phiên bản mới hơn mà chưa kiểm tra.

Trên Windows, `.gitignore` có thể không dễ chọn trong hộp thoại. Có thể tạo riêng trên GitHub bằng **Add file → Create new file**, đặt tên `.gitignore`, rồi chép nội dung từ bản trong ZIP.

## 3. Giữ đường dẫn Streamlit

Gói này dùng:

```text
fir-fpga-project/app.py
fir-fpga-project/requirements.txt
```

Nếu app đang triển khai dùng đường dẫn này, em giữ nguyên. Nếu app cũ dùng `ap.py` hoặc file ở vị trí khác, cần chỉnh **Main file path** trong cấu hình triển khai cho khớp.

Sau commit, kiểm tra ứng dụng Streamlit và thử thiết kế bộ lọc, tải file input, mở README để xem các ảnh có hiển thị không. Thêm link Streamlit thật của em vào README sau khi kiểm tra truy cập thành công.

## 4. Chạy trên máy Windows

Mở Anaconda Prompt hoặc terminal. Chuyển đến thư mục vừa giải nén, ví dụ:

```bat
cd /d D:\FIR-Filter-TangNano9K
python -m pip install -r fir-fpga-project\requirements.txt
python -m streamlit run fir-fpga-project\app.py
```

Các đường dẫn ví dụ phải được thay bằng vị trí thật trên máy em.

## 5. Dữ liệu và ảnh có sẵn

- `docs/images/`: 44 ảnh gốc trích từ các trang thiết kế và kết quả của báo cáo.
- `docs/RESULTS_GALLERY.md`: xem ảnh cùng số trang PDF nguồn.
- `reports/project_report.pdf`: báo cáo gốc, giữ nguyên.
- `reports/gowin_resource_usage.txt`: bảng tài nguyên em đã cung cấp.
- `reports/gowin_timing_report.txt`: đoạn báo cáo timing em đã cung cấp.
- `fir-fpga-project/data/`: bộ hệ số 75 tap đệm thành 200, hai tín hiệu 1000 mẫu và đầu ra tham chiếu Python.

Không đổi tên `reference_chirp.hex` thành kết quả FPGA để chứng minh đã chạy phần cứng. Khi có output thật, đối chiếu bằng script hoặc app rồi đưa vào repo cùng thông tin cấu hình.

## 6. Phần chưa có trong tài liệu em gửi

Gói này chưa chứa project Gowin `.gprj` gốc, testbench gốc, `.sdc`, bitstream, chương trình truyền UART hoặc dữ liệu output đo thật. Hướng dẫn cấu hình lại phần cứng nằm trong `docs/HARDWARE_SETUP.md`.

Không cần chờ các file còn thiếu mới đưa tài liệu và code hiện có lên GitHub. README đã nêu đúng phạm vi để người xem hiểu nội dung có thể chạy và phần cần bổ sung.
