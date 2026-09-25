"""Dựng video dọc 1080x1920 bằng Pillow + ffmpeg (imageio-ffmpeg kèm sẵn binary, không cần cài thêm).

Bố cục (kỹ thuật short giữ chân người xem):
  - Trên:   chữ lớn (con số / từ khoá) bật lên đầu mỗi cảnh
  - Giữa:   hình minh hoạ chuyển động Ken Burns + hiệu ứng "pop" khi đổi cảnh (mỗi 2-4 giây)
  - Dưới:   phụ đề karaoke 3-4 từ, tô màu từ đang đọc (đa số người xem short tắt tiếng)
  - Đáy:    thanh tiến trình — tạo cảm giác "sắp hết, xem nốt"
"""
import math
import subprocess
from pathlib import Path
from typing import Callable, List, Optional

from PIL import Image, ImageDraw, ImageOps

from . import character as charmod
from . import props as propmod
from .config import FPS, RenderOptions, STYLES
from .images import _wrap, font
from .langs import cjk_font, roman_font
from .script import Project

from .gpu import encoder_args, ffmpeg_exe

FFMPEG = ffmpeg_exe()
# ---------- Bố cục: "doc" 1080x1920 (short) | "ngang" 1920x1080 (video dài YouTube) ----------
LAYOUTS = {
    "doc": dict(W=1080, H=1920, IMG_BOX=(40, 470, 1040, 1440), CARD_BOX=(70, 150, 1010, 670),
                CAPTION_Y=1560, CAPTION_X=540, CAPTION_W=940, OVERLAY=(540, 250), OVERLAY_W=960, WM=(540, 90)),
    # ngang: sân khấu nhân vật bên trái, thẻ học + phụ đề bên phải
    "ngang": dict(W=1920, H=1080, IMG_BOX=(40, 110, 980, 1040), CARD_BOX=(1030, 150, 1880, 620),
                  CAPTION_Y=700, CAPTION_X=1455, CAPTION_W=820, OVERLAY=(1455, 380), OVERLAY_W=820, WM=(1455, 60)),
}
WIDTH, HEIGHT = 1080, 1920
IMG_BOX = LAYOUTS["doc"]["IMG_BOX"]
CARD_BOX = LAYOUTS["doc"]["CARD_BOX"]
CAPTION_Y, CAPTION_X, CAPTION_W = 1560, 540, 940
OVERLAY, OVERLAY_W, WM = (540, 250), 960, (540, 90)


def set_layout(name: str) -> None:
    global WIDTH, HEIGHT, IMG_BOX, CARD_BOX, CAPTION_Y, CAPTION_X, CAPTION_W, OVERLAY, OVERLAY_W, WM
    L = LAYOUTS.get(name, LAYOUTS["doc"])
    WIDTH, HEIGHT, IMG_BOX, CARD_BOX = L["W"], L["H"], L["IMG_BOX"], L["CARD_BOX"]
    CAPTION_Y, CAPTION_X, CAPTION_W = L["CAPTION_Y"], L["CAPTION_X"], L["CAPTION_W"]
    OVERLAY, OVERLAY_W, WM = L["OVERLAY"], L["OVERLAY_W"], L["WM"]
POP_FRAMES = 7


def _ease_out(t: float) -> float:
    return 1 - (1 - t) ** 3


def _prepare(path: str, box_w: int, box_h: int, zoom: float) -> Image.Image:
    img = Image.open(path).convert("RGB")
    return ImageOps.fit(img, (int(box_w * (1 + zoom)), int(box_h * (1 + zoom))), Image.LANCZOS)


def _rounded_mask(w: int, h: int, r: int = 48) -> Image.Image:
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=255)
    return m


def _word_times(text: str, dur: float) -> List[tuple]:
    """Chia thời lượng câu cho từng từ theo độ dài ký tự (xấp xỉ tốt cho TTS đều nhịp)."""
    words = text.split()
    weights = [len(w) + 2 for w in words]
    total, t, out = sum(weights), 0.0, []
    speak = dur * 0.94
    for w, k in zip(words, weights):
        d = speak * k / total
        out.append((w, t, t + d))
        t += d
    return out


def _caption_chunks(words: List[tuple], size: int = 4) -> List[List[tuple]]:
    return [words[i:i + size] for i in range(0, len(words), size)]


