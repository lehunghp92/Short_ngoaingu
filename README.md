# 🎬 Shorts Studio

App PC dựng video **short giải thích kiểu infographic** (học kỹ thuật kênh *The Infographics Show*), cho
YouTube Shorts / TikTok / Reels / Facebook. Chỉ dùng **mã nguồn mở, chạy offline**.

| Bước | Công cụ (mã nguồn mở) |
|---|---|
| Kịch bản | Công thức 6 nhịp + LLM local qua [Ollama](https://ollama.com) (tuỳ chọn), ví dụ `qwen2.5:7b` |
| Giọng đọc | [Piper](https://github.com/OHF-Voice/piper1-gpl): **có giọng tiếng Việt**, chạy trên CPU · [Kokoro](https://github.com/hexgrad/kokoro): tiếng Anh |
| Hình ảnh | Stable Diffusion qua [diffusers](https://github.com/huggingface/diffusers) (SDXL-Turbo) · hoặc thẻ đồ hoạ tự vẽ (không cần GPU) |
| Dựng video | Pillow + ffmpeg: Ken Burns, hiệu ứng pop, phụ đề karaoke, thanh tiến trình, -14 LUFS |
| Font | [Be Vietnam Pro](https://fonts.google.com/specimen/Be+Vietnam+Pro) (OFL) |

## Dàn nhân vật hoạt hình (gốc, dùng chung khung xương)
![Dàn nhân vật](docs/cast_sheet.png)
Gồm 21 nhân vật (ông chủ, cô tạp hoá, cô giáo, bạn tập gym, đầu bếp, bác sĩ…), 10 động tác, 5 biểu cảm, 12 đạo cụ và 10 phông nền; miệng nhép theo giọng và mắt tự chớp.
Mẫu có sẵn: `examples/tien_giay_nhanvat.json`. Chi tiết xem [CHARACTER_GUIDE.md](CHARACTER_GUIDE.md).

## 🌏 Kênh học ngoại ngữ (Anh / Trung / Hàn)
**8 phong cách dạy học** để chọn: Hỏi–Giảng, Nhập vai tình huống, Top 3 lỗi sai, Game show đố vui, 5 từ vựng tốc độ, Luyện nói theo (shadowing), Truyện chêm, Giảng 1 người. Video dài 40–50 giây, **Full-HD 1080×1920** (H.264 High, CRF 17). Bơ (người học) hỏi, Mai (cô giáo) giảng và đọc mẫu.
Mỗi nhân vật có giọng Việt riêng (VieNeu-TTS, 25 giọng mẫu), bảng tên hiện phía trên người đang nói.
Mẫu kịch bản: `examples/lessons/cafe_{en,zh,ko}.json`; định dạng giảng 1 người cũ nằm trong `examples/lessons/giang/`.
Trong app: chọn **nguồn kịch bản** (thư viện có sẵn hoặc LLM), **module TTS** (VieNeu hoặc Piper) và giọng cho từng nhân vật.

Một chủ đề sinh ra 3 bài học cho 3 kênh. Mỗi video gồm: thẻ học 3 tầng (chữ ngoại ngữ, phiên âm IPA/pinyin/romaja,
nghĩa tiếng Việt), dạng câu sai ✗ / câu đúng ✓, giọng bản ngữ đọc mẫu 2 lần (thường rồi chậm), quiz đếm ngược,
và hội thoại 2 nhân vật.
```bash
python lesson_cli.py examples/lessons/                   # dựng 3 video mẫu "đi cà phê"
python lesson_cli.py --generate "hỏi đường" --langs en,zh,ko   # sinh bằng Ollama rồi dựng
```
Trong app, dùng tab **🌏 Bài học ngoại ngữ**. Chiến lược và lịch đăng xem **[LANGUAGE_CHANNELS.md](LANGUAGE_CHANNELS.md)**.

## Cài đặt (Windows / macOS / Linux, Python 3.10–3.12)
```bash
cd shorts_studio
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python app.py                   # mở http://127.0.0.1:7860
```
Windows: có thể bấm đúp `run_windows.bat`.

**Tuỳ chọn:**
- **Sinh kịch bản tự động:** cài [Ollama](https://ollama.com), rồi chạy `ollama pull qwen2.5:7b`.
- **Ảnh AI:** cần GPU NVIDIA ≥ 6 GB VRAM. Cài [PyTorch CUDA](https://pytorch.org/get-started/locally/),
  rồi chạy `pip install -r requirements-gpu.txt`. Lần đầu chạy sẽ tự tải model SDXL-Turbo (khoảng 7 GB).

Model giọng (khoảng 60 MB mỗi giọng) và font được tự tải lần đầu vào `models/` và `assets/`.

## 🎬 Video dài cùng chủ đề (YouTube)
Tab **🎬 Video dài** (hoặc lệnh `long_cli.py`) ghép và mở rộng các bài cùng chủ đề thành video 8–60 phút, ngang 1920×1080.
Có 5 định dạng: trọn chủ đề, phim tình huống, luyện nghe thụ động, ôn tập tuần, flashcard.
Mỗi lần dựng tự xuất mốc chương YouTube, phụ đề SRT, thumbnail và PDF tóm tắt. Chiến lược kênh xem **[LONGFORM.md](LONGFORM.md)**.

### ✅ Quy trình trước khi đăng
1. **Chạy thử trên máy GPU**: `python batch_render.py` dựng 8 kịch bản mẫu, xuất `projects/_batch/<giờ>/bao_cao.md` (thời lượng ước lượng vs thực tế, thời gian dựng, tốc độ x thời gian thực, giọng từng nhân vật). Máy chưa có Qwen: `python batch_render.py --native piper --no-one-voice`.
2. **Độ dài 40–50 s**: nút 🔎 *Rà soát* ước lượng thời lượng ngay từ kịch bản (không cần dựng) và cảnh báo khi ngắn/dài.
3. **Rà soát ngôn ngữ**: kiểm tra tự động (thiếu nghĩa, lẫn chữ viết, câu quá dài so với level, đáp án quiz lệch câu công bố, mở/kết dài) + tuỳ chọn LLM thứ hai soát ngữ pháp/độ tự nhiên/nghĩa. Nút 📤 xuất **bảng CSV** cho người bản xứ: đánh `x` vào cột *ok* hoặc ghi câu sửa ở *sua_thanh* / *nghia_sua* → 📥 nhập lại, app tự cập nhật kịch bản.

### 📚 Khung nội dung 10 định dạng × 5 level × 3 ngôn ngữ
Level 1-5 ↔ CEFR A1-C1 / HSK 1-6 / TOPIK 1-6: ngữ pháp, độ dài câu, chủ đề, trọng tâm từng định dạng; từ vựng chuẩn tải từ nguồn mở (HSK 3.0, NIKL+TOPIK, CEFR-J) và câu mẫu thật từ Tatoeba; tự kiểm tra từ vượt level. Tab **📚 Khung nội dung** hoặc `python curriculum_cli.py`. Xem **[CURRICULUM.md](CURRICULUM.md)**.

### 🔟 10 định dạng thu hút nhất
Tin nhắn KakaoTalk/WeChat, đố vui A/B/C có đếm ngược và tiếng hiệu ứng, 1 câu – 3 ngôn ngữ, mổ xẻ chữ, phát âm (thanh điệu/khẩu hình), câu thoại phim, phim bộ (Tập trước/Còn tiếp), thử thách 30 ngày (tab riêng), video dài hỗn hợp định dạng, luyện nghe có nhạc nền và kéo dài tới N phút. Xem **[FORMATS10.md](FORMATS10.md)**.
```bash
python long_cli.py --fmt tron_chu_de examples/lessons/giao_tiep/taphoa-muabanh_ko.json examples/lessons/cafe_ko.json
python long_cli.py --fmt luyen_nghe --repeats 2 "examples/lessons/**/*_ko.json"
```

## 🎙️ Giọng đọc — "1 nhân vật = 1 giọng"
| Module | Dùng cho | Ghi chú |
|---|---|---|
| **VieNeu-TTS** | tiếng Việt (chính) | 25 giọng mẫu Bắc/Trung/Nam |
| **OmniVoice** (fine-tune tiếng Việt) | tiếng Việt (**dự phòng**) | nhân bản giọng từ `assets/voices/*.wav`; cài bằng `setup_omnivoice.bat` |
| **Qwen3-TTS** 0.6B (Alibaba) | Trung / Hàn / Anh | GPU; bản **Base** nhân bản giọng, bản CustomVoice có 9 giọng sẵn |
| Piper | mọi thứ tiếng | nhẹ, CPU, không cần GPU |

- **Mặc định mỗi nhân vật chỉ có 1 giọng trong cả clip.** Giọng tiếng Việt của nhân vật được **nhân bản** sang câu Trung/Hàn/Anh
  bằng Qwen3-TTS Base (dự phòng bằng OmniVoice), nên cùng một nhân vật nói cả hai thứ tiếng bằng cùng một giọng.
- Giọng `auto`: tự chọn theo **giới tính nhân vật**, và 2 nhân vật trong một clip không bao giờ trùng giọng.
- Muốn dùng **giọng của chính bạn**: thu một đoạn 5–10 giây vào `assets/voices/TenBan.wav`, đặt lời thoại của đoạn đó vào
  `TenBan.txt`. Giọng sẽ xuất hiện trong module OmniVoice và dùng được cho nhân bản giọng.

## ⚡ Dùng GPU (NVIDIA)
App **tự phát hiện GPU**, không cần cấu hình tay:
| Phần | GPU | Khi không có GPU |
|---|---|---|
| Mã hoá video Full-HD | NVENC `h264_nvenc` | libx264 (CPU) |
| Giọng VieNeu-TTS | PyTorch CUDA | ONNX CPU |
| Ảnh Stable Diffusion | CUDA fp16 | (không khuyến nghị) |

Cách cài: chạy `run_windows.bat` (tự cài PyTorch CUDA nếu thấy card NVIDIA), hoặc làm tay theo `requirements-gpu.txt`.
Sau đó chạy `python check_gpu.py` để kiểm tra. Đầu trang app cũng hiện trạng thái GPU.
Đặt biến `SHORTS_NO_GPU=1` nếu muốn tắt GPU.

## Dùng dòng lệnh
```bash
python cli.py examples/khong_ngu_11_ngay.json --voice "vi-vais1000 (Việt, nữ)" --images card --watermark "@TenKenh"
```
Kết quả nằm trong `projects/<tên-video>/`:
- file video `.mp4`
- `cover.jpg` (ảnh bìa)
- `export/` gồm file và phần mô tả riêng cho từng nền tảng

Xem **[TECHNIQUES.md](TECHNIQUES.md)** (kỹ thuật xây kênh) và **[CHARACTER_GUIDE.md](CHARACTER_GUIDE.md)** (kế hoạch tạo nhân vật hoạt hình riêng).
