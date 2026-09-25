"""Màn hình đặc biệt cho các định dạng dạy ngoại ngữ mới (vẽ toàn khung, dọc hoặc ngang).

  chat       📱 Khung nhắn tin giả lập (KakaoTalk / WeChat / iMessage) — bong bóng + "đang soạn tin…"
  compare    🌏 So sánh 3 ngôn ngữ — 3 thẻ Anh/Trung/Hàn, thẻ đang đọc phát sáng
  anatomy    🔤 Mổ xẻ chữ/từ — tách chữ Hàn thành phụ âm + nguyên âm, chữ Hán thành bộ, âm Hán-Việt
  pron       🎤 Phát âm cận cảnh — khẩu hình miệng + đường cong thanh điệu (tiếng Trung) có chấm chạy theo giọng
  breakdown  🎬 Câu thoại phim / lời bài hát — khung phụ đề điện ảnh + tách từng từ kèm nghĩa
Kèm: âm thanh hiệu ứng (đúng/sai/tích tắc) và nhạc nền dịu (tự tạo, không bản quyền) cho luyện nghe.
"""
import math
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .config import ASSETS
from .images import _wrap, font
from .langs import cjk_font, roman_font

INK = "#1E1A2B"
LANG_NAME = {"en": "TIẾNG ANH", "zh": "TIẾNG TRUNG", "ko": "TIẾNG HÀN", "vi": "TIẾNG VIỆT"}
LANG_COLOR = {"en": "#3A86FF", "zh": "#E63946", "ko": "#8E6CEF"}


def _ease(t):
    return 1 - (1 - min(1.0, max(0.0, t))) ** 3


def _active(s, lt):
    """Chỉ số đoạn giọng bản ngữ đang phát (theo thứ tự) hoặc -1."""
    for i, (a, b) in enumerate(s.native_spans or []):
        if a <= lt <= b + 0.15:
            return i
    return -1


# ======================= 📱 CHAT =======================
CHAT_APPS = {
    "kakao": {"bg": "#B2C7D9", "bar": "#A9BDCE", "me": "#FEE500", "me_text": INK, "other": "#FFFFFF", "name": "KakaoTalk"},
    "wechat": {"bg": "#EDEDED", "bar": "#F7F7F7", "me": "#95EC69", "me_text": INK, "other": "#FFFFFF", "name": "WeChat"},
    "imessage": {"bg": "#FFFFFF", "bar": "#F2F2F7", "me": "#0A84FF", "me_text": "#FFFFFF", "other": "#E9E9EB",
                 "name": "Messages"},
}


