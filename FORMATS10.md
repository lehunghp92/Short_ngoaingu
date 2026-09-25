# 10 định dạng dạy ngoại ngữ thu hút nhất

Chọn ở tab **🌏 Kênh học ngoại ngữ** (ô *Định dạng*), hoặc trong kịch bản JSON: `"style": "<mã>"`.
Mọi định dạng dùng chung kịch bản dạng `turns`. Mẫu cho từng định dạng nằm trong `examples/lessons/formats10/`.

| # | Định dạng | Mã `style` | Trường JSON riêng | Mẫu |
|---|---|---|---|---|
| 1 | 🛒 Tình huống đời thường (cảnh + đồ vật + giá) | `giao_tiep` | `background`, `item`, `price` | `giao_tiep/taphoa-muabanh_ko.json` |
| 2 | 📱 Tin nhắn KakaoTalk / WeChat / iMessage | `chat` | `chat_app` (kakao/wechat/imessage), `typing` | `tinnhan-henhcafe_ko.json` |
| 3 | 🏆 Đố vui trắc nghiệm A/B/C | `do_vui` | `options`, `answer`, `picked` (khi trả lời sai), `tag` để ghi điểm | `dovui-abc-dulich_en.json` |
| 4 | ❌ Top lỗi sai – sửa đúng | `top_sai` | `mark: sai/dung` | `styles/congso-top3_en.json` |
| 5 | 🌏 1 câu – 3 ngôn ngữ | `so_sanh_3` | `compare: [{lang, text}] × 3` | `motcau-bangonngu_ko.json` |
| 6 | 🔤 Mổ xẻ chữ | `mo_xe_chu` | `anatomy: {word, parts:[{text,label}], meaning, han_viet, tip}` | `moxechu-bothu_zh.json` |
| 7 | 🎤 Phát âm (thanh điệu / khẩu hình) | `phat_am` | `pron: {title, items:[{text, meaning, mouth, tip}]}` | `phatam-4thanh_zh.json` |
| 8 | 🎬 Câu thoại phim / bài hát | `cau_thoai` | `breakdown: {source, sentence, meaning, words:[{w,m}]}` | `cauthoai-phim_ko.json` |
| 9 | 🎭 Phim bộ nhiều tập | `phim_bo` | cấp bài: `previously`, `next`, `series`, `episode` | `phimbo-lacseoul-tap2_ko.json` |
| 10 | 📅 Thử thách 30 ngày | `thu_thach` | cấp bài: `day` → huy hiệu **NGÀY N/30** | `thuthach-ngay01_ko.json` + tab 📅 |

## Hiệu ứng chung
- **Âm thanh hiệu ứng** tự tạo (không bản quyền): `"sfx": "dung" | "sai" | "tick" | "pop" | "whoosh"`.
  - Câu hỏi quiz tự đếm ngược 3-2-1 có tiếng tích tắc.
  - Khi công bố đáp án, app tự phát tiếng "đúng" hoặc "sai".
  - Mỗi tin nhắn mới trong định dạng chat có tiếng "pop".
- **Chấm điểm:** dùng `tag` của lượt trả lời, ví dụ `"Bơ 2 điểm"`.
- **Khung thoại:** màn phát âm tự vẽ đường thanh điệu tiếng Trung (lấy từ pypinyin). Tiếng Hàn và tiếng Anh dùng khẩu hình: `open`, `round`, `spread`, `closed`, `neutral`.
- **Luật dùng câu thoại có bản quyền:** không chép nguyên lời bài hát hay đoạn phim dài. Chỉ dùng các câu ngắn, thông dụng.

## Video dài (tab 🎬)
- **🎨 Hỗn hợp định dạng.** Mỗi chương gồm:
  1. Bài học theo phong cách riêng của bài;
  2. Đố vui A/B/C;
  3. Phần nghe – nhắc lại;
  4. Ôn nhanh.
- **🔁 Ôn tập tuần:** phần quiz đã được nâng lên trắc nghiệm A/B/C.
- **🎧 Luyện nghe:**
  - Có nhạc nền dịu tự tạo; bật/tắt ở mục *Nhạc nền*.
  - Có tuỳ chọn **kéo dài tới N phút**: các câu được lặp theo vòng, phù hợp video 30–60 phút để nghe khi ngủ hoặc lái xe.

## Thử thách 30 ngày (tab 📅)
1. Nhập chủ đề, rồi bấm **Lập lịch**. App dùng khung 4 tuần mặc định (ngày 7/14/21/28 là ôn tập), hoặc lập lịch bằng LLM.
2. Chọn ngày N, rồi bấm **Sinh & dựng**. LLM viết bài theo phong cách `thu_thach` và lưu vào `projects/_challenge/...`. Lần sau dựng lại không phải gọi LLM nữa.

## Lịch đăng gợi ý (mỗi kênh)
| Thứ | Short | Video dài (cuối tuần) |
|---|---|---|
| 2 | Tình huống đời thường | |
| 3 | Tin nhắn | |
| 4 | Mổ xẻ chữ / Phát âm | |
| 5 | Phim bộ (tập mới) | |
| 6 | Đố vui A/B/C | |
| 7 | 1 câu – 3 ngôn ngữ (đăng cả 3 kênh) | Hỗn hợp định dạng / Luyện nghe 30 phút |
| CN | Câu thoại phim | Ôn tập tuần |
| Hằng ngày | Thử thách 30 ngày (series riêng) | |
