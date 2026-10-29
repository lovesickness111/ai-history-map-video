# Hướng dẫn Cài đặt, Vận hành và Kiến trúc Workflow

**Cập nhật: 30/10/2026 — Asia/Bangkok.**  
Tài liệu hướng dẫn chi tiết quy trình vận hành pipeline, cấu hình phần cứng, đặc tả kiến trúc camera điện ảnh và phân tích kỹ thuật các điểm chưa làm tốt cần lưu ý. Đọc song song với [STATUS.md](STATUS.md) để theo dõi tiến độ và các bằng chứng kiểm chứng.

---

## 1. Hai chế độ của dự án

| Chế độ | Timeline | Mục đích / Trạng thái |
|---|---|---|
| **Minh họa (Illustrative)** | `data/hanoi_illustrative_timeline.json` | 480 nhà, cây cối, ruộng đồng và 2 công trình ở vị trí giả lập. Dùng để kiểm tra nhanh mỹ thuật procedural và logic animation. |
| **GIS Điện ảnh (Cinematic GIS)** | `data/hanoi_timeline.json` | **Chế độ mục tiêu chính**: Bản đồ toàn quốc Việt Nam → Cú lướt vệ tinh thuần Z vào Thăng Long, DEM 30m Copernicus, 2.400 căn nhà phố, hệ thống tường thành Hoàng Thành Thăng Long, Chùa Một Cột trên hồ sen Linh Chiểu, Cột Cờ Hà Nội theo tọa độ thực UTM EPSG:32648. |

> [!IMPORTANT]
> Khi chạy các lệnh kiểm tra minh họa, bắt buộc truyền cờ `--timeline data/hanoi_illustrative_timeline.json`. Nếu không truyền cờ `--timeline`, pipeline mặc định sử dụng chế độ **GIS Điện ảnh**.

---

## 2. Công cụ và Thư viện Cần thiết

### Công cụ hệ thống

| Thành phần | Yêu cầu tối thiểu | Phiên bản đã kiểm chứng | Ghi chú vận hành |
|---|---|---|---|
| **Python host** | Python 3.11+ | 3.11.9 64-bit | Điều phối pipeline, xử lý dữ liệu và kiểm thử tự động. |
| **Blender** | Nhánh 4.5 LTS | 4.5.15 portable | Chạy ở chế độ Headless (`tools/blender-4.5.15-windows-x64/blender.exe`). |
| **FFmpeg + ffprobe** | Hỗ trợ `ass`, `libx264`, `aac` | 9.0.2-full_build | Nằm trong PATH hệ thống; dùng để ghép chuỗi frame PNG, phụ đề và âm thanh. |
| **PowerShell** | PowerShell 5.1 / 7+ | Windows PowerShell | Chạy lệnh điều khiển và script tự động. |
| **Phông chữ** | Be Vietnam Pro Bold | Google Fonts OFL | Lưu trữ trong `assets/fonts/` phục vụ phụ đề ASS documentary. |

### Cấu hình Phần cứng Khuyến nghị (Hardware Specifications)

Pipeline được tối ưu hóa chuyên sâu theo kiến trúc headless (batching hình học gom 2.400 căn nhà thành một mesh duy nhất, chia sẻ vật liệu procedural, không dùng texture ảnh nặng, nhận diện hash SHA-256 để tái sử dụng khung hình không đổi).

Dưới đây là các mức cấu hình phần cứng dựa trên kết quả đo kiểm thực tế khi render Full HD 1080p (900 frames / 30fps):