def draw_chat(W, H, data, s, lt, k, actors):
    app = CHAT_APPS.get(data.get("app", "kakao"), CHAT_APPS["kakao"])
    lang = data.get("lang", "ko")
    frame = Image.new("RGB", (W, H), "#1B2A41")
    d = ImageDraw.Draw(frame)
    landscape = W > H
    # khung điện thoại
    pw = int(H * 0.52) if landscape else int(W * 0.9)
    ph = int(H * 0.92) if landscape else int(H * 0.66)
    px = (W - pw) // 2 if not landscape else int(W * 0.08)
    py = (H - ph) // 2 if landscape else int(H * 0.075)
    d.rounded_rectangle([px - 14, py - 14, px + pw + 14, py + ph + 14], 60, fill="#111111")
    d.rounded_rectangle([px, py, px + pw, py + ph], 48, fill=app["bg"])
    d.rounded_rectangle([px, py, px + pw, py + 150], 48, fill=app["bar"])
    d.rectangle([px, py + 100, px + pw, py + 150], fill=app["bar"])
    d.text((px + pw // 2, py + 90), data.get("title", app["name"]), font=font(46), fill=INK, anchor="mm")
    msgs = data.get("messages", [])
    fm, fr, fv = cjk_font(lang, 64), roman_font(34), font(38, "Bold")
    # xếp tin nhắn từ dưới lên, tin mới nhất ở đáy
    blocks, maxw = [], pw * 0.72
    for m in msgs:
        lines = _wrap(d, m["text"], fm, maxw - 60) if " " in m["text"] else [m["text"]]
        h = len(lines) * 78 + (48 if m.get("meaning") else 0) + 44
        blocks.append((m, lines, h + (44 if m.get("roman") else 0)))
    y = py + ph - 40
    if data.get("typing"):
        y -= 90
        side_me = data["typing"] == "me"
        bx = px + pw - 190 if side_me else px + 40
        d.rounded_rectangle([bx, y + 10, bx + 150, y + 76], 34, fill=app["me"] if side_me else app["other"])
        for j in range(3):
            r = 9 + 4 * (0.5 + 0.5 * math.sin(lt * 8 - j))
            cx = bx + 40 + j * 36
            d.ellipse([cx - r, y + 43 - r, cx + r, y + 43 + r], fill="#888888")
    # tin mới nhất ở đáy như app thật, nhưng khi còn ít tin thì xếp từ trên xuống (không để trống nửa màn hình)
    used = sum(h + 18 for _, _, h in blocks)
    if used < y - (py + 170):
        y = py + 170 + used
    for idx in range(len(blocks) - 1, -1, -1):
        m, lines, h = blocks[idx]
        y -= h + 18
        if y < py + 170:
            break
        me = m.get("side") == "me"
        tw = max(d.textlength(ln, font=fm) for ln in lines) + 60
        tw = max(tw, d.textlength(m.get("meaning", ""), font=fv) + 60) if m.get("meaning") else tw
        tw = min(tw, maxw)
        newest = idx == len(blocks) - 1
        e = _ease((k + 1) / 8) if newest else 1
        bx = px + pw - 40 - tw if me else px + 40
        by = y + (1 - e) * 40
        col = app["me"] if me else app["other"]
        hb = h - (44 if m.get("roman") else 0)
        d.rounded_rectangle([bx, by, bx + tw, by + hb], 34, fill=col)
        tc = app["me_text"] if me else INK
        ty = by + 24
        for ln in lines:
            d.text((bx + 30, ty), ln, font=fm, fill=tc)
            ty += 78
        if m.get("meaning"):
            d.text((bx + 30, ty + 2), m["meaning"], font=fv, fill=tc if me else "#555555")
        if m.get("roman"):
            d.text((bx + 10 if not me else bx + tw - 10, by + hb + 6), m["roman"], font=fr, fill="#33475B",
                   anchor="la" if not me else "ra")
    if not landscape and actors is not None:
        _cast_bottom(frame, W, H, data, lt, actors, 0.2)
    # nhân vật đang cầm điện thoại ở bên cạnh (khung ngang)
    if landscape and data.get("cast"):
        from . import character as charmod
        for i, key in enumerate(data["cast"][:2]):
            a = actors.setdefault(key, charmod.load(key))
            talking = (i == 0 and data.get("speaker") == 1) or (i == 1 and data.get("speaker") == 2)
            from . import props as propmod
            im = a.render("chi_tay" if talking else "dung", lt, mouth_open=0.5 + 0.5 * math.sin(lt * 18) if talking else 0,
                          flip=bool(i), prop=propmod.get("dien_thoai"))
            im = im.crop(im.getbbox())
            th = int(H * 0.62)
            im = im.resize((int(im.width * th / im.height), th), Image.LANCZOS)
            x = int(W * (0.62 + 0.2 * i)) - im.width // 2
            frame.paste(im, (x, H - th - 30), im)
    return frame


# ======================= 🌏 SO SÁNH 3 NGÔN NGỮ =======================
def draw_compare(W, H, data, s, lt, k):
    frame = Image.new("RGB", (W, H), "#1B2A41")
    d = ImageDraw.Draw(frame)
    landscape = W > H
    ty = int(H * (0.1 if landscape else 0.1))
    d.text((W // 2, ty), f"“{data.get('meaning', '')}”", font=font(80 if landscape else 76), fill="#FFB400",
           anchor="mm")
    d.text((W // 2, ty + 80), "nói thế nào trong 3 thứ tiếng?", font=font(40, "Bold"), fill="#FFFFFF",
           anchor="mm")
    items = data.get("items", [])
    act = _active(s, lt)
    n = max(1, len(items))
    for i, it in enumerate(items):
        if landscape:
            cw, ch = (W - 160) // n - 30, int(H * 0.62)
            x0, y0 = 80 + i * (cw + 30 + 30 // n), int(H * 0.25)
        else:
            cw, ch = W - 120, int(H * 0.22)
            x0, y0 = 60, int(H * 0.2) + i * (ch + 40)
        on = i == act
        col = LANG_COLOR.get(it["lang"], "#3A86FF")
        e = _ease((k - i * 6) / 10)
        if e <= 0:
            continue
        grow = 12 if on else 0
        d.rounded_rectangle([x0 - grow, y0 - grow, x0 + cw + grow, y0 + ch + grow], 40,
                            fill="#FFFFFF" if on or act < 0 else "#DDE3EA", outline=col, width=14 if on else 8)
        d.rounded_rectangle([x0 + 30, y0 - 32, x0 + 30 + d.textlength(LANG_NAME[it["lang"]], font=font(34)) + 40,
                             y0 + 30], 24, fill=col)
        d.text((x0 + 50, y0 - 1), LANG_NAME[it["lang"]], font=font(34), fill="#FFFFFF", anchor="lm")
        ff = cjk_font(it["lang"], 92 if landscape else 96)
        while d.textlength(it["foreign"], font=ff) > cw - 60 and ff.size > 40:
            ff = cjk_font(it["lang"], ff.size - 8)
        d.text((x0 + cw // 2, y0 + ch * 0.45), it["foreign"], font=ff, fill=INK, anchor="mm")
        if it.get("roman"):
            d.text((x0 + cw // 2, y0 + ch * 0.76), it["roman"], font=roman_font(46), fill="#6C757D", anchor="mm")
    return frame


# ======================= 🔤 MỔ XẺ CHỮ =======================
def draw_anatomy(W, H, data, s, lt, k, actors=None):
    frame = Image.new("RGB", (W, H), "#F4F1EA")
    d = ImageDraw.Draw(frame)
    lang = data.get("lang", "ko")
    landscape = W > H
    word = data.get("word", "")
    fw = cjk_font(lang, 170 if landscape else 260)
    d.text((W // 2, int(H * (0.15 if landscape else 0.2))), word, font=fw, fill=INK, anchor="mm")
    if data.get("roman"):
        d.text((W // 2, int(H * (0.28 if landscape else 0.29))), data["roman"], font=roman_font(54), fill="#6C757D",
               anchor="mm")
    parts = data.get("parts", [])
    n = max(1, len(parts))
    t_per = max(0.5, (s.duration * 0.35) / n)            # mọi phần hiện xong trước ~40% thời lượng
    y0 = int(H * (0.37 if landscape else 0.35))
    gap = 90                                             # đủ chỗ cho dấu "+" và nhãn không đè nhau
    cw = min(230 if landscape else 250, (W - 120 - (n - 1) * gap) // n)
    total = n * cw + (n - 1) * gap
    x = (W - total) // 2
    cols = ["#FF6B6B", "#4D96FF", "#6BCB77", "#FFD93D", "#B983FF", "#FF9F45"]
    fl = font(40, "Bold")
    lab_h = 0
    for i, p in enumerate(parts):
        e = _ease((lt - 0.4 - i * t_per) / 0.4)
        if e <= 0:
            break
        c = cols[i % len(cols)]
        yy = y0 + (1 - e) * 60
        d.rounded_rectangle([x, yy, x + cw, yy + cw], 30, fill=c, outline=INK, width=6)
        d.text((x + cw // 2, yy + cw * 0.47), p["text"], font=cjk_font(lang, int(cw * 0.6)), fill=INK, anchor="mm")
        lab = _wrap(d, p.get("label", ""), fl, cw + gap - 20)[:2]
        for li, ln in enumerate(lab):
            d.text((x + cw // 2, yy + cw + 40 + li * 50), ln, font=fl, fill=INK, anchor="mm")
        lab_h = max(lab_h, len(lab) * 50)
        if i < n - 1:
            d.text((x + cw + gap // 2, yy + cw // 2), "+", font=font(80), fill=INK, anchor="mm")
        x += cw + gap
    y_note = y0 + cw + 70 + max(lab_h, 50)
    fn = font(46 if landscape else 54)
    for key, label in (("meaning", "Nghĩa"), ("han_viet", "Hán – Việt"), ("tip", "Mẹo nhớ")):
        if data.get(key) and lt > 0.4 + n * t_per:
            txt = f"{label}: {data[key]}"
            for ln in _wrap(d, txt, fn, W - 140)[:2]:
                d.text((W // 2, y_note), ln, font=fn, fill="#264653" if key != "han_viet" else "#E63946",
                       anchor="mm")
                y_note += 58 if landscape else 70
    if not landscape and actors is not None:
        _cast_bottom(frame, W, H, data, lt, actors, 0.22)
    return frame


# ======================= 🎤 PHÁT ÂM =======================
TONE_SHAPES = {1: [(0, 5), (1, 5)], 2: [(0, 3), (1, 5)], 3: [(0, 2), (0.5, 1), (1, 4)], 4: [(0, 5), (1, 1)],
               5: [(0, 3), (1, 3)]}
MOUTH = {"open": (1.0, 1.0), "round": (0.55, 0.9), "spread": (1.25, 0.45), "closed": (1.0, 0.12),
         "neutral": (0.9, 0.55)}


def _tone_numbers(text):
    try:
        from pypinyin import Style, pinyin
        out = []
        for syl in pinyin(text, style=Style.TONE3, neutral_tone_with_five=True):
            t = syl[0]
            out.append(int(t[-1]) if t and t[-1].isdigit() else 5)
        return out
    except Exception:  # noqa: BLE001
        return []


def draw_pron(W, H, data, s, lt, k):
    frame = Image.new("RGB", (W, H), "#FFF8E7")
    d = ImageDraw.Draw(frame)
    lang = data.get("lang", "zh")
    items = data.get("items", [])
    act = _active(s, lt)
    landscape = W > H
    d.text((W // 2, int(H * (0.1 if landscape else 0.095))), data.get("title", "PHÁT ÂM CHUẨN"), font=font(70), fill="#E63946", anchor="mm")
    n = max(1, len(items))
    for i, it in enumerate(items):
        if landscape:
            cw, ch = (W - 120) // n - 24, int(H * 0.68)
            x0, y0 = 60 + i * (cw + 24), int(H * 0.2)
        else:
            cw, ch = W - 100, int(H * 0.8) // n - 24
            x0, y0 = 50, int(H * 0.14) + i * (ch + 24)
        on = i == act
        d.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], 36, fill="#FFFFFF", outline="#E63946" if on else "#CCCCCC",
                            width=12 if on else 6)
        tall = cw < ch * 0.9          # thẻ hẹp (khung ngang 4 mục): chữ ở trên, đồ thị ở dưới
        if tall:
            tx, ys = x0 + cw * 0.5, (0.17, 0.33, 0.42)
            ff = cjk_font(lang, int(min(ch * 0.2, cw * 0.55)))
        else:
            tx, ys = x0 + cw * 0.25, (0.38, 0.72, 0.87)
            ff = cjk_font(lang, int(min(ch * 0.33, cw * 0.4)))
        d.text((tx, y0 + ch * ys[0]), it["text"], font=ff, fill=INK, anchor="mm")
        if it.get("roman"):
            d.text((tx, y0 + ch * ys[1]), it["roman"], font=roman_font(max(40, int(min(ch * 0.12, cw * 0.14)))),
                   fill="#264653", anchor="mm")
        if it.get("meaning"):
            d.text((tx, y0 + ch * ys[2]), it["meaning"], font=font(max(34, int(min(ch * 0.1, cw * 0.11))), "Bold"),
                   fill="#6C757D", anchor="mm")
        # đường thanh điệu (Trung) hoặc khẩu hình miệng: bên phải, hoặc nửa dưới nếu thẻ hẹp
        if tall:
            gx0, gy0, gw, gh = x0 + cw * 0.1, y0 + ch * 0.5, cw * 0.8, ch * 0.36
        else:
            gx0, gy0, gw, gh = x0 + cw * 0.52, y0 + ch * 0.15, cw * 0.42, ch * 0.7
        tones = it.get("tones") or (_tone_numbers(it["text"]) if lang == "zh" else [])
        prog = 0.0
        if on and s.native_spans:
            a, b = s.native_spans[act]
            prog = min(1.0, (lt - a) / max(0.1, b - a))
        if tones:
            for lv in range(1, 6):     # 5 mức cao độ
                yy = gy0 + gh - (lv - 1) / 4 * gh
                d.line([gx0, yy, gx0 + gw, yy], fill="#E9ECEF", width=3)
            seg = gw / len(tones)
            for ti, tn in enumerate(tones[:4]):
                pts = [(gx0 + ti * seg + 16 + px * (seg - 32), gy0 + gh - (py - 1) / 4 * gh)
                       for px, py in TONE_SHAPES.get(tn, TONE_SHAPES[5])]
                d.line(pts, fill="#E63946", width=14, joint="curve")
                d.text((gx0 + ti * seg + seg / 2, gy0 + gh + 30), f"thanh {tn}", font=font(32, "Bold"),
                       fill="#E63946", anchor="mm")
            if on:
                pos = prog * len(tones[:4])
                ti = min(int(pos), len(tones[:4]) - 1)
                shape = TONE_SHAPES.get(tones[ti], TONE_SHAPES[5])
                u = pos - ti
                (x1, y1), (x2, y2) = shape[0], shape[-1]
                py_ = y1 + (y2 - y1) * u
                cx = gx0 + ti * seg + 16 + u * (seg - 32)
                cy = gy0 + gh - (py_ - 1) / 4 * gh
                d.ellipse([cx - 22, cy - 22, cx + 22, cy + 22], fill="#FFB400", outline=INK, width=4)
        else:
            sx, sy = MOUTH.get(it.get("mouth", "neutral"), MOUTH["neutral"])
            talk = 1 + (0.25 * math.sin(lt * 18) if on else 0)
            mw, mh = gw * 0.7 * sx, gh * 0.45 * sy * talk
            cx, cy = gx0 + gw / 2, gy0 + gh / 2
            d.ellipse([cx - gw * 0.48, cy - gh * 0.5, cx + gw * 0.48, cy + gh * 0.5], fill="#F6C9A0", outline=INK,
                      width=6)
            d.ellipse([cx - mw / 2, cy - mh / 2, cx + mw / 2, cy + mh / 2], fill="#8C2B3C", outline=INK, width=6)
            if mh > 40:
                d.chord([cx - mw * 0.35, cy, cx + mw * 0.35, cy + mh / 2], 0, 180, fill="#F28B9B")
            if it.get("tip"):
                for li, ln in enumerate(_wrap(d, it["tip"], font(36, "Bold"), gw)[:2]):
                    d.text((cx, gy0 + gh + 30 + li * 44), ln, font=font(36, "Bold"), fill="#264653", anchor="mm")
    return frame


# ======================= 🎬 CÂU THOẠI / BÀI HÁT =======================
def _cast_bottom(frame, W, H, data, lt, actors, frac=0.3):
    """Hai nhân vật đứng dưới đáy khung (người đang nói chỉ tay, nhép miệng theo giọng)."""
    from . import character as charmod
    cast = [c for c in (data.get("cast") or []) if c]
    for i, key in enumerate(cast[:2]):
        a = actors.setdefault(key, charmod.load(key))
        talking = data.get("speaker") == i + 1
        im = a.render("chi_tay" if talking else "dung", lt,
                      mouth_open=0.5 + 0.5 * math.sin(lt * 18) if talking else 0, flip=bool(i))
        im = im.crop(im.getbbox())
        th = int(H * frac)
        im = im.resize((int(im.width * th / im.height), th), Image.LANCZOS)
        x = int(W * (0.22 + 0.56 * i)) - im.width // 2 if len(cast) > 1 else W // 2 - im.width // 2
        frame.paste(im, (x, H - th - 60), im)


def draw_breakdown(W, H, data, s, lt, k, actors=None):
    frame = Image.new("RGB", (W, H), "#14142B")
    d = ImageDraw.Draw(frame)
    lang = data.get("lang", "ko")
    landscape = W > H
    # khung phim: 2 dải đen + "màn hình" ở giữa
    top = int(H * (0.14 if landscape else 0.13))
    scr_h = int(H * (0.42 if landscape else 0.26))
    d.rectangle([0, top, W, top + scr_h], fill=data.get("scene_color", "#2B2D42"))
    for i in range(6):
        x = int(W * (0.1 + i * 0.16))
        d.ellipse([x - 90, top + scr_h - 140, x + 90, top + scr_h + 40], fill="#1B1D30")
    d.text((W // 2, top - 40), data.get("source", "🎬 CÂU THOẠI HAY").replace("🎬 ", ""), font=font(40, "Bold"),
           fill="#FFB400", anchor="mm")
    sent = data.get("sentence", "")
    fs = cjk_font(lang, 92 if landscape else 88)
    lines = _wrap(d, sent, fs, W - 120) if " " in sent else [sent]
    y = top + scr_h - 30 - len(lines) * 100
    for ln in lines:
        d.text((W // 2, y), ln, font=fs, fill="#FFE66D", anchor="mm", stroke_width=6, stroke_fill="#000000")
        y += 100
    if data.get("meaning"):
        d.text((W // 2, top + scr_h + 70), data["meaning"], font=font(56), fill="#FFFFFF", anchor="mm")
    words = data.get("words", [])
    t_per = max(0.6, s.duration * 0.6 / max(1, len(words)))
    y0 = top + scr_h + (150 if landscape else 180)
    fw, fmn = cjk_font(lang, 76), font(38, "Bold")
    row_h, gap = 190, 24
    # xếp chip thành các hàng rồi căn giữa từng hàng
    rows, cur, cw_ = [], [], 0
    for i, w in enumerate(words):
        bw = max(d.textlength(w["w"], font=fw), d.textlength(w.get("m", ""), font=fmn)) + 70
        if cur and cw_ + bw > W - 120:
            rows.append((cur, cw_ - gap))
            cur, cw_ = [], 0
        cur.append((i, w, bw))
        cw_ += bw + gap
    if cur:
        rows.append((cur, cw_ - gap))
    for r, (row, rw) in enumerate(rows):
        x, yy = (W - rw) / 2, y0 + r * (row_h + 24)
        for i, w, bw in row:
            e = _ease((lt - 0.3 - i * t_per) / 0.35)
            if e <= 0:
                continue
            col = ["#FF6B6B", "#4D96FF", "#6BCB77", "#FFD93D", "#B983FF"][i % 5]
            y1 = yy + (1 - e) * 50
            d.rounded_rectangle([x, y1, x + bw, y1 + row_h], 30, fill=col, outline="#FFFFFF", width=4)
            d.text((x + bw / 2, y1 + 70), w["w"], font=fw, fill=INK, anchor="mm")
            d.text((x + bw / 2, y1 + 150), w.get("m", ""), font=fmn, fill=INK, anchor="mm")
            x += bw + gap
    if not landscape and actors is not None:
        _cast_bottom(frame, W, H, data, lt, actors, 0.3)
    return frame


EXTRA_KINDS = {"chat", "compare", "anatomy", "pron", "breakdown"}


def draw_extra(W, H, s, lt, k, actors):
    sl = s.slide
    kind = sl.get("kind")
    if kind == "chat":
        return draw_chat(W, H, sl, s, lt, k, actors)
    if kind == "compare":
        return draw_compare(W, H, sl, s, lt, k)
    if kind == "anatomy":
        return draw_anatomy(W, H, sl, s, lt, k, actors)
    if kind == "pron":
        return draw_pron(W, H, sl, s, lt, k)
    return draw_breakdown(W, H, sl, s, lt, k, actors)


# ======================= âm thanh hiệu ứng + nhạc nền =======================
from .tts import SR  # cùng tần số lấy mẫu với giọng đọc để ghép nối không lệch


def _write(path: Path, x: np.ndarray, sr=SR):
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def sfx(name: str, out: Path) -> float:
    """Âm thanh hiệu ứng tổng hợp (không bản quyền): dung | sai | tick | whoosh | pop."""
    def tone(f, dur, vol=0.35, decay=6.0):
        t = np.arange(int(SR * dur)) / SR
        return vol * np.sin(2 * np.pi * f * t) * np.exp(-decay * t)
    if name == "dung":
        x = np.concatenate([tone(880, 0.12), tone(1318, 0.35)])
    elif name == "sai":
        t = np.arange(int(SR * 0.45)) / SR
        x = 0.25 * np.sign(np.sin(2 * np.pi * 140 * t)) * np.exp(-3 * t)
    elif name == "tick":
        x = tone(1500, 0.06, 0.3, 40)
    elif name == "pop":
        x = tone(600, 0.1, 0.35, 30)
    else:  # whoosh
        n = int(SR * 0.35)
        x = np.random.default_rng(0).normal(0, 0.15, n) * np.hanning(n)
    _write(out, x)
    return len(x) / SR


def ambient_music(out: Path, seconds: int = 120) -> Path:
    """Nhạc nền dịu (pad hợp âm C–Am–F–G chậm) để luyện nghe/ngủ. Tự tạo nên không vướng bản quyền."""
    if out.exists():
        return out
    chords = [(261.6, 329.6, 392.0), (220.0, 261.6, 329.6), (174.6, 220.0, 261.6), (196.0, 246.9, 293.7)]
    seg = 8.0
    t = np.arange(int(SR * seg)) / SR
    env = np.minimum(1, np.minimum(t / 2.0, (seg - t) / 2.0))
    parts = []
    for i in range(int(math.ceil(seconds / seg))):
        c = chords[i % len(chords)]
        x = sum(np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2 * t + 0.3) for f in c) / 6
        parts.append(x * env * 0.5)
    _write(out, np.concatenate(parts))
    return out


MUSIC_DIR = ASSETS / "music"
