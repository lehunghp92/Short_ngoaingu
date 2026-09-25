# Kỹ thuật The Infographics Show → áp dụng cho Short

TIS là kênh video dài (8–15 phút), nhưng các kỹ thuật cốt lõi chuyển sang short rất tốt. Phần dưới
chỉ ra kỹ thuật nào giữ nguyên, kỹ thuật nào cần nén lại.

## 1. Chủ đề — công thức tiêu đề
| Mẫu TIS | Ví dụ bản short |
|---|---|
| **What if…** / Điều gì xảy ra nếu… | Điều gì xảy ra nếu bạn không ngủ 11 ngày? |
| **… vs …** (so sánh) | Lính La Mã vs Samurai — ai thắng? |
| **Ngày tồi tệ nhất / Kinh khủng nhất…** | Hình phạt kinh khủng nhất lịch sử |
| **Cuộc sống của…** (góc nhìn "bạn") | Một ngày làm phi hành gia |
| **Con số khổng lồ / bí mật** | Vì sao máy bay không bay thẳng qua Thái Bình Dương? |

Tiêu đề **≤ 50 ký tự**, có một "khoảng trống tò mò" mà chỉ xem hết video mới lấp được.

## 2. Kịch bản — 6 nhịp trong 35–55 giây
1. **Hook (0–2s):** câu hỏi hoặc con số gây sốc. Không chào hỏi, không giới thiệu kênh.
2. **Đặt "bạn" vào tình huống:** TIS luôn kể ở ngôi thứ hai, khiến người xem thành nhân vật chính.
3–5. **Leo thang 3 bậc:** mỗi câu một sự kiện tệ hơn hoặc lạ hơn, có **con số cụ thể**.
6. **Twist:** sự thật bất ngờ, khiến người xem muốn chia sẻ.
7. **Kết vòng lặp:** câu cuối nối về câu đầu để nền tảng tự phát lại (tăng thời lượng xem), hoặc một
   câu hỏi kéo người xem bình luận.

Mỗi cảnh = **một câu** 8–16 từ ≈ 2–4 giây. Người xem short rời đi nếu hình đứng yên quá 3 giây.

## 3. Hình ảnh — nhận diện cố định
- TIS dùng **một phong cách duy nhất**: vector 2D phẳng, viền đậm, nhân vật đầu tròn đơn giản, màu tươi.
  Chỉ cần nhìn một khung hình là nhận ra kênh.
  → Trong app, prompt phong cách nằm cố định ở `studio/config.py → Style.image_prompt`. **Đừng đổi giữa
  các video.**
- **Mỗi câu = một hình** minh hoạ đúng nghĩa đen câu đó ("literal visuals").
- **Chữ lớn** cho con số hoặc từ khoá; **phụ đề karaoke**, vì phần lớn người xem short tắt tiếng.
- Chuyển động nhẹ liên tục: zoom chậm (Ken Burns) + hiệu ứng "pop" khi đổi cảnh.

## 4. Âm thanh
- Giọng kể rõ, nhịp hơi nhanh (tốc độ 1.1–1.2), không ngập ngừng.
- Nhạc nền nhỏ (khoảng 10–15% âm lượng giọng), không lời, không bản quyền (YouTube Audio Library,
  Pixabay Music).
- Âm lượng chuẩn -14 LUFS; app tự chuẩn hoá.

## 5. Đa nền tảng
| Nền tảng | Giới hạn thời lượng | Ghi chú |
|---|---|---|
| YouTube Shorts | ≤ 3 phút | Tiêu đề ≤ 100 ký tự, thêm #Shorts |
| TikTok | ≤ 10 phút | Nên để 3–5 hashtag ngách; 3 giây đầu quyết định |
| Instagram Reels | ≤ 3 phút | Ảnh bìa quan trọng khi hiện trên lưới trang cá nhân |
| Facebook Reels | ≤ 90 giây | |

- Đăng cùng một video lên cả 4 nền tảng, nhưng **không để watermark của nền tảng khác** (TikTok/Instagram
  giảm phân phối video có logo đối thủ). App xuất file sạch.
- Đều đặn 1–2 video/ngày trong 60–90 ngày đầu. Theo dõi **tỷ lệ xem hết** và **% người lướt qua
  (swipe-away)**, không chỉ số lượt xem.

## 6. Quy trình làm một video bằng app
1. Chọn chủ đề theo mục 1 → **Sinh kịch bản** (Ollama) hoặc dùng **Khung trống**.
2. **Kiểm tra lại sự thật và con số**: LLM có thể bịa. Sửa từng câu trong bảng.
3. Viết cột `visual` bằng tiếng Anh, cụ thể: ai / đang làm gì / ở đâu.
4. Dựng thử bằng **thẻ đồ hoạ** để duyệt nhịp, rồi dựng bản cuối bằng **Stable Diffusion**.
5. Xem lại ảnh; cảnh nào ảnh xấu thì sửa `visual` rồi dựng lại.
6. Đăng các file trong thư mục `export/`, copy phần mô tả từ các file `.txt`.

## 7. Lưu ý bản quyền và chính sách
- **Không** sao chép hình, nhân vật hay kịch bản của TIS. Chỉ học *kỹ thuật*.
- YouTube yêu cầu **gắn nhãn nội dung tổng hợp** khi nội dung AI trông như thật (người thật, sự kiện
  thật). Hình vector hoạt hình thường không cần nhãn, nhưng giọng AI thì nên ghi chú trong mô tả.
- Kênh chỉ dựng từ mẫu lặp đi lặp lại, ít giá trị riêng, có thể bị từ chối kiếm tiền (chính sách
  "nội dung lặp lại"). Hãy đầu tư vào **nghiên cứu chủ đề và kịch bản** — đó là giá trị thật của kênh.