| Thành phần | Cấu hình tối thiểu (Chạy được) | Cấu hình khuyến nghị (Tiêu chuẩn) | Cấu hình hiệu năng cao (Render nhanh) | Số liệu đo thực tế trên scene 2.400 nhà + GIS |
|---|---|---|---|---|
| **CPU** | 4 nhân / 4 luồng (i3 đời 8+ hoặc Ryzen 3) | 6–8 nhân (Core i5 đời 11+ hoặc Ryzen 5 5600) | 8–16 nhân (Core i7/i9 hoặc Ryzen 7/9) | Intel Core i3-8100 (4C/4T @ 3.60 GHz), chạy 4 threads |
| **GPU** | iGPU Intel UHD 630 / AMD Radeon Vega | GPU rời GTX 1650 / RTX 3050 (4 GB VRAM) | GPU RTX 3060 / 4060 trở lên (8 GB+ VRAM) | Intel UHD Graphics 630 (onboard, không có card rời) |
| **RAM** | 8 GB DDR4 | 16 GB DDR4/DDR5 | 32 GB DDR4/DDR5 | Sử dụng thực tế chỉ **~200 – 220 MB RAM** trong Blender |
| **Ổ cứng** | 10 GB trống (HDD/SATA SSD) | 20 GB trống (NVMe SSD) | 50 GB+ trống (NVMe PCIe 4.0) | Chuỗi 900 PNG 1080p chiếm ~1.2 GB, MP4 chiếm ~11.3 MB |
| **Tốc độ render** | ~4.2 – 5.0 s / frame 1080p | ~0.8 – 1.5 s / frame 1080p | < 0.3 – 0.5 s / frame 1080p | ~4.5 s / frame trên iGPU UHD 630 |
| **Tổng thời gian render 30s** | ~25 – 40 phút (nhờ cache frame) | ~6 – 10 phút | ~2 – 3 phút | Thực tế: ~35 phút cho 900 frame (319 frame render, 581 frame reuse) |

> [!NOTE]
> **Về bộ nhớ RAM:** Mặc dù máy tính nên có tối thiểu 8 GB RAM để vận hành hệ điều hành và các tác vụ nền, bản thân tiến trình Blender headless xử lý toàn bộ 2.400 căn nhà, 480.000 tam giác và địa hình GIS chỉ ngốn khoảng **220 MB RAM**. Không bao giờ xảy ra hiện tượng tràn bộ nhớ hay Out-Of-Memory (OOM).

> [!TIP]
> **Tối ưu hóa GPU rời:** Khi chạy trên máy có GPU rời NVIDIA/AMD, EEVEE Next sẽ tự động tận dụng nhân tính toán phần cứng để render thời gian thực, rút ngắn thời gian xuất video 30 giây xuống chỉ còn vài phút.

---

## 3. Cài đặt Môi trường Nhanh (Bootstrap)

Mở PowerShell tại thư mục gốc của dự án:

```powershell
Set-Location -LiteralPath 'E:\Source code\ai-history-map-video'
python --version
Get-Command ffmpeg, ffprobe
python scripts/bootstrap.py
```

- `bootstrap.py` tự động tải Blender 4.5.15 LTS Windows x64 từ server chính thức của Blender Foundation, kiểm tra mã băm SHA-256, giải nén vào `tools/`, đồng thời tải font Be Vietnam Pro từ Google Fonts.
- **Python host điều phối pipeline**. Mã `import bpy` chạy trực tiếp bên trong Python nhúng của Blender, tuyệt đối không chạy bằng Python host và không cần `pip install bpy`.

