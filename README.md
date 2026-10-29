# Automated 3D History Timelapse — Thăng Long, Hà Nội (1010–1900)

Dự án tự động hóa bằng **Python + Blender Headless + FFmpeg** nhằm sản xuất video lịch sử 3D điện ảnh dài **30 giây, 1920×1080 (Full HD), 30 fps (900 frames)** tái hiện tiến trình phát triển của Thăng Long — Hà Nội qua các mốc lịch sử trọng đại.

---

## 📌 Trạng thái Phát triển & Định hướng Mới

Dự án đã chuyển hướng sang **phong cách phim tài liệu điện ảnh 3D (Cinematic Documentary 3D Timelapse)** lấy cảm hứng từ các tác phẩm quốc tế ([Jerusalem 3D Timelapse](https://youtu.be/GagpWco3FPM)):

- **Tập trung vào các mốc lịch sử trọng đại (Milestone-focused Eras)** thay vì đếm năm dàn trải.
- **Hệ thống 5 Shot Camera Điện ảnh**: Cú lướt vệ tinh rơi thẳng đứng (Pure-Z Descent), xoay quanh kiến trúc (Hero Orbit), lướt tầm trung dọc sông Tô Lịch và kéo rộng toàn cảnh (Panoramic Pull-back).
- **Hạ tầng GIS thực tế 100%**: Bản đồ toàn quốc Việt Nam, mô hình cao độ số Copernicus DEM 30m, mạng lưới đường phố và sông ngòi OpenStreetMap trong hệ quy chiếu metric UTM Zone 48N (EPSG:32648).
- **Kiến trúc lịch sử chân thực**: Chùa Một Cột trên hồ sen Linh Chiểu, Cột Cờ Hà Nội 3 tầng chân đế đá, hệ thống tường thành Hoàng Thành Thăng Long và 2.400 căn nhà phố cổ.
- **Ánh sáng vật lý Nishita Sky**: Mặt trời sớm mai góc xiên 26° tạo bóng đổ dài đầy hoài niệm.

---

## 📚 Tài liệu Dự án

- 📖 **[docs/STATUS.md](docs/STATUS.md)** — **Báo cáo Tiến độ, Những gì chưa làm tốt và Giải pháp Điện ảnh Mới**: Phân tích chi tiết 5 nguyên nhân gốc rễ gây giật ở cú zoom mở đầu, bảng đối chiếu kỹ thuật và công thức toán học của giải pháp Pure-Z Smootherstep Swoop.
- 🛠️ **[docs/WORKFLOW.md](docs/WORKFLOW.md)** — **Hướng dẫn Vận hành, Cấu hình Phần cứng và Kiến trúc Workflow**: Chi tiết cài đặt môi trường, cấu hình phần cứng tối thiểu & khuyến nghị, hướng dẫn render từng shot (`--frames <N>`), xử lý lỗi và bài học kinh nghiệm.
- 📦 **[requirements-gis.txt](requirements-gis.txt)** — Danh sách các thư viện Python xử lý GIS (rasterio, pyproj, shapely, numpy, pillow).

---

## 🚀 Hướng dẫn Chạy Nhanh

Mở PowerShell tại thư mục dự án:

```powershell
Set-Location -LiteralPath 'E:\Source code\ai-history-map-video'

# 1. Cài đặt tự động Blender 4.5.15 LTS và font chữ
python scripts/bootstrap.py

# 2. Chạy bộ kiểm thử tự động (52/52 tests pass)
python -m unittest discover -s tests -v

# 3. Kiểm tra tính toàn vẹn của môi trường
python pipeline.py doctor --engine eevee

# 4. Render kiểm tra 2 Shot đầu tiên (240 frame / 8 giây) bản nháp:
python pipeline.py render --preset draft --frames 240 --engine eevee

# 5. Render Master hoàn chỉnh 30 giây (1080p Full HD, 900 frame):
python pipeline.py render --preset final --engine eevee
```

---

## 🎬 Cấu trúc 5 Shot Điện ảnh Hoàn chỉnh

| Shot | Frame | Thời lượng | Mốc Lịch sử | Góc máy & Nội dung Diễn hoạt |
|---|---|---|---|---|
| **Shot 1** | 1 – 120 | 4.0s | **1010: Định đô Thăng Long** | Toàn cảnh Việt Nam từ không gian → Hạ cánh êm ái thuần Z xuống Thăng Long → Ngước góc 26° lướt tầm thấp qua tường thành Hoàng Thành và ngắm dải Sông Hồng. |
| **Shot 2** | 121 – 240 | 4.0s | **1049: Khởi dựng Chùa Một Cột** | Cận cảnh Chùa Một Cột trên Hồ Sen Linh Chiểu → Camera xoay quỹ đạo 80° ghi lại quá trình mọc từng cột đá, giàn đỡ, điện thờ và 4 mái cong. |
| **Shot 3** | 241 – 660 | 14.0s | **Thăng Long 36 Phố Phường** | Bay lướt tầm trung dọc trục sông Tô Lịch và Sông Hồng, 2.400 căn nhà phố cổ tăng dần mật độ theo các thế kỷ. |
| **Shot 4** | 661 – 780 | 4.0s | **1812: Xây dựng Cột Cờ Hà Nội** | Cú xoay máy ngước tầm thấp quanh 3 tầng chân đế đá, thân tháp gạch bát giác vươn cao đón ngọn cờ. |
| **Shot 5** | 781 – 900 | 4.0s | **1900: Toàn cảnh Di sản ngàn năm** | Kéo lùi máy quay ra xa và lên cao, thu trọn vẹn toàn bộ Hoàng Thành, Phố Cổ và dòng Sông Hồng trải dài ra đường chân trời đón ánh ban mai. |
