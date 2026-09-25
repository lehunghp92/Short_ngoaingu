# Chiến lược 3 kênh học ngoại ngữ (Anh / Trung / Hàn)

## 1. Nhận diện kênh
| | Kênh 1 | Kênh 2 | Kênh 3 |
|---|---|---|---|
| Tên | Học Tiếng Anh cùng Bơ | Học Tiếng Trung cùng Bơ | Học Tiếng Hàn cùng Bơ |
| Tên tài khoản | @HocTiengAnhCungBo | @HocTiengTrungCungBo | @HocTiengHanCungBo |
| Giọng bản ngữ | Piper `en-lessac` | Piper `zh-huayan` | Piper `ko-kss` |
| Phiên âm | IPA | Pinyin có dấu thanh | Romaja |

Dùng chung nhân vật dẫn chuyện **Bơ** và bạn diễn **Mai**. Người xem kênh này dễ sang xem kênh kia vì nhận ra nhân vật.
Hãy đăng ký tên tài khoản giống nhau trên TikTok, YouTube, Instagram và Facebook ngay từ đầu.

## 2. Cấu trúc một video (20–40 giây)
`hook → câu SAI ✗ → câu ĐÚNG ✓ (đọc 2 lần: thường, chậm) → giải thích → [từ vựng | hội thoại | quiz đếm ngược] → kết "lưu lại để ôn"`

Mỗi thẻ học có 3 tầng: **chữ ngoại ngữ** (to nhất, phát sáng khi giọng bản ngữ đang đọc), **phiên âm**, **nghĩa tiếng Việt**.
Thẻ được thiết kế để người xem chụp màn hình lưu lại.

## 3. Lịch nội dung 30 ngày (mỗi kênh 1 video/ngày, cùng chủ đề cho cả 3 kênh)
| Tuần | Series (mỗi series ~7 tập) | Ví dụ tập |
|---|---|---|
| 1 | **Đi cà phê / nhà hàng** | gọi món · mang đi · hỏi giá · thanh toán · khen món ăn |
| 2 | **Đừng nói X, hãy nói Y** | "I'm fine", "Give me", các câu nghe cộc lốc hoặc sai sắc thái |
| 3 | **Du lịch** | hỏi đường · sân bay · khách sạn · taxi · mua sắm · mặc cả |
| 4 | **Công sở & phỏng vấn** + quiz tổng kết | giới thiệu bản thân · email · họp · xin nghỉ |

Mỗi tuần nên có thêm 1 video **"so sánh 3 ngôn ngữ"** (ví dụ "Cảm ơn nói thế nào trong Anh / Trung / Hàn"), đăng lên cả 3 kênh để kéo người xem giữa các kênh.

## 4. Quy trình mỗi ngày (khoảng 30–45 phút cho cả 3 kênh)
1. Tab **🌏 Bài học ngoại ngữ**: nhập chủ đề → **Sinh 3 bài** (Ollama), hoặc tự viết JSON theo `examples/lessons/`.
2. **Kiểm tra từng câu** bằng từ điển hoặc nhờ người bản ngữ. Đây là bước bắt buộc, vì một video sai sẽ làm mất uy tín kênh.
3. **Dựng video cho cả 3 kênh.** Mở từng video nghe lại giọng bản ngữ; nếu phát âm máy chưa tốt, sửa câu hoặc bỏ câu đó.
4. Đăng video trong thư mục `export/`, copy tiêu đề và mô tả từ các file `.txt`. Nên đăng vào khung 11h–13h hoặc 19h–22h.
5. Ghi lại số liệu mỗi tuần: **tỷ lệ xem hết, lượt lưu, lượt chia sẻ** → làm tiếp series nào có nhiều lượt lưu nhất.

## 5. Tăng view và kiếm tiền
- Hook dùng cảm giác "sợ sai": "90% người Việt nói sai…", "Đừng bao giờ nói… với người Hàn".
- Cuối video luôn kêu gọi **lưu lại**, hoặc đặt câu hỏi cho phần bình luận ("Comment câu bạn muốn học").
- Trả lời bình luận bằng video mới, vì đây là nguồn chủ đề miễn phí.
- Sau khoảng 3 tháng: bán **bộ flashcard PDF** theo series, khoá học ngắn, hoặc affiliate app học ngoại ngữ.

## 6. Lưu ý chất lượng
- Giọng Piper chạy offline, miễn phí nhưng chưa hoàn hảo, nhất là thanh điệu tiếng Trung. Khi kênh có thu nhập, nên
  **thu âm giọng người thật** cho câu mẫu: đặt file WAV vào thư mục `projects/<video>/audio/` thay thế, hoặc mở rộng app.
- Không dùng cảnh phim hoặc nhạc có bản quyền. Chỉ trích dẫn **chữ** của câu thoại.

## 7. Phong cách dạy học (chọn khi tạo kịch bản)
| Phong cách | Mã `style` | Dùng khi | Nhân vật mặc định |
|---|---|---|---|
| 💬 Hỏi – Giảng (Bơ hỏi, Mai giảng) | `hoi_thoai` | Mặc định, hợp mọi chủ đề giao tiếp | bo & mai |
| 🎭 Nhập vai tình huống | `nhap_vai` | Tình huống thực tế: mua sắm, nhà hàng, sân bay, bệnh viện | du_khach & co_tap_hoa |
| ❌ Top 3 lỗi sai người Việt hay mắc | `top_sai` | Tăng tương tác, bình luận tranh luận | bo & co_giao |
| 🏆 Game show đố vui | `do_vui` | Ôn tập, tăng xem lại (rewatch) | mai & bo |
| ⚡ 5 từ vựng tốc độ | `tu_vung_nhanh` | Từ vựng theo chủ đề, lượt lưu cao | ban_gym & bo |
| 🎤 Luyện nói theo (shadowing) | `noi_theo` | Phát âm, phản xạ nói | co_giao & bo |
| 📖 Truyện chêm | `ke_chuyen` | Giải trí + nhớ từ theo ngữ cảnh | bo & ong_chu |
| 🧑‍🏫 Giảng 1 người (sai/đúng + quiz) | `giang` | Nhanh gọn, dễ sản xuất | bo & — |

- Tất cả phong cách dùng chung một định dạng kịch bản `turns`, nên có thể đổi phong cách và nhân vật tự do. Người dẫn `N` chỉ có giọng, không xuất hiện trên màn hình.
- Mỗi phong cách có một bài mẫu trong `examples/lessons/styles/`.
- Nên xoay vòng các phong cách trong tuần, ví dụ: T2 Hỏi–Giảng · T3 Nhập vai · T4 Top 3 lỗi sai · T5 Từ vựng tốc độ · T6 Đố vui · T7 Luyện nói theo · CN Truyện chêm.