def _draw_actor(frame, actor, s, lt, env, k, st, action=None, expression=None, position=None,
                facing_left=False, prop=None):
    """Nhân vật đứng trên 'sàn' của khung hình, di chuyển nếu động tác có 'move'."""
    action = action or s.action
    expression = s.expression if expression is None else expression
    position = position or s.position
    prop = s.prop if prop is None else prop
    a = charmod.ACTIONS.get(action, charmod.ACTIONS["dung"])
    mo = float(env[min(k, len(env) - 1)]) if env is not None and len(env) else 0.0
    prop_img = propmod.get(prop) if prop in propmod.PROPS else None
    img = actor.render(action, lt, mouth_open=mo, expression=expression, prop=prop_img)
    bbox = img.getbbox()
    if not bbox:
        return
    img = img.crop(bbox)
    target_h = int((IMG_BOX[3] - IMG_BOX[1]) * (0.58 if s.card else 0.62) * actor.stature)
    img = img.resize((max(1, int(img.width * target_h / img.height)), target_h), Image.LANCZOS)
    bw = IMG_BOX[2] - IMG_BOX[0]
    xs = {"trai": 0.25, "giua": 0.5, "phai": 0.75}
    fx = xs.get(position, 0.5)
    move = a.get("move", 0)
    flip = facing_left
    if move:   # đi ngang khung hình trong suốt cảnh
        p = lt / max(s.duration, 0.01)
        fx = 0.15 + 0.7 * p if position != "phai" else 0.85 - 0.7 * p
        flip = position == "phai"
    if flip:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    bob = a.get("bob", 0) * abs(math.sin(lt * (8 if move else 2.6)))
    jump = a.get("jump", 0) * abs(math.sin(min(lt * 6, math.pi))) if not a.get("loop") else \
        a.get("jump", 0) * abs(math.sin(lt * 5))
    floor = IMG_BOX[3] - 40
    x = int(IMG_BOX[0] + bw * fx - img.width / 2)
    y = int(floor - img.height - bob - jump)
    # bóng đổ dưới chân
    sh = Image.new("RGBA", (img.width, 40), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([img.width * 0.2, 5, img.width * 0.8, 35], fill=(0, 0, 0, 70))
    frame.paste(sh, (x, floor - 25), sh)
    # pop-in đầu cảnh
    if k < POP_FRAMES:
        e = _ease_out((k + 1) / POP_FRAMES)
        img = img.resize((max(1, int(img.width * e)), max(1, int(img.height * e))))
        x += int((1 - e) * img.width / 2)
        y = int(floor - img.height - bob - jump)
    frame.paste(img, (x, y), img)
    # bảng tên phía trên người ĐANG NÓI (chỉ khi có 2 nhân vật)
    if s.character2 and env is not None and k >= POP_FRAMES:
        name = actor.name.split("(")[0].strip()
        fn = font(40)
        d = ImageDraw.Draw(frame)
        w = int(d.textlength(name, font=fn)) + 50
        tx, ty = x + img.width // 2 - w // 2, y - 78
        d.rounded_rectangle([tx, ty, tx + w, ty + 60], 30, fill=st.accents[0], outline="#1E1A2B", width=5)
        d.polygon([tx + w // 2 - 14, ty + 58, tx + w // 2 + 14, ty + 58, tx + w // 2, ty + 78], fill=st.accents[0])
        d.text((tx + w // 2, ty + 30), name, font=fn, fill="#1E1A2B", anchor="mm")


def _draw_focus_item(frame, s, lt, k, st):
    """Đồ vật đang được nói tới: hiện to giữa sân khấu, vòng sáng nhấp nháy + thẻ giá.
    Nhân vật đang nói chỉ tay về phía đồ vật (action chi_tay)."""
    img = propmod.get(s.item).copy()
    size = 250
    img.thumbnail((size, size), Image.LANCZOS)
    bw = IMG_BOX[2] - IMG_BOX[0]
    cx = IMG_BOX[0] + int(bw * (0.5 if s.character2 else 0.74))
    cy = IMG_BOX[1] + int((IMG_BOX[3] - IMG_BOX[1]) * 0.47)
    e = _ease_out(min(1.0, (k + 1) / (POP_FRAMES + 3)))
    bob = int(8 * math.sin(lt * 4))
    d = ImageDraw.Draw(frame)
    glow = 150 + int(10 * math.sin(lt * 6))
    ring = Image.new("RGBA", (glow * 2 + 20, glow * 2 + 20), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    rd.ellipse([10, 10, glow * 2 + 10, glow * 2 + 10], fill=(255, 255, 255, 170), outline=st.accents[0], width=10)
    frame.paste(ring, (cx - glow - 10, cy - glow - 10 + bob), ring)
    if e < 1:
        img = img.resize((max(1, int(img.width * e)), max(1, int(img.height * e))))
    frame.paste(img, (cx - img.width // 2, cy - img.height // 2 + bob), img)
    if s.price:
        fp = font(46)
        w = int(d.textlength(s.price, font=fp)) + 50
        tx, ty = cx + 60, cy + 90 + bob
        d.polygon([tx - 26, ty + 30, tx, ty, tx + w, ty, tx + w, ty + 60, tx, ty + 60], fill="#FFD166",
                  outline="#1E1A2B")
        d.ellipse([tx - 12, ty + 22, tx + 4, ty + 38], fill="#1E1A2B")
        d.text((tx + w // 2 + 6, ty + 30), s.price, font=fp, fill="#1E1A2B", anchor="mm")


def _slide_frame(s, lt, k, st, actors):
    """Màn slide toàn khung: tiêu đề video, mục lục, chuyển chương, ôn nhanh, kết thúc."""
    sl = s.slide
    kind = sl.get("kind", "chapter")
    frame = Image.new("RGB", (WIDTH, HEIGHT), st.bg)
    d = ImageDraw.Draw(frame)
    acc = st.accents
    landscape = WIDTH > HEIGHT
    e = _ease_out(min(1.0, (k + 1) / (POP_FRAMES + 4)))
    # hoạ tiết nền: các vòng tròn màu mờ
    deco = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    dd = ImageDraw.Draw(deco)
    for i, (fx, fy, r) in enumerate(((0.08, 0.15, 260), (0.92, 0.2, 200), (0.85, 0.9, 320), (0.1, 0.88, 220))):
        dd.ellipse([WIDTH * fx - r, HEIGHT * fy - r, WIDTH * fx + r, HEIGHT * fy + r], fill=acc[i % len(acc)] + "30")
    frame.paste(deco, (0, 0), deco)
    cx = WIDTH // 2
    title = sl.get("title", "")
    lang = sl.get("lang", "en")
    if kind in ("title", "outro"):
        ft = font(96 if landscape else 88)
        lines = _wrap(d, title, ft, WIDTH * 0.62 if landscape else WIDTH - 120)[:3]
        y = HEIGHT * (0.30 if landscape else 0.26) - len(lines) * 55 + (1 - e) * 60
        for ln in lines:
            d.text((cx, y), ln, font=ft, fill=st.text, anchor="mm", stroke_width=6, stroke_fill="#000000")
            y += 110
        if sl.get("subtitle"):
            fs = font(48, "Bold")
            maxw = WIDTH * (0.6 if landscape else 0.86)
            sub = _wrap(d, sl["subtitle"], fs, maxw - 80)[:3]
            w = max(d.textlength(ln, font=fs) for ln in sub) + 80
            hh = 40 + len(sub) * 62
            d.rounded_rectangle([cx - w / 2, y + 10, cx + w / 2, y + 10 + hh], 40, fill=acc[0])
            for li, ln in enumerate(sub):
                d.text((cx, y + 10 + 20 + 31 + li * 62), ln, font=fs, fill="#1E1A2B", anchor="mm")
        # nhân vật chào ở hai bên
        for idx, key in enumerate(sl.get("cast", [])[:2]):
            a = actors.setdefault(key, charmod.load(key))
            im = a.render("vay_tay" if idx == 0 else "vui_mung", lt, expression="vui")
            im = im.crop(im.getbbox())
            th = int(HEIGHT * (0.55 if landscape else 0.36))
            im = im.resize((int(im.width * th / im.height), th), Image.LANCZOS)
            if idx == 1:
                im = im.transpose(Image.FLIP_LEFT_RIGHT)
            x = int(WIDTH * (0.06 if idx == 0 else 0.94) - (0 if idx == 0 else im.width)) if landscape else                 int(WIDTH * (0.28 if idx == 0 else 0.72) - im.width / 2)
            frame.paste(im, (x, HEIGHT - th - 40), im)
    elif kind == "toc":
        d.text((cx, HEIGHT * 0.12), title or "Nội dung video", font=font(76), fill=acc[0], anchor="mm")
        fi = font(46 if landscape else 44, "Bold")
        items = sl.get("items", [])
        cols = 2 if landscape and len(items) > 6 else 1
        per = (len(items) + cols - 1) // cols
        for i, it in enumerate(items):
            col, row = divmod(i, per)
            x0 = WIDTH * (0.12 + 0.42 * col) if landscape else 90
            y0 = HEIGHT * 0.24 + row * (86 if landscape else 110)
            if lt < 0.25 * i:
                continue
            d.ellipse([x0, y0 - 30, x0 + 60, y0 + 30], fill=acc[i % len(acc)])
            d.text((x0 + 30, y0), str(i + 1), font=font(34), fill="#1E1A2B", anchor="mm")
            d.text((x0 + 84, y0), it, font=fi, fill=st.text, anchor="lm")
    elif kind == "chapter":
        n = sl.get("number", "")
        fn = font(64, "Bold")
        tag = f"PHẦN {n}" if n else "PHẦN MỚI"
        w = d.textlength(tag, font=fn) + 90
        y = HEIGHT * 0.36 + (1 - e) * 80
        d.rounded_rectangle([cx - w / 2, y - 55, cx + w / 2, y + 55], 55, fill=acc[(int(n or 0)) % len(acc)])
        d.text((cx, y), tag, font=fn, fill="#1E1A2B", anchor="mm")
        ft = font(92)
        yy = y + 150
        for ln in _wrap(d, title, ft, WIDTH - 200)[:2]:
            d.text((cx, yy), ln, font=ft, fill=st.text, anchor="mm", stroke_width=6, stroke_fill="#000000")
            yy += 110
    elif kind == "recap":
        d.text((cx, HEIGHT * 0.09), title or "ÔN NHANH", font=font(72), fill=acc[0], anchor="mm")
        items = sl.get("items", [])
        spans = s.native_spans or []
        cur = next((i for i, (a, b) in enumerate(spans) if a <= lt <= b + 0.6), -1)
        rowh = min(150, int(HEIGHT * 0.78 / max(1, len(items))))
        for i, it in enumerate(items):
            y = HEIGHT * 0.17 + i * rowh
            on = i == cur
            box = [WIDTH * 0.06, y, WIDTH * 0.94, y + rowh - 16]
            d.rounded_rectangle(box, 26, fill="#FFFFFF" if on else "#2A3B55", outline=acc[i % len(acc)], width=6)
            ff = cjk_font(lang, min(60, rowh // 2))
            d.text((box[0] + 40, y + (rowh - 16) / 2), it.get("foreign", ""), font=ff,
                   fill="#1E1A2B" if on else st.text, anchor="lm")
            d.text((box[2] - 40, y + (rowh - 16) / 2), it.get("meaning", ""), font=font(min(40, rowh // 3), "Bold"),
                   fill="#264653" if on else "#C9D1DC", anchor="rm")
    return frame


MARK_COLORS = {"sai": "#E63946", "dung": "#2A9D8F", "tu": "#3A86FF", "thoai": "#8E6CEF",
               "quiz_q": "#F4A261", "quiz_a": "#2A9D8F"}


def _fit_font(d, text, lang, max_w, start, min_size=48, max_lines=2):
    size = start
    while size > min_size:
        f = cjk_font(lang, size)
        lines = _wrap(d, text, f, max_w) if " " in text else _wrap_chars(d, text, f, max_w)
        if len(lines) <= max_lines:
            return f, lines, size
        size -= 8
    f = cjk_font(lang, min_size)
    return f, (_wrap(d, text, f, max_w) if " " in text else _wrap_chars(d, text, f, max_w))[:max_lines], min_size


def _wrap_chars(d, text, f, max_w):
    """Xuống dòng theo ký tự (chữ Hán/Hàn không có khoảng trắng)."""
    lines, cur = [], ""
    for ch in text:
        if d.textlength(cur + ch, font=f) > max_w and cur and ch not in "。，！？、：；.,!?)）」":
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    return lines + ([cur] if cur else [])


def _badge(frame, text, st):
    """Nhãn tên series góc trên (VD 'NGÀY 7/30'); phần 'Tập trước/Tập sau' thành dải chữ ở đáy màn hình."""
    d = ImageDraw.Draw(frame)
    parts = text.split(" · ", 1)
    head, note = (parts[0], parts[1] if len(parts) > 1 else "")
    if head.startswith(("Tập trước", "Tập sau")):
        head, note = "", text
    if head:
        fb = font(36)
        while d.textlength(head, font=fb) > WIDTH * 0.3 and fb.size > 26:
            fb = fb.font_variant(size=fb.size - 2)
        w = d.textlength(head, font=fb) + 50
        y = 8 if HEIGHT > WIDTH else 24
        d.rounded_rectangle([24, y, 24 + w, y + 56], 28, fill=st.accents[0], outline="#1E1A2B", width=4)
        d.text((24 + w / 2, y + 28), head, font=fb, fill="#1E1A2B", anchor="mm")
    if note:
        fn = font(42)
        lines = _wrap(d, note, fn, WIDTH - 140)[:2]
        h = 30 + len(lines) * 54
        y1 = HEIGHT - 40
        d.rounded_rectangle([40, y1 - h, WIDTH - 40, y1], 30, fill="#1E1A2B", outline=st.accents[0], width=5)
        for i, ln in enumerate(lines):
            d.text((WIDTH // 2, y1 - h + 15 + 27 + i * 54), ln, font=fn, fill="#FFFFFF", anchor="mm")


def _draw_card(frame, s, lt, k, st):
    c = s.card
    d = ImageDraw.Draw(frame)
    mark = c.get("mark", "tu")
    col = MARK_COLORS.get(mark, "#3A86FF")
    x0, y0, x1, y1 = CARD_BOX
    e = _ease_out(min(1.0, (k + 1) / POP_FRAMES))
    dy = int((1 - e) * 60)
    d.rounded_rectangle([x0 + 8, y0 + 12 + dy, x1 + 8, y1 + 12 + dy], 40, fill="#00000040")
    d.rounded_rectangle([x0, y0 + dy, x1, y1 + dy], 40, fill="#FFFFFF", outline=col, width=12)
    # huy hiệu ✗ / ✓ / ?
    bx, by, r = x0 + 20, y0 + 20 + dy, 46
    if mark in ("sai", "dung", "quiz_q"):
        d.ellipse([bx - r, by - r, bx + r, by + r], fill=col, outline="#FFFFFF", width=6)
        if mark == "sai":
            d.line([bx - 20, by - 20, bx + 20, by + 20], fill="#FFFFFF", width=12)
            d.line([bx - 20, by + 20, bx + 20, by - 20], fill="#FFFFFF", width=12)
        elif mark == "dung":
            d.line([bx - 22, by, bx - 6, by + 18, bx + 24, by - 18], fill="#FFFFFF", width=12, joint="curve")
        else:
            d.text((bx, by), "?", font=font(64), fill="#FFFFFF", anchor="mm")
    speaking = any(a <= lt <= b for a, b in s.native_spans)
    # nhãn góc thẻ: "#1", "Câu 2/3", "Từ 3/5"
    if c.get("tag"):
        ft = font(40)
        w = int(d.textlength(c["tag"], font=ft)) + 48
        d.rounded_rectangle([x1 - w - 10, y0 + dy - 28, x1 + 10, y0 + dy + 34], 30, fill=col, outline="#FFFFFF", width=5)
        d.text((x1 - w / 2, y0 + dy + 3), c["tag"], font=ft, fill="#FFFFFF", anchor="mm")
    # luyện nói theo: sau khi giọng mẫu đọc xong → nhắc người xem nói
    if c.get("shadow") and s.native_spans and lt > s.native_spans[-1][1]:
        fs = font(48)
        msg = "🎤 ĐẾN LƯỢT BẠN NÓI!".replace("🎤 ", "")
        w = int(d.textlength(msg, font=fs)) + 80
        pulse = 1 + 0.04 * math.sin(lt * 8)
        cxm, cym = (x0 + x1) // 2, y1 + dy + 10
        hw, hh = w * pulse / 2, 42 * pulse
        d.rounded_rectangle([cxm - hw, cym - hh, cxm + hw, cym + hh], 40, fill="#E63946", outline="#FFFFFF", width=6)
        d.text((cxm, cym), msg, font=fs, fill="#FFFFFF", anchor="mm")
    lang = c.get("lang", "en")
    inner = x1 - x0 - 100
    cx = (x0 + x1) // 2
    opts_ = c.get("options") or []
    # đáp án A/B/C nằm TRONG thẻ: 1 hàng 3 ô, hoặc xếp dọc từng dòng nếu có đáp án dài
    fo = (cjk_font(lang, 46) if lang in ("zh", "ko") else font(46)) if opts_ else None
    col_w = (x1 - x0 - 50 - 16 * (len(opts_) - 1)) / max(1, len(opts_))
    stack = bool(opts_) and any(d.textlength(f"{'ABCD'[i]}. {o}", font=fo) > col_w - 30 for i, o in enumerate(opts_))
    opt_h = (len(opts_) * 74 + 6 if stack else 130) if opts_ else 0
    avail = (y1 - y0) - 70 - opt_h              # chiều cao dành cho chữ (trừ lề trên/dưới)
    # tầng 1: chữ ngoại ngữ — thu nhỏ dần tới khi cả 3 tầng vừa khít trong thẻ
    start = 108
    while True:
        ff, lines, size = _fit_font(d, c.get("foreign", ""), lang, inner, start, min_size=min(48, start))
        fr, fm = roman_font(max(32, int(size * 0.4))), font(max(38, int(size * 0.45)))
        rl, ml = int(fr.size * 1.3), int(fm.size * 1.25)
        roman_lines = _wrap(d, c.get("roman", ""), fr, inner)[:2] if c.get("roman") else []
        mean_lines = _wrap(d, c.get("meaning", ""), fm, inner)[:2] if c.get("meaning") else []
        block = len(lines) * size * 1.12 + len(roman_lines) * rl + 24 + len(mean_lines) * ml
        if block <= avail or start <= 56:
            break
        start -= 8
    y = y0 + dy + 35 + max(0, (avail - block) / 2)
    fcol = col if speaking else "#1E1A2B"
    if mark == "quiz_q" and not c.get("teaser"):
        pause_start = s.caption_span[-1][1] if s.caption_span else 0
        if lt > pause_start:
            n = 3 - int((lt - pause_start) / 1.0)
            lines = [str(max(1, n))]
            ff = font(150)
        fcol = col
    for ln in lines:
        d.text((cx, y + size // 2), ln, font=ff, fill=fcol, anchor="mm")
        if mark == "sai":
            w = d.textlength(ln, font=ff)
            d.line([cx - w / 2 - 10, y + size // 2, cx + w / 2 + 10, y + size // 2], fill=col, width=10)
        y += int(size * 1.12)
    # tầng 2: phiên âm
    for ln in roman_lines:
        d.text((cx, y + rl // 2), ln, font=fr, fill="#6C757D", anchor="mm")
        y += rl
    # tầng 3: nghĩa tiếng Việt
    y += 24
    for ln in mean_lines:
        d.text((cx, y + ml // 2), ln, font=fm, fill="#264653", anchor="mm")
        y += ml
    # quiz trắc nghiệm A/B/C: hàng lựa chọn ở đáy thẻ, đáp án đúng sáng xanh khi công bố
    if opts_:
        n = len(opts_)
        for i, o in enumerate(opts_):
            if stack:
                ox, oy, ow, oh = x0 + 25, y1 + dy - opt_h - 10 + i * 74, x1 - x0 - 50, 66
            else:
                ox, oy, ow, oh = x0 + 25 + i * (col_w + 16), y1 + dy - opt_h - 10, col_w, 110
            right = c.get("reveal") and i == c.get("answer", -1)
            wrong = c.get("reveal") and i == c.get("picked", -1) and not right
            fill = "#2A9D8F" if right else ("#E63946" if wrong else "#FFFFFF")
            d.rounded_rectangle([ox, oy, ox + ow, oy + oh], 26, fill=fill, outline="#1E1A2B", width=5)
            txt = f"{'ABCD'[i]}. {o}"
            fi = fo
            while d.textlength(txt, font=fi) > ow - 30 and fi.size > 30:
                fi = fi.font_variant(size=fi.size - 2)
            d.text((ox + ow / 2, oy + oh / 2), txt, font=fi, fill="#FFFFFF" if (right or wrong) else "#1E1A2B",
                   anchor="mm")


def render(project: Project, out: Path, opts: RenderOptions, audio: Path,
           progress: Optional[Callable[[float, str], None]] = None) -> Path:
    st = STYLES.get(opts.style, STYLES["infographic"])
    set_layout(opts.layout)
    bw, bh = IMG_BOX[2] - IMG_BOX[0], IMG_BOX[3] - IMG_BOX[1]
    mask = _rounded_mask(bw, bh)
    total = sum(s.duration for s in project.scenes)
    n_frames = int(total * FPS) + 1
    f_over, f_cap, f_wm = font(118), font(76), font(40, "Bold")

    cmd = [FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-", "-i", str(audio)]
    if opts.music and Path(opts.music).exists():
        cmd += ["-stream_loop", "-1", "-i", opts.music, "-filter_complex",
                f"[2:a]volume={opts.music_volume}[m];[1:a][m]amix=inputs=2:duration=first[a]",
                "-map", "0:v", "-map", "[a]"]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]
    cmd += [*encoder_args(opts.quality), "-g", str(FPS * 2), "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", str(out)]
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    starts, t = [], 0.0
    for s in project.scenes:
        starts.append(t)
        t += s.duration
    cache, actors = {}, {}
    frame_idx = 0
    try:
        for si, s in enumerate(project.scenes):
            if si not in cache and not s.slide:
                cache.clear()
                cache[si] = _prepare(s.image, bw, bh, opts.zoom)
            src = cache.get(si)
            if s.caption_span and isinstance(s.caption_span[0], list):   # bài học: phụ đề theo từng đoạn Việt
                words = []
                for a0, b0, txt in s.caption_span:
                    words += [(w, a + a0, b + a0) for w, a, b in _word_times(txt, b0 - a0)]
            else:
                words = _word_times(s.text, s.duration)
            actor, actor2, env = None, None, None
            if s.character:
                actor = actors.setdefault(s.character, charmod.load(s.character))
                env = charmod.mouth_envelope(s.audio, FPS) if s.audio else None
            if s.character2:
                actor2 = actors.setdefault(s.character2, charmod.load(s.character2))
            chunks = _caption_chunks(words)
            scene_frames = int(round((starts[si] + s.duration) * FPS)) - frame_idx
            for k in range(scene_frames):
                lt = k / FPS
                if s.slide:
                    from .formats_extra import EXTRA_KINDS, draw_extra
                    if s.slide.get("kind") in EXTRA_KINDS:
                        frame = draw_extra(WIDTH, HEIGHT, s, lt, k, actors)
                        if s.overlay:
                            _badge(frame, s.overlay, st)
                    else:
                        frame = _slide_frame(s, lt, k, st, actors)
                    d = ImageDraw.Draw(frame)
                    if opts.watermark:
                        d.text(WM, opts.watermark, font=f_wm, fill=st.text, anchor="mm")
                    if opts.progress_bar:
                        g = (frame_idx + 1) / n_frames
                        d.rectangle([0, HEIGHT - 18, int(WIDTH * g), HEIGHT], fill=st.accents[0])
                    proc.stdin.write(frame.tobytes())
                    frame_idx += 1
                    if progress and frame_idx % 30 == 0:
                        progress(frame_idx / n_frames, f"Dựng khung hình {frame_idx}/{n_frames}")
                    continue
                frame = Image.new("RGB", (WIDTH, HEIGHT), st.bg)
                d = ImageDraw.Draw(frame)
                # --- hình: Ken Burns (zoom chậm + trôi nhẹ), xen kẽ hướng theo cảnh
                p = lt / max(s.duration, 0.01)
                z = opts.zoom * (p if si % 2 == 0 else 1 - p)
                cw, ch = int(bw * (1 + z)), int(bh * (1 + z))
                scale = src.width / (bw * (1 + opts.zoom))
                cx = (src.width - cw * scale) / 2 + (8 if si % 3 == 0 else -8) * p * scale
                cy = (src.height - ch * scale) / 2
                cx = min(max(cx, 0), src.width - cw * scale)
                cy = min(max(cy, 0), src.height - ch * scale)
                crop = src.crop((int(cx), int(cy), int(cx + cw * scale), int(cy + ch * scale))).resize((bw, bh))
                # hiệu ứng "pop" đầu cảnh
                if k < POP_FRAMES:
                    e = _ease_out((k + 1) / POP_FRAMES)
                    sw, sh = int(bw * (0.86 + 0.14 * e)), int(bh * (0.86 + 0.14 * e))
                    small = crop.resize((sw, sh))
                    frame.paste(small, (IMG_BOX[0] + (bw - sw) // 2, IMG_BOX[1] + (bh - sh) // 2),
                                _rounded_mask(sw, sh))
                else:
                    frame.paste(crop, IMG_BOX[:2], mask)
                env1, env2 = {1: (env, None), 2: (None, env)}.get(s.speaker, (None, None))
                if s.item in propmod.PROPS:
                    _draw_focus_item(frame, s, lt, k, st)
                if actor2 is not None:
                    _draw_actor(frame, actor2, s, lt, env2, k, st, action=s.action2 or "dung",
                                expression=s.expression2, position="phai", facing_left=True, prop="")
                if actor is not None:
                    _draw_actor(frame, actor, s, lt, env1, k, st,
                                position="trai" if actor2 is not None else s.position)
                # --- chữ lớn trên cùng (bật lên)
                if s.card:
                    _draw_card(frame, s, lt, k, st)
                    if s.overlay and not opts.extra.get("hide_overlay"):
                        _badge(frame, s.overlay, st)      # đã có thẻ nội dung → tên series chỉ là nhãn nhỏ
                if s.overlay and not opts.extra.get("hide_overlay") and not s.card:
                    e = _ease_out(min(1.0, (k + 1) / POP_FRAMES))
                    size = max(40, int(118 * (0.6 + 0.4 * e)))
                    fo = f_over if size == 118 else font(size)
                    head, _, note = s.overlay.partition(" · ")
                    if head.startswith(("Tập trước", "Tập sau")):
                        head, note = "", s.overlay
                    if note:
                        _badge(frame, note, st)
                    lines = _wrap(d, head.upper(), fo, OVERLAY_W)[:2]
                    for li, line in enumerate(lines):
                        y = OVERLAY[1] + li * size * 1.08 - (len(lines) - 1) * size * 0.54
                        d.text((OVERLAY[0], y), line, font=fo, fill=st.accents[si % len(st.accents)],
                               anchor="mm", stroke_width=8, stroke_fill="#000000")
                # --- phụ đề karaoke
                in_span = not s.caption_span or not isinstance(s.caption_span[0], list) or \
                    any(a0 <= lt <= b0 + 0.3 for a0, b0, _ in s.caption_span)
                if opts.captions and chunks and in_span:
                    chunk = next((c for c in chunks if c[-1][2] >= lt), chunks[-1])
                    line = " ".join(w for w, _, _ in chunk)
                    lines = _wrap(d, line, f_cap, CAPTION_W)
                    y = CAPTION_Y
                    wi = 0
                    for ln in lines:
                        x = CAPTION_X - d.textlength(ln, font=f_cap) / 2
                        for w in ln.split():
                            _, a, b = chunk[wi]
                            col = st.caption_highlight if a <= lt < b + 0.05 else st.text
                            d.text((x, y), w, font=f_cap, fill=col, stroke_width=7, stroke_fill="#000000")
                            x += d.textlength(w + " ", font=f_cap)
                            wi += 1
                        y += 96
                # --- tên kênh + thanh tiến trình
                if opts.watermark:
                    d.text(WM, opts.watermark, font=f_wm, fill=st.text, anchor="mm")
                if opts.progress_bar:
                    g = (frame_idx + 1) / n_frames
                    d.rectangle([0, HEIGHT - 18, WIDTH, HEIGHT], fill="#00000055")
                    d.rectangle([0, HEIGHT - 18, int(WIDTH * g), HEIGHT], fill=st.accents[0])
                proc.stdin.write(frame.tobytes())
                frame_idx += 1
                if progress and frame_idx % 30 == 0:
                    progress(frame_idx / n_frames, f"Dựng khung hình {frame_idx}/{n_frames}")
    finally:
        proc.stdin.close()
        proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg lỗi khi ghi video")
    return out
