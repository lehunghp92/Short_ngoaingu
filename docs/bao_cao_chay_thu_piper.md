# Báo cáo dựng hàng loạt

*25/09/2026 07:29*

- **GPU (PyTorch CUDA)**: không
- **Mã hoá NVENC**: không (CPU)
- **Qwen3-TTS**: chưa cài
- **1 nhân vật = 1 giọng**: tắt
- **Giọng Việt**: vieneu
- **Chất lượng**: nhap
- **Tổng**: 8 video, 316s video trong 3431s (0.09x thời gian thực, ~429s/video)

| Kịch bản | Ước lượng | Thực tế | Dựng mất | Tốc độ | Trạng thái | Giọng |
|---|---|---|---|---|---|---|
| cauthoai-phim_ko.json | 44.6s | 41.6s | 594.0s | 0.07x | OK | A=vieneu:Hải Đăng, B=vieneu:Trúc Ly |
| dovui-abc-dulich_en.json | 52.0s | 39.8s | 481.3s | 0.08x | NGẮN | A=vieneu:Trúc Ly, B=vieneu:Hải Đăng |
| motcau-bangonngu_ko.json | 51.6s | 42.5s | 209.2s | 0.20x | OK | A=vieneu:Trúc Ly, B=vieneu:Hải Đăng |
| moxechu-bothu_zh.json | 41.7s | 33.5s | 416.3s | 0.08x | NGẮN | A=vieneu:Trúc Ly, B=vieneu:Hải Đăng |
| phatam-4thanh_zh.json | 46.8s | 38.2s | 250.7s | 0.15x | NGẮN | A=vieneu:Trúc Ly, B=vieneu:Hải Đăng |
| phimbo-lacseoul-tap2_ko.json | 46.5s | 39.6s | 476.1s | 0.08x | NGẮN | A=vieneu:Trúc Ly, B=vieneu:Ngọc Huyền, N=vieneu:Thiện Minh |
| thuthach-ngay01_ko.json | 43.9s | 41.0s | 494.5s | 0.08x | OK | A=vieneu:Trúc Ly, B=vieneu:Hải Đăng |
| tinnhan-henhcafe_ko.json | 45.5s | 39.4s | 509.3s | 0.08x | NGẮN | A=vieneu:Hải Đăng, B=vieneu:Trúc Ly, N=vieneu:Thiện Minh |