### Thư viện Python phục vụ xử lý GIS
Phần trích xuất dữ liệu địa hình (Fetch GIS) sử dụng môi trường ảo độc lập:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-gis.txt
```

| Thư viện | Phiên bản | Vai trò kỹ thuật |
|---|---|---|
| **rasterio** | 1.4.4 | Đọc COG (Cloud Optimized GeoTIFF) qua HTTP Range, crop và reproject độ cao |
| **pyproj** | 3.7.2 | Chuyển đổi tọa độ trắc địa WGS84 (EPSG:4326) ↔ UTM 48N (EPSG:32648) |
| **numpy** | 2.4.6 | Thao tác mảng cao độ số, nội suy ma trận điểm và mã hóa 16-bit |
| **pillow** | 13.0.0 | Xuất ảnh cao độ PNG 16-bit grayscale kiểm tra |
| **shapely** | 2.2.0 | Xử lý đa giác (Polygon), vùng đệm (buffer) và phân rã tam giác (triangulation) |

---

## 4. Kiến trúc Workflow GIS Điện ảnh (Cinematic GIS Workflow)

### Cấu hình Tọa độ & Không gian 3D
Tệp cấu hình `data/hanoi_gis.json` định nghĩa ranh giới địa lý (Bounding Box) theo thứ tự `[west, south, east, north]`:
`[105.827, 21.018, 105.870, 21.047]` trong hệ quy chiếu **UTM Zone 48N (EPSG:32648)** với tỷ lệ chuẩn hóa **10m = 1 đơn vị Blender (Blender Unit)**.

Dữ liệu bundle hoàn chỉnh tại `data/gis/hanoi/` bao gồm:
1. **DEM cao độ số 30m** trích xuất từ dữ liệu vệ tinh Copernicus DSM.
2. **Mạng lưới mặt nước và đường phố** trích xuất từ OpenStreetMap.
3. **2.400 căn nhà phố cổ** được bố trí tự động dọc theo các trục đường và đê sông, không chồng lấn mặt nước.
4. **Lưới địa hình toàn quốc Việt Nam** phục vụ phân cảnh zoom mở đầu từ không gian.
5. **Hệ thống Hoàng Thành Thăng Long** gồm 4 bức tường thành đá gạch và các chòi canh tháp góc mái ngói cổ.
6. **Hồ sen Linh Chiểu (Pagoda Lotus Pond)** viền đá bao bọc dưới chân Chùa Một Cột.

---

### Hệ thống 5 Shot Điện ảnh Hoàn chỉnh (30 Giây / 900 Frames)

Lấy cảm hứng từ cấu trúc dựng phim tài liệu 3D quốc tế, video 30 giây được phân rã thành 5 Shot điện ảnh tương ứng với các thời kỳ trọng đại:

```
[Bản đồ Toàn quốc] ──Shot 1 (1–120)──> [Lướt tầm thấp Hoàng Thành & Sông Hồng (1010)]
                                                         │
                                               Shot 2 (121–240) [Hero Orbit Chùa Một Cột (1049)]
                                                         │
                                               Shot 3 (241–660) [Flyover 36 Phố Phường (1100–1800)]
                                                         │
                                               Shot 4 (661–780) [Góc ngước Cột Cờ Hà Nội (1812)]
                                                         │
                                               Shot 5 (781–900) [Toàn cảnh Di sản ngàn năm (1900)]
```

1. **Shot 1 (Frame 1–120 / 4s) — 1010 Định Đô Thăng Long:**
   - Bắt đầu từ không gian nhìn toàn cảnh bản đồ Việt Nam.
   - Thực hiện cú rơi vệ tinh thuần Z (Pure-Z Descent) hạ cánh chính xác xuống Thăng Long.
   - Khi tiếp cận độ cao 150m, camera ngước góc 26° lướt tầm thấp qua tường thành Hoàng Thành và dải Sông Hồng.
2. **Shot 2 (Frame 121–240 / 4s) — 1049 Khởi dựng Chùa Một Cột:**
   - Cắt cảnh sang góc cận kiến trúc (Hero Landmark Orbit).
   - Camera xoay quỹ đạo 80° với góc dốc 21°–25°, ghi lại quá trình vươn cao của cột đá, giàn đỡ hoa sen, điện Liên Hoa Đài và 4 mái đao cong trên mặt nước hồ sen Linh Chiểu.
3. **Shot 3 (Frame 241–660 / 14s) — Thăng Long 36 Phố Phường:**
   - Bay lướt tầm trung (Mid-altitude Flyover) dọc theo trục sông Tô Lịch và Sông Hồng.
   - 2.400 căn nhà phố cổ lần lượt mọc lên theo mật độ tăng dần theo các mốc thế kỷ, thể hiện sự phồn vinh của đô thị cổ.
4. **Shot 4 (Frame 661–780 / 4s) — 1812 Cột Cờ Hà Nội:**
   - Cú xoay máy ngước tầm thấp (Upward Orbit) tôn vinh công trình Kỳ Đài gồm 3 tầng chân đế đá vuông, thân tháp gạch bát giác và chòi quan sát vươn cao.
5. **Shot 5 (Frame 781–900 / 4s) — 1900 Toàn cảnh Di sản ngàn năm:**
   - Kéo lùi máy quay (Panoramic Pull-back) lùi xa và lên cao độ 165m, thu trọn vẹn toàn bộ Hoàng Thành, Phố Cổ và dòng Sông Hồng trải dài ra đường chân trời đón ánh ban mai.

---

### Quy trình Render Kiểm tra Từng Shot (Partial Render Workflow)

Để tiết kiệm thời gian phát triển và không phải chờ đợi render toàn bộ 900 frame (mất ~35 phút trên iGPU), pipeline cung cấp tham số `--frames <N>` cho phép render nhanh các shot đầu tiên:

```powershell
# Bước 1: Kiểm tra tính sẵn sàng của môi trường
python pipeline.py doctor --engine eevee

