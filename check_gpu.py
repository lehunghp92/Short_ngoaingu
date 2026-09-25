"""Kiểm tra app có dùng được GPU trên máy bạn không:  python check_gpu.py"""
from studio import gpu

print("ffmpeg dùng        :", gpu.ffmpeg_exe())
print("Mã hoá NVENC (GPU) :", "CÓ" if gpu.nvenc_ok() else "KHÔNG (sẽ dùng CPU libx264)")
cuda = gpu.cuda_info()
print("PyTorch CUDA       :", cuda or "KHÔNG — cài torch bản CUDA: https://pytorch.org/get-started/locally/")
try:
    import onnxruntime as ort
    print("ONNX providers     :", ort.get_available_providers())
except ImportError:
    pass
try:
    import qwen_tts  # noqa: F401
    print("Qwen3-TTS          :", "ĐÃ CÀI — sẽ chạy " + ("GPU" if cuda else "CPU (chậm)"))
except ImportError:
    print("Qwen3-TTS          : CHƯA CÀI — pip install qwen-tts")
if cuda:
    from vieneu import Vieneu
    v = Vieneu()
    print("VieNeu backend     :", getattr(v, "backend", "?"), "(pytorch = đang chạy GPU)")
