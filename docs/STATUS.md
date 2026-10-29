# Báo cáo Tiến độ, Những gì chưa làm tốt và Giải pháp Điện ảnh Mới

**Cập nhật: 30/10/2026 — Asia/Bangkok.**  
Tài liệu phân tích chuyên sâu về hiện trạng kỹ thuật, mổ xẻ nguyên nhân gốc rễ các điểm chưa làm tốt và đặc tả toàn diện giải pháp điện ảnh mới cho video 3D Timelapse lịch sử Thăng Long — Hà Nội.

---

## 1. Mục tiêu và Định hướng Đổi mới

Dự án xây dựng pipeline tự động hóa bằng **Python + Blender Headless + FFmpeg** nhằm sản xuất video lịch sử 3D dài **30 giây, 1920×1080 (Full HD), 30 fps (900 frames)** tái hiện tiến trình phát triển của **Thăng Long — Hà Nội từ năm 1010 đến 1900**.

### Bước chuyển mình từ phản hồi của người dùng
Sau khi tiếp nhận video tham chiếu phong cách phim tài liệu 3D quốc tế ([JERUSALEM - 3D Timelapse](https://youtu.be/GagpWco3FPM)), dự án đã chính thức thay đổi triết lý thiết kế:
1. **Không dàn trải thời gian qua từng năm một cách vô nghĩa**: Thay vì để bộ đếm năm nhảy số đơn điệu và mô hình mọc ngẫu nhiên không có điểm nhấn, video tập trung sâu vào **các mốc lịch sử trọng đại (Milestone-focused Eras)**.
2. **Áp dụng ngôn ngữ điện ảnh (Cinematic Language)**:
   - Camera bay lượn tầm thấp sống động (Drone Swoop, Orbit, Low-angle Flyover, Panoramic Pull-back) thay cho góc nhìn sa bàn tĩnh từ trên cao.
   - Chiếu sáng mặt trời tự nhiên theo mô hình vật lý Nishita Sky với góc chiếu xiên thấp (26°), tạo bóng đổ dài làm nổi bật từng đường nét kiến trúc cổ truyền.
   - Thêm hệ thống tường thành Hoàng Thành Thăng Long và các chòi canh mái ngói đá bao bọc khu trung tâm hoàng cung.
3. **Giữ vững độ chính xác GIS tuyệt đối**: Toàn bộ công trình (Chùa Một Cột 1049, Cột Cờ Hà Nội 1812, 2.400 căn nhà phố cổ) và sông ngòi, địa hình đều được neo cố định theo hệ tọa độ mét metric chuẩn UTM EPSG:32648 và mô hình cao độ số Copernicus DSM 30m.

---

## 2. Bảng đối chiếu tổng hợp: Điểm đã làm tốt vs Những gì chưa làm tốt

| Hạng mục | Điểm đã làm tốt (Đã đạt được & Kiểm chứng) | Những gì chưa làm tốt (Hạn chế & Cần khắc phục) |
|---|---|---|
| **Pipeline & Môi trường** | - Hoàn toàn tự động hóa, headless 100%.<br>- 52/52 unit tests pass (100%).<br>- Bộ nhớ RAM cực nhẹ (~200–220 MB).<br>- Tái sử dụng frame thông minh qua hash SHA-256. | - Chưa hỗ trợ resume render nếu tiến trình bị ngắt giữa chừng.<br>- Chưa có cơ chế render proxy tốc độ cao (như bản xem nhanh 360p trong 1–2 phút). |
| **Chuyển động Camera** | - Góc quay đã đa dạng hóa thành 5 shot điện ảnh.<br>- Chùa Một Cột có cú xoay quỹ đạo hero shot.<br>- Cột Cờ Hà Nội có góc ngước ấn tượng. | - **Cú zoom mở đầu từ bản đồ toàn quốc vào Hà Nội bị giật nhiều** (Off-center drift, kinematic jerk spike, hố rỗng địa hình).<br>- Điểm đánh dấu Hà Nội bị chớp tắt giật cục. |
| **Dữ liệu Địa hình & GIS** | - Tích hợp thành công DEM 30m Copernicus thật.<br>- Mạng lưới đường và sông hồ khớp với OSM.<br>- Đã dựng được hồ sen Linh Chiểu dưới chân Chùa Một Cột. | - **Tồn tại "hố rỗng" 30km** giữa patch DEM Hà Nội (4.5km) và bản đồ toàn quốc (Delaunay 35km).<br>- Bước nhảy màu sắc và độ phân giải giữa vector toàn quốc (350m) và DEM Hà Nội (30m) quá gắt. |
| **Mô hình Kiến trúc** | - Chùa Một Cột và Cột Cờ dựng procedural chi tiết, tỷ lệ thật.<br>- Tường thành Hoàng Thành và tháp canh gạch ngói cổ.<br>- 2.400 căn nhà phố cổ sắp xếp không xung đột. | - Nhà phố cổ sinh theo ô đất hiện đại, chưa có bản vẽ khảo cổ chi tiết cho từng thế kỷ.<br>- Vật liệu bề mặt chủ yếu là procedural shader đơn giản, chưa có bản đồ texture chi tiết (PBR texture map). |
| **Ánh sáng & Thẩm mỹ** | - Ánh sáng Nishita Sky đẹp, bóng đổ dài tự nhiên.<br>- Phụ đề ASS phong cách documentary rõ ràng. | - Chưa có hiệu ứng khí quyển theo mùa hoặc sương mù mờ ảo sớm mai (fog/mist pass) để tăng tính hoài niệm lịch sử. |
| **Âm thanh & Hậu kỳ** | - Tích hợp FFmpeg tự động ghép video, phụ đề và kiểm tra chuẩn kỹ thuật `yuv420p`. | - Mặc định video xuất ra chưa có âm thanh nếu người dùng không cung cấp file nhạc nền và SFX từ bên ngoài. |

---

## 3. Những gì chưa làm tốt: Phân tích Chuyên sâu và Nguyên nhân Gốc rễ

Dưới đây là mổ xẻ chi tiết 6 vấn đề kỹ thuật lớn đã được nhận diện qua các đợt render thử nghiệm:

### 🔴 Vấn đề 1: Cú zoom bản đồ từ vệ tinh xuống Hà Nội bị giật và chóng mặt (Kinematic Jerk & Multi-axis Drift)
- **Hiện tượng thực tế:** Trong bản render 2 shot mẫu (`output/20261030_005718_render_5736c0/final_video.mp4`), khi camera bắt đầu lao từ không gian xuống mặt đất, người xem cảm thấy hình ảnh bị rung lắc, khung hình giật cục, mục tiêu Hà Nội bị trôi dạt khắp nơi trước khi "phanh gấp" một cách gượng gạo.
- **Nguyên nhân gốc rễ 1 — Trôi dạt tâm ngắm 4 trục cùng lúc:**
  Camera ban đầu lấy tâm toàn quốc là miền Trung (`y = -56.000`, ngang vĩ độ Đà Nẵng). Khi zoom xuống Hà Nội (`y = 15`), thuật toán cũ dịch chuyển đồng thời 4 trục phi tuyến tính trong vỏn vẹn 1.5 giây:
  1. Trục Y trượt 560 km lên phía Bắc.
  2. Trục Z rơi tự do từ 450.000m xuống 300m.
  3. Góc Azimuth xoay từ 0° sang -15°.
  4. Góc Elevation nghiêng từ 88° xuống 65°.
  Việc di chuyển 4 trục tự do cùng lúc làm điểm đích Hà Nội chạy zigzag trên màn hình, khiến mắt người xem không có điểm tựa thị giác.
- **Nguyên nhân gốc rễ 2 — Cú sốc gia tốc giật (Kinematic Jerk Spike):**
  Thuật toán cũ sử dụng hàm `math.exp()` trên khoảng zoom 1.500 lần dồn vào 46 frame (~18% tỷ lệ mỗi frame). Đến frame 70, camera đột ngột chuyển sang hàm tuyến tính `lerp()` để lướt Hoàng Thành. Sự gián đoạn ở đạo hàm cấp 2 ($\frac{d^2 x}{dt^2}$) tạo ra một đỉnh gia tốc giật cực đại, khiến camera như va phải một bức tường vô hình rồi mới bò tiếp.

### 🔴 Vấn đề 2: "Hố rỗng địa hình" 30 km giữa không trung (The 30-km Terrain Chasm)
- **Hiện tượng thực tế:** Ở đoạn giữa của cú zoom (cao độ khoảng 2.000m – 10.000m), toàn bộ cảnh quan mặt đất biến mất, thay vào đó là một khoảng trống màu xanh lơ phẳng lì như camera bị lỗi render hoặc rơi xuống biển.
- **Nguyên nhân gốc rễ:** Trong `scripts/fetch_gis.py`, bản đồ toàn quốc bị khoét một lỗ chữ nhật đúng bằng kích thước patch Hà Nội:
  ```python
  country = country.difference(box(*meta['bounds_projected_m']))
  ```
  Sau đó, hàm phân rã tam giác (triangulation) nối các đỉnh bao quanh lỗ khoét tạo ra các cạnh tam giác dài **20 km đến 35 km**. Trong khi đó, patch DEM chi tiết của Hà Nội chỉ có kích thước **4.5 km**.
  Khoảng cách từ mép 2.2 km của Hà Nội ra mép 30 km của lưới quốc gia hoàn toàn không có lưới đa giác mặt đất. Khi camera hạ xuống cao độ trung bình, nó nhìn xuyên qua lỗ thủng xuống đối tượng `Regional_sea` (mặt biển màu teal), gây ra hiện tượng mất trắng hình ảnh trước khi patch Hà Nội đột ngột hiện ra.

### 🔴 Vấn đề 3: Xung đột độ phân giải lưới và màu sắc vật liệu (LOD & Material Discontinuity)
- **Hiện tượng thực tế:** Khi camera tiếp cận gần mặt đất, các mảng đa giác góc cạnh sắc lẹm nhấp nháy lướt qua màn hình, sau đó chuyển màu đột ngột sang thảm cỏ xanh của Hà Nội.
- **Nguyên nhân gốc rễ:** 
  - Bản đồ toàn quốc dùng vector đơn giản hóa thô (độ phân giải cạnh ~350m) với thuộc tính màu đỉnh (vertex color) tông màu ô-liu sẫm `[0.18, 0.34, 0.15]`.
  - Địa hình Copernicus Hà Nội dùng lưới cao độ 30m với vật liệu Principled BSDF màu cỏ non `[0.40, 0.42, 0.29]`.
  - Sự thiếu hụt một lớp lưới đệm chuyển tiếp (Level of Detail - LOD transition buffer) khiến ranh giới giữa hai mô hình trở thành một vết cắt thô bạo.

### 🔴 Vấn đề 4: Điểm đánh dấu vị trí (Locator Marker) chớp tắt nhị phân
- **Hiện tượng thực tế:** Vòng tròn định vị ánh kim chỉ vị trí Thăng Long xuất hiện rồi biến mất đánh "bụp" một cái.
- **Nguyên nhân gốc rễ:** Đối tượng `Hanoi_locator` có đường kính 9.000m được lập trình ẩn đi bằng cờ nhị phân `hide_render = True` ở frame 65 thay vì thu nhỏ dần kích thước hoặc làm mờ độ trong suốt (alpha fade).

### 🔴 Vấn đề 5: Hạn chế về tính xác thực khảo cổ học của mạng lưới nhà phố
- **Hiện tượng thực tế:** Dù 2.400 căn nhà phố cổ tạo nên khung cảnh đô thị sầm uất, cách bố trí nhà mang tính xấp xỉ hình thái học hơn là phục dựng chính xác từng ngôi nhà theo lịch sử.
- **Nguyên nhân gốc rễ:** 
  - Dữ liệu ranh giới đất và đường phố lấy từ OpenStreetMap thời điểm hiện đại. Các triều đại Lý, Trần, Lê có cấu trúc phường hội, thành quách và kênh rạch khác biệt lớn so với hiện nay (ví dụ: sông Tô Lịch xưa thông với sông Hồng, hồ Hoàn Kiếm thời Lê rất rộng lớn gồm cả hồ Tả Vọng và Hữu Vọng).
  - Do hạn chế về tư liệu bản đồ khảo cổ học số hóa của Việt Nam trước thế kỷ 19, hệ thống buộc phải dùng giải pháp **phát sinh thủ tục có định hướng (Procedural Generation with GIS Constraints)**. Nhà mọc theo mật độ tăng dần theo timeline để biểu đạt sự thịnh vượng kinh tế thay vì định danh chính xác từng hộ dân lịch sử.

### 🔴 Vấn đề 6: Nút thắt hiệu năng render trên phần cứng phổ thông
- **Hiện tượng thực tế:** Thời gian kết xuất một khung hình 1080p trên đồ họa tích hợp iGPU Intel UHD 630 dao động từ **4.2s đến 5.0s/frame**. Tổng thời gian render đủ 900 frame (30 giây video) mất khoảng **35 đến 40 phút**.
- **Nguyên nhân gốc rễ:** EEVEE Next trong Blender 4.5 đòi hỏi tính toán đổ bóng mặt trời tự nhiên (Sun shadow maps 4096), lọc bóng mềm, và xử lý tán xạ bầu trời trên 480.000 đa giác. Khi không có GPU rời (NVIDIA/AMD), việc giả lập tính toán đồ họa qua luồng CPU/iGPU đạt đến giới hạn phần cứng.

---

## 4. Đặc tả Kiến trúc Giải pháp Điện ảnh Mới

Nhằm giải quyết triệt để các tồn tại trên, đưa chất lượng video tiệm cận các tác phẩm phim tài liệu lịch sử 3D quốc tế, dự án triển khai bộ giải pháp kỹ thuật mới:

```
[Camera Vệ tinh Không gian]
       │
       ▼  Hạ độ cao thuần Z (Pure-Z Descent) — Tâm ngắm khóa chặt Thăng Long (-80, 15, 0)
[Đường cong Logarit Smootherstep bậc 5 — Triệt tiêu 100% rung lắc và giật gia tốc]
       │
       ▼  Vùng đệm đồng bằng 60km (Seamless Buffer Plain) xóa bỏ hoàn toàn hố rỗng 30km
[Marker định vị thu nhỏ mượt mà Scale (1,1,1) -> (0,0,0) như ánh sáng tiếp đất]
       │
       ▼  Tiếp cận tầm thấp nóc thành (Cao độ 150m)
[Kỹ thuật "Hạ cánh rồi mới ngước chân trời" (Swoop & Level-out): Tilt từ 88° xuống 26°]
       │
       ▼  Shot 1: 1010 Lướt tầm thấp Hoàng Thành Thăng Long & Sông Hồng
       │
       ▼  Shot 2: 1049 Hero Orbit Chùa Một Cột tọa lạc giữa Hồ Sen Linh Chiểu
       │
       ▼  Shot 3: Thăng Long 36 Phố Phường mở rộng sầm uất dọc sông Tô Lịch
       │
       ▼  Shot 4: 1812 Góc ngước hùng tráng quanh 3 tầng đế đá Cột Cờ Hà Nội
       │
       ▼  Shot 5: 1900 Cú kéo máy Panoramic Pull-back đón bình minh trên toàn cảnh di sản
```

### 1. Khóa cứng tâm ngắm theo trục Z (Locked-Focus Pure-Z Descent)
- **Quy tắc bất biến:** Tâm ngắm của camera (`focus`) được neo cố định ngay tại trung tâm Hoàng Thành Thăng Long (`Vector((-80, 15, 0))`) từ **Frame 1 đến Frame 75**.
- Trong suốt giai đoạn hạ độ cao từ không gian:
  - Góc dốc camera giữ thẳng đứng từ đỉnh đầu xuống: `Elevation = 88.0°`.
  - Hướng nhìn giữ nguyên hướng thẳng về phía Bắc: `Azimuth = 0.0°`.
  - Camera chỉ chuyển động trên một trục duy nhất: **Trục Z (độ cao)**.
- **Hiệu quả thị giác:** Dải đất hình chữ S của Việt Nam nở rộng đều đặn và êm ái ra 4 góc màn hình. Điểm đến Thăng Long luôn nằm bất biến tại hồng tâm thị giác, triệt tiêu hoàn toàn hiện tượng trôi lệch góc nhìn.

### 2. Đường cong biến thiên mượt bậc 5 (Smootherstep Logarithmic Easing)
- Thay vì dùng hàm bậc 3 thông thường ($3t^2 - 2t^3$) có đạo hàm cấp hai khác 0 ở biên, hệ thống áp dụng đa thức bậc 5 của Ken Perlin:
  $$\text{smootherstep}(t) = 6t^5 - 15t^4 + 10t^3$$
- Đa thức này triệt tiêu cả vận tốc lẫn gia tốc ở hai đầu:
  $$\frac{d}{dt}\text{smootherstep}(0) = 0, \quad \frac{d}{dt}\text{smootherstep}(1) = 0$$
  $$\frac{d^2}{dt^2}\text{smootherstep}(0) = 0, \quad \frac{d^2}{dt^2}\text{smootherstep}(1) = 0$$
- Khoảng cách camera được tính trơn tru trên thang logarit:
  $$\ln(D(t)) = \ln(D_{\text{start}}) \cdot (1 - u) + \ln(D_{\text{end}}) \cdot u$$
  với $u = \text{smootherstep}((f - 20) / 55)$.
- **Hiệu quả:** Camera bắt đầu rơi vô cùng dịu dàng, tăng tốc êm ái ở giữa hành trình và hãm phanh mượt mà khi tiếp cận mặt đất, loại bỏ hoàn toàn cú va đập quán tính.

### 3. Kỹ thuật "Hạ cánh rồi mới ngước chân trời" (Swoop & Level-out Dynamics)
- Camera tuyệt đối không nghiêng góc ngắm (tilt) khi còn ở trên cao vì sẽ làm biến dạng phối cảnh mặt đất.
- Chỉ khi camera đã hạ xuống khoảng cách an toàn (~150m trên nóc thành ở Frame 76), camera mới bắt đầu hạ góc dốc từ **88.0° xuống 26.0°** và lướt nhẹ theo phương ngang.
- **Hiệu quả:** Tạo ra cú "reveal" đầy cảm xúc của phim tài liệu: bức tường thành gạch cổ Hoàng Thành, các chòi canh mái ngói đá và dải Sông Hồng dần dần nhô lên trên đường chân trời đón ánh ban mai.

### 4. Lớp địa hình đồng bằng chuyển tiếp vùng đệm (Seamless Buffer Plain)
- Để xóa sổ hoàn toàn "hố rỗng 30km", trong `history_pipeline/geoscene.py` bổ sung đối tượng lưới địa hình `Regional_delta_plain` bao bọc vùng đồng bằng Bắc Bộ bán kính 60 km.
- Đáy chìm dưới mực nước biển được nâng cao lên ngang cao độ phù sa (+2.5m). Ở bất kỳ cao độ nào trong hành trình rơi, camera luôn nhìn thấy mặt đất liền mạch và hệ thống sông ngòi tự nhiên, không bao giờ rơi vào khoảng trống màu xanh rỗng.

### 5. Thu nhỏ mượt mà điểm định vị (Smooth Scale-Down Marker)
- Khối trụ định vị ánh kim Thăng Long không còn dùng lệnh tắt `hide_render`.
- Từ frame 20 đến frame 40, kích thước của marker được nội suy giảm dần từ `Vector((1, 1, 1))` về `Vector((0, 0, 0))`. Điểm đánh dấu thu gọn lại thành một đốm sáng nhỏ dần rồi tan biến tự nhiên vào tâm Hoàng Thành.

### 6. Ánh sáng vật lý Nishita Sky & Mô hình hóa bóng đổ dài
- Sử dụng mô hình bầu trời khí quyển Nishita Sky của EEVEE Next:
  - Độ cao mặt trời (Sun Elevation): **26.0°** (góc xiên đầu buổi sáng).
  - Góc xoay mặt trời (Sun Rotation): **135.0°** (hướng Đông Nam).
  - Năng lượng chiếu sáng: **4.8**.
  - Màu sắc ánh nắng: Tông vàng ấm cổ kính `(1.0, 0.92, 0.78)`.
- **Hiệu quả:** Tạo ra các vệt bóng đổ dài sắc nét của Chùa Một Cột, Cột Cờ Hà Nội và hệ thống tường thành, mang lại cảm giác hoành tráng, trầm mặc và chân thực như phim điện ảnh.

### 7. Phụ đề điện ảnh ASS (Documentary Typography)
- Nâng cấp tệp phụ đề `overlay.ass`:
  - Tiêu đề thương hiệu documentary: `THĂNG LONG — HÀ NỘI` (Font Be Vietnam Pro Bold, viền xám đen sang trọng).
  - Mốc năm hiển thị cỡ lớn (**Font size 76pt**) đặt ở góc trái màn hình, đổi màu vàng hoàng kim tại các mốc trọng đại.
  - Phần diễn giải sự kiện lịch sử súc tích, hiển thị đồng bộ chính xác từng frame.

---

## 5. Bảng Thông số 5 Shot Điện ảnh Hoàn chỉnh (30 Giây / 900 Frames)

| Shot | Khoảng Frame | Thời lượng | Mốc Năm | Quỹ đạo Camera | Độ cao / Cự ly | Góc dốc (Elev) & Hướng (Azim) | Nội dung Diễn hoạt & Thẩm mỹ |
|---|---|---|---|---|---|---|---|
| **Shot 1** | 1 – 120 | 4.0s | **1010** | Pure-Z Descent → Level-out Glide | 320.000m → 145m | 88° → 26°<br>Azim: 0° → -10° | Toàn cảnh Việt Nam từ không gian → Hạ cánh êm ái xuống Thăng Long → Ngước góc 26° lướt tầm thấp dọc tường thành Hoàng Thành và ngắm dải Sông Hồng. |
| **Shot 2** | 121 – 240 | 4.0s | **1049** | Hero Landmark Orbit | Cự ly: 5.4m | 21° – 25°<br>Azim: -45° → +35° | Cắt cảnh điện ảnh sang Chùa Một Cột tọa lạc giữa Hồ Sen Linh Chiểu có viền đá → Camera xoay quỹ đạo 80° ghi lại quá trình mọc từng cột đá, giàn đỡ, điện thờ và 4 mái cong. |
| **Shot 3** | 241 – 660 | 14.0s | **1100–1800** | Continuous Flyover | Cự ly: 155m | 28° – 25°<br>Azim: -20° → +15° | Bay lướt tầm trung dọc trục sông Tô Lịch và Sông Hồng, 2.400 căn nhà phố cổ tăng dần mật độ đại diện cho sự phồn hoa của Thăng Long 36 Phố Phường. |
| **Shot 4** | 661 – 780 | 4.0s | **1812** | Dramatic Upward Orbit | Cự ly: 20m | 20° – 25°<br>Azim: -35° → +35° | Cận cảnh Cột Cờ Hà Nội; camera ngước tầm thấp xoay quanh 3 tầng chân đế đá, thân tháp gạch bát giác vươn cao đón ngọn cờ tổ quốc. |
| **Shot 5** | 781 – 900 | 4.0s | **1900** | Panoramic Pull-back | Cự ly: 18m → 165m | 23° → 27°<br>Azim: 35° → -15° | Kéo lùi máy quay ra xa và lên cao, thu trọn vẹn toàn bộ Hoàng Thành, Phố Cổ và dòng Sông Hồng trải dài ra đường chân trời rực rỡ nắng mai. |

---

## 6. Kế hoạch Hành động & Tiêu chí Nghiệm thu

1. **Triển khai mã nguồn:**
   - Cập nhật hàm `animate_camera()` và `overview()` trong `history_pipeline/geoscene.py` theo đúng công thức Locked-Focus Pure-Z Smootherstep và thu nhỏ scale marker.
   - Bổ sung lưới đệm đồng bằng `Regional_delta_plain` vào `geoscene.py`.
2. **Kiểm tra tự động:**
   - Chạy `python -m unittest discover -s tests -v` để đảm bảo 100% 52/52 tests tiếp tục vượt qua.
3. **Kết xuất bản kiểm tra Shot 1 & Shot 2 mới:**
   - Chạy lệnh `python pipeline.py render --preset draft --frames 240 --engine eevee` để xuất clip 8 giây kiểm chứng độ mượt mà của hiệu ứng zoom mới.
4. **Kết xuất bản Master 1080p hoàn chỉnh:**
   - Sau khi người dùng xác nhận cú zoom đã êm mượt tự nhiên, tiến hành render đầy đủ 900 frame ở chuẩn Full HD 1080p.