# Bước 2: Render kiểm tra 2 Shot đầu tiên (240 frame / 8 giây) ở bản nháp 720p:
python pipeline.py render --preset draft --frames 240 --engine eevee

# Bước 3: Render kiểm tra 2 Shot đầu tiên ở chuẩn 1080p Full HD:
python pipeline.py render --preset final --frames 240 --engine eevee

# Bước 4: Render toàn bộ 900 frame (30 giây) bản nháp 720p:
python pipeline.py render --preset draft --engine eevee

# Bước 5: Render Master chính thức 1080p Full HD (30 giây / 900 frame hoàn chỉnh):
python pipeline.py render --preset final --engine eevee
```

### Chiếu sáng Bầu trời Nishita & Typography Phụ đề
- **Hệ thống ánh sáng vật lý:** EEVEE Next sử dụng mô hình khí quyển Nishita Sky (độ cao mặt trời 26°, góc xoay 135°, năng lượng 4.8, ánh nắng vàng ấm `(1.0, 0.92, 0.78)`). Mô hình này tạo ra bóng đổ nghiêng dài tự nhiên và đường chân trời dịu mắt, khác biệt hoàn toàn với ánh sáng sa bàn phẳng nhân tạo.
- **Phụ đề điện ảnh:** Phụ đề ASS tự động căn chỉnh lề theo tỷ lệ khung hình với tiêu đề phim `THĂNG LONG — HÀ NỘI`, mốc năm font Be Vietnam Pro Bold cỡ 76pt và diễn giải sự kiện hiển thị đồng bộ theo từng phân đoạn.

---

## 5. Timeline, Cấu trúc Mã và Dữ liệu

| Thành phần | Đường dẫn tệp | Vai trò kỹ thuật |
|---|---|---|
| **Điều phối CLI** | `pipeline.py` | Giao diện dòng lệnh chính (`doctor`, `preview`, `render`), cấu hình preset, validate preflight. |
| **Logic Timeline** | `history_pipeline/timeline.py` | Đọc, xác thực và chuẩn hóa mốc năm, sự kiện và thứ tự hiển thị công trình. |
| **Hình học & Vật liệu** | `history_pipeline/geometry.py` | Tạo mesh cơ bản (box, cylinder), shader vật liệu (gạch, đá, ngói, cỏ, nước, vàng). |
| **Mô hình Kiến trúc** | `history_pipeline/models.py` | Dựng procedural Chùa Một Cột, Cột Cờ Hà Nội, nhà cổ theo tham số kích thước. |
| **Cảnh quan GIS & Camera** | `history_pipeline/geoscene.py` | Dựng địa hình Copernicus, mạng lưới đường phố OSM, Hoàng Thành, hồ sen và **thuật toán điều khiển camera điện ảnh**. |
| **Điểm vào Blender Headless** | `scripts/blender_entry.py` | Script Python chạy bên trong Blender: dựng cảnh, gắn keyframe animation và render frame PNG. |
| **Hậu kỳ FFmpeg & ASS** | `history_pipeline/postprocess.py` | Sinh tệp phụ đề `overlay.ass`, gọi FFmpeg ghép chuỗi ảnh thành video MP4 chuẩn `yuv420p` và kiểm tra `ffprobe`. |
| **Dữ liệu GIS đã chuẩn hóa** | `data/gis/hanoi/scene.json` | Chứa toàn bộ tọa độ metric của địa hình, sông hồ, đường phố và 2.400 căn nhà. |

---

## 6. Phân tích Kỹ thuật: Những gì chưa làm tốt & Bài học Kinh nghiệm

Phần này ghi lại các bài học kỹ thuật quan trọng rút ra từ quá trình phát triển và thử nghiệm:

### 1. Hiện tượng giật zoom và gia tốc giật bậc 2 (Kinematic Jerk Analysis)
- **Vấn đề đã gặp:** Ở bản dựng thử nghiệm ban đầu, cú zoom từ bản đồ Việt Nam vào Hà Nội bị giật mạnh, người xem có cảm giác rung lắc và chóng mặt.
- **Nguyên nhân toán học:**
  - Thuật toán cũ cho camera di chuyển đồng thời 4 trục phi tuyến tính: vừa trượt Y 560 km, vừa rơi Z 450 km, vừa xoay Azimuth -15°, vừa nghiêng Elevation 88°→65° chỉ trong 1.5 giây (46 frame).
  - Độ thu phóng chênh lệch tới 1.500 lần dồn vào thời gian quá ngắn tạo ra biến thiên tỷ lệ ~18%/frame.
  - Sự ngắt quãng giữa hàm mũ `exp()` và hàm tuyến tính `lerp()` ở frame 70 tạo ra xung lực gia tốc giật (Jerk spike), khiến camera bị khựng lại đột ngột.
- **Giải pháp khắc phục:**
  - Áp dụng nguyên tắc **Locked-Focus Pure-Z Descent**: Tâm ngắm khóa chặt tại Thăng Long `Vector((-80, 15, 0))`. Camera giữ nguyên góc nhìn vệ tinh thẳng đứng (Elevation 88°, Azimuth 0°) và chỉ rơi thuần túy theo trục Z.
  - Sử dụng hàm mượt bậc 5 Perlin Smootherstep ($6t^5 - 15t^4 + 10t^3$) trên khoảng cách logarit, triệt tiêu 100% gia tốc ở 2 đầu tiếp xúc.
  - Tách rời hoàn toàn pha hạ độ cao (Descent) và pha ngước góc (Tilt): chỉ khi camera hạ sát cao độ 150m trên nóc thành mới bắt đầu ngước nhìn chân trời.

### 2. Hiện tượng "Hố rỗng địa hình" 30km (Terrain Chasm)
- **Vấn đề đã gặp:** Ở độ cao trung gian (2.000m – 10.000m), toàn bộ cảnh quan biến thành một mảng màu xanh lơ phẳng lì.
- **Nguyên nhân:** Lệnh khoét lỗ bản đồ toàn quốc `country.difference(box)` tạo ra các cạnh tam giác Delaunay dài tới 35 km bao quanh patch Hà Nội (chỉ rộng 4.5 km). Khi camera rơi qua độ cao này, nó nhìn xuyên qua lỗ thủng xuống đối tượng `Regional_sea`.
- **Giải pháp khắc phục:** Bổ sung lớp lưới đệm đồng bằng chuyển tiếp `Regional_delta_plain` bao bọc vùng đồng bằng sông Hồng rộng 60 km $\times$ 60 km với màu sắc và cao độ đồng nhất, bịt kín khoảng trống giữa bản đồ quốc gia và bản đồ thành phố.

### 3. Sự khác biệt giữa Dữ liệu GIS Hiện đại và Khảo cổ học Phong kiến
- **Vấn đề thực tế:** Mạng lưới sông hồ, đường xá và ranh giới ô đất lấy từ OpenStreetMap thời điểm 2024–2026. Trong lịch sử thời Lý–Trần–Lê, hình thái địa lý Hà Nội có nhiều khác biệt lớn (ví dụ: sông Hồng từng đổi dòng nhiều lần, sông Tô Lịch thông nước trực tiếp, đê sông Hồng có hướng tuyến khác).
- **Cách tiếp cận hiện tại:** Do thiếu hụt dữ liệu khảo cổ học số hóa dạng vector theo tọa độ mét cho các thế kỷ 11–18, dự án sử dụng **phương pháp biểu đạt hình thái học (Morphological Approximation)**. 2.400 căn nhà phố cổ được phân bố theo mật độ tăng dần theo trục giao thông thủy bộ để biểu thị sự hưng thịnh của kinh tế đô thị, kết hợp cùng các công trình biểu tượng chuẩn xác (Chùa Một Cột, Cột Cờ, tường thành Hoàng Thành).

### 4. Nút thắt Thời gian Render trên Đồ họa Tích hợp
- **Vấn đề thực tế:** Render 900 frame 1080p trên iGPU Intel UHD 630 mất ~35 phút.
- **Kinh nghiệm vận hành:** Luôn sử dụng cờ `--frames 240` và `--preset draft` để nghiệm thu nhanh bố cục camera và chuyển động trong vòng 5–7 phút trước khi tiến hành xuất bản bản Master 900 frame hoàn chỉnh.

---

## 7. Xử lý Lỗi Thường gặp (Troubleshooting)

| Hiện tượng | Nguyên nhân có thể | Cách khắc phục |
|---|---|---|
| `GIS bundle missing` | Chưa có dữ liệu `data/gis/hanoi/scene.json`. | Chạy script fetch GIS: `.\.venv\Scripts\python.exe scripts/fetch_gis.py`. |
| `ModuleNotFoundError: No module named 'rasterio'` | Chạy fetch GIS bằng Python host thay vì môi trường ảo `.venv`. | Sử dụng đúng interpreter: `.\.venv\Scripts\python.exe`. |
| `ModuleNotFoundError: No module named 'bpy'` | Chạy script Blender bằng Python thông thường. | Dùng lệnh `python pipeline.py render ...`; pipeline sẽ tự khởi chạy Blender portable. |
| `Blender not found` | Chưa chạy bootstrap để tải Blender portable. | Chạy `python scripts/bootstrap.py` hoặc chỉ định đường dẫn qua `--blender`. |
| `Missing FFmpeg filter/encoder` | Bản build FFmpeg thiếu `ass` hoặc `libx264`. | Cài đặt bản FFmpeg đầy đủ (full build) và kiểm tra lại bằng `pipeline.py doctor`. |
| `Camera clipping/nhấp nháy ở xa` | Giá trị `clip_start` hoặc `clip_end` của camera không phù hợp với cự ly vệ tinh. | Kiểm tra hàm `set_camera` trong `geoscene.py`; `clip_end` phải tự co giãn linh hoạt theo `distance * 5`. |
| `Animation verification failed` | Khi render một phần bằng `--frames <N>`, một số công trình có frame khởi công nằm ngoài khoảng render. | Đảm bảo `scripts/blender_entry.py` đã cập nhật logic kiểm tra phù hợp với `frame_end` thực tế. |

---

## 8. Nguồn Dữ liệu & Bản quyền

- Dữ liệu cao độ số toàn cầu: [Copernicus DEM GLO-30 DSM](https://registry.opendata.aws/copernicus-dem/) (Giấy phép công cộng).
- Dữ liệu bản đồ vector: [OpenStreetMap contributors](https://www.openstreetmap.org/copyright) (Giấy phép ODbL).
- Dữ liệu đường biên bản đồ thế giới: [Natural Earth Data](https://www.naturalearthdata.com/) (Public Domain).
- Phông chữ hiển thị: [Be Vietnam Pro](https://fonts.google.com/specimen/Be+Vietnam+Pro) (SIL Open Font License).
