"""Cấu hình chung: đường dẫn, kích thước video, phong cách hình ảnh."""
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "projects"
MODELS = ROOT / "models"
ASSETS = ROOT / "assets"

WIDTH, HEIGHT, FPS = 1080, 1920, 30      # Full-HD dọc 9:16 — chuẩn Shorts/TikTok/Reels
QUALITY = {
    # CRF thấp = nét hơn. Maxrate ~12 Mbps: đủ nét sau khi nền tảng nén lại, file 40-50s ~ 30-60 MB.
    "fullhd": {"preset": "slow", "crf": "17", "maxrate": "12M", "bufsize": "24M"},
    "nhap": {"preset": "veryfast", "crf": "26", "maxrate": "4M", "bufsize": "8M"},
}


@dataclass
class Style:
    """Bộ nhận diện kênh — giữ CỐ ĐỊNH cho mọi video (bí quyết nhận diện của kênh infographic)."""
    name: str = "infographic"
    bg: str = "#1B2A41"
    accents: tuple = ("#FFB400", "#FF5A5F", "#00A6A6", "#7FB800", "#8E6CEF")
    text: str = "#FFFFFF"
    caption_highlight: str = "#FFB400"
    # Prompt phong cách cho Stable Diffusion: vector 2D phẳng, viền đậm, nhân vật đơn giản
    image_prompt: str = ("flat 2D vector cartoon illustration, infographic style, bold clean outlines, "
                         "simple rounded characters, vibrant solid colors, minimal shading, "
                         "centered composition, plain background")
    negative_prompt: str = ("photo, realistic, 3d render, text, letters, watermark, logo, blurry, "
                            "noisy, deformed hands, extra limbs")


STYLES = {
    "infographic": Style(),
    "sang": Style(name="sang", bg="#F4F1EA", text="#1B1B1B", caption_highlight="#FF5A5F",
                  accents=("#FF5A5F", "#2D7DD2", "#F7A400", "#3BB273", "#7768AE")),
}


@dataclass
class RenderOptions:
    style: str = "infographic"
    captions: bool = True
    progress_bar: bool = True
    zoom: float = 0.08            # Ken Burns: phóng to 8% mỗi cảnh
    music: str = ""               # đường dẫn nhạc nền (tuỳ chọn)
    music_volume: float = 0.12
    watermark: str = ""           # tên kênh góc trên
    quality: str = "fullhd"       # fullhd: chất lượng cao (mặc định) | nhap: xem thử nhanh
    layout: str = "doc"           # doc: 1080x1920 (short) | ngang: 1920x1080 (video dài YouTube)
    extra: dict = field(default_factory=dict)
