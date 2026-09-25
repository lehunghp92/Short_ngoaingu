"""Hình minh hoạ cho từng cảnh.

- sd       : Stable Diffusion (diffusers, mã nguồn mở). Mặc định SDXL-Turbo — 1-4 bước, nhanh trên GPU.
- card     : không cần GPU — tự vẽ thẻ đồ hoạ phẳng (hình khối + từ khoá) theo bảng màu kênh.
- Ảnh tự thêm: đặt đường dẫn vào scene.image và app sẽ dùng luôn.
"""
import hashlib
import math
import random
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .config import ASSETS, HEIGHT, WIDTH, Style

FONT_URLS = {
    "ExtraBold": "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/bevietnampro/BeVietnamPro-ExtraBold.ttf",
    "Bold": "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/bevietnampro/BeVietnamPro-Bold.ttf",
}
_fonts = {}


def font(size: int, weight: str = "ExtraBold") -> ImageFont.FreeTypeFont:
    """Be Vietnam Pro (OFL) — hỗ trợ đầy đủ dấu tiếng Việt. Tự tải lần đầu, lỗi thì dùng font hệ thống."""
    key = (size, weight)
    if key not in _fonts:
        path = ASSETS / "fonts" / f"BeVietnamPro-{weight}.ttf"
        try:
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                r = requests.get(FONT_URLS[weight], timeout=60)
                r.raise_for_status()
                path.write_bytes(r.content)
            _fonts[key] = ImageFont.truetype(str(path), size)
        except Exception:  # noqa: BLE001
            for fallback in ("arialbd.ttf", "DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
                try:
                    _fonts[key] = ImageFont.truetype(fallback, size)
                    break
                except OSError:
                    continue
            else:
                _fonts[key] = ImageFont.load_default()
    return _fonts[key]


# ---------------- Stable Diffusion ----------------
_pipe = {}


def sd_available() -> bool:
    try:
        import diffusers  # noqa: F401
        import torch  # noqa: F401
        return True
    except ImportError:
        return False


def generate_sd(prompt: str, style: Style, out: Path, model: str = "stabilityai/sdxl-turbo",
                steps: int = 4, seed: int = 0) -> Path:
    import torch
    from diffusers import AutoPipelineForText2Image
    if model not in _pipe:
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if dev == "cuda" else torch.float32
        p = AutoPipelineForText2Image.from_pretrained(model, torch_dtype=dtype)
        _pipe[model] = p.to(dev)
    pipe = _pipe[model]
    turbo = "turbo" in model
    g = torch.Generator(device=pipe.device).manual_seed(seed)
    img = pipe(prompt=f"{prompt}, {style.image_prompt}",
               negative_prompt=None if turbo else style.negative_prompt,
               num_inference_steps=steps, guidance_scale=0.0 if turbo else 6.5,
               width=768, height=1024 if not turbo else 768, generator=g).images[0]
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


# ---------------- Phông nền phẳng cho cảnh có nhân vật (không cần GPU) ----------------
def generate_backdrop(style: Style, out: Path, idx: int = 0) -> Path:
    W, H = WIDTH, int(HEIGHT * 0.62)
    acc = style.accents
    sky = acc[(idx + 2) % len(acc)]
    img = Image.new("RGB", (W, H), sky)
    d = ImageDraw.Draw(img)
    rnd = random.Random(idx)
    d.ellipse([W - 330, 80, W - 130, 280], fill="#FFF3C4")                     # mặt trời
    for _ in range(3):                                                           # mây
        x, y = rnd.randint(40, W - 300), rnd.randint(60, 380)
        for dx, r in ((0, 50), (60, 70), (130, 50)):
            d.ellipse([x + dx - r, y - r, x + dx + r, y + r], fill="#FFFFFF")
    for j, col in enumerate((acc[(idx + 3) % len(acc)], acc[(idx + 4) % len(acc)])):   # đồi
        cx = rnd.randint(0, W)
        d.ellipse([cx - 900, H - 520 + j * 120, cx + 900, H + 900], fill=col)
    d.rectangle([0, H - 90, W, H], fill="#3C3C3C")                              # sàn
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


# ---------------- Thẻ đồ hoạ phẳng (không cần GPU) ----------------
def _wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + ([cur] if cur else [])


def generate_card(scene_text: str, keyword: str, style: Style, out: Path, idx: int = 0) -> Path:
    seed = int(hashlib.md5(scene_text.encode()).hexdigest()[:8], 16)
    rnd = random.Random(seed)
    W, H = WIDTH, int(HEIGHT * 0.62)
    img = Image.new("RGB", (W, H), style.bg)
    d = ImageDraw.Draw(img)
    acc = style.accents
    main = acc[idx % len(acc)]
    # nền: các khối tròn lớn mờ
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for i in range(6):
        r = rnd.randint(120, 380)
        x, y = rnd.randint(-100, W + 100), rnd.randint(-100, H + 100)
        c = acc[(idx + i + 1) % len(acc)]
        ld.ellipse([x - r, y - r, x + r, y + r], fill=c + "40")
    img.paste(layer.filter(ImageFilter.GaussianBlur(8)), (0, 0), layer.filter(ImageFilter.GaussianBlur(8)))
    # hình chính: vòng tròn đặc + vành + các "tia" kiểu infographic
    cx, cy, R = W // 2, H // 2, 300
    for k in range(12):
        a = 2 * math.pi * k / 12 + rnd.random() * 0.2
        d.line([cx + math.cos(a) * (R + 30), cy + math.sin(a) * (R + 30),
                cx + math.cos(a) * (R + 90), cy + math.sin(a) * (R + 90)], fill=acc[(idx + 2) % len(acc)], width=14)
    d.ellipse([cx - R - 18, cy - R - 18, cx + R + 18, cy + R + 18], fill="#FFFFFF")
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=main)
    label = (keyword or scene_text.split()[0]).upper()
    size = 150
    while size > 50:
        f = font(size)
        lines = _wrap(d, label, f, 2 * R - 60)
        if len(lines) <= 3 and all(d.textlength(l, font=f) <= 2 * R - 60 for l in lines):
            break
        size -= 10
    lh = size * 1.1
    y0 = cy - lh * len(lines) / 2
    for i, l in enumerate(lines):
        d.text((cx, y0 + i * lh + lh / 2), l, font=f, fill="#FFFFFF", anchor="mm",
               stroke_width=6, stroke_fill="#00000055")
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out
