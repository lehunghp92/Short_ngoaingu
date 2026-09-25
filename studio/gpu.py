"""Tự phát hiện và dùng GPU trên máy của bạn (không cần cấu hình tay).

- Mã hoá video : NVIDIA NVENC (h264_nvenc) nếu ffmpeg + driver hỗ trợ → nhanh gấp nhiều lần CPU
- VieNeu-TTS   : tự chạy PyTorch/CUDA khi đã cài torch bản CUDA (xem requirements-gpu.txt)
- Stable Diffusion: diffusers trên CUDA (fp16)
- Qwen3-TTS    : giọng bản ngữ Trung/Hàn/Anh trên CUDA (bfloat16)
Ghép khung hình (Pillow) vẫn chạy CPU.
"""
import os
import shutil
import subprocess
from functools import lru_cache

import imageio_ffmpeg


@lru_cache(maxsize=None)
def ffmpeg_exe() -> str:
    """Ưu tiên ffmpeg do bạn chỉ định (SHORTS_FFMPEG) → ffmpeg trong PATH → bản kèm imageio-ffmpeg."""
    return os.environ.get("SHORTS_FFMPEG") or shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()


@lru_cache(maxsize=None)
def nvenc_ok() -> bool:
    """Thử mã hoá 1 khung hình bằng h264_nvenc — chỉ True khi GPU NVIDIA + driver thực sự dùng được."""
    if os.environ.get("SHORTS_NO_GPU"):
        return False
    try:
        r = subprocess.run([ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                            "color=c=black:s=256x256:d=0.1", "-frames:v", "1", "-c:v", "h264_nvenc",
                            "-f", "null", "-"], capture_output=True, timeout=30)
        return r.returncode == 0
    except Exception:  # noqa: BLE001
        return False


@lru_cache(maxsize=None)
def cuda_info() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            p = torch.cuda.get_device_properties(0)
            return f"{p.name} ({p.total_memory / 2**30:.0f} GB)"
    except Exception:  # noqa: BLE001
        pass
    return ""


def encoder_args(quality: str) -> list:
    """Tham số mã hoá H.264 Full-HD: NVENC nếu có, không thì libx264."""
    from .config import QUALITY
    q = QUALITY.get(quality, QUALITY["fullhd"])
    common = ["-maxrate", q["maxrate"], "-bufsize", q["bufsize"], "-profile:v", "high", "-pix_fmt", "yuv420p"]
    if nvenc_ok():
        cq = str(int(q["crf"]) + 2)            # NVENC cq ~ x264 crf + 2 cho chất lượng tương đương
        return ["-c:v", "h264_nvenc", "-preset", "p7" if quality == "fullhd" else "p3", "-tune", "hq",
                "-rc", "vbr", "-cq", cq, "-b:v", "0", *common]
    return ["-c:v", "libx264", "-preset", q["preset"], "-crf", q["crf"], "-level", "4.2", *common]


def summary() -> str:
    cuda = cuda_info()
    parts = [f"🟢 GPU CUDA: {cuda}" if cuda else "⚪ Không thấy GPU CUDA cho PyTorch (VieNeu/Stable Diffusion chạy CPU)",
             "🟢 Mã hoá video: NVENC (GPU)" if nvenc_ok() else "⚪ Mã hoá video: libx264 (CPU)"]
    return " · ".join(parts)
