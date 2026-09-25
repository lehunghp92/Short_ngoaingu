"""Dàn nhân vật GỐC của kênh — vẽ vector phẳng bằng code, dùng chung khung xương (rig).

Nhân vật dẫn chuyện: "Bơ" — đầu tròn to, tóc xoăn 1 lọn dựng đứng, kính tròn, áo hoodie xanh ngọc
có dây rút vàng. Nhân vật phụ thay đầu/tóc/áo/phụ kiện trên CÙNG bộ khớp → dùng chung mọi động tác.
Chạy: python -m studio.cast   (tạo lại toàn bộ assets/characters/* và model sheet)
"""
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from PIL import Image, ImageDraw

from .character import CHAR_DIR

SS = 3            # vẽ ở độ phân giải gấp 3 rồi thu nhỏ → nét mượt (khử răng cưa)
HD = 1.5          # asset lưu ở 1.5x toạ độ thiết kế → nhân vật cao ~1080 px, sắc nét ở video Full-HD
LINE = "#1E1A2B"
LW = 7            # độ dày nét viền (px sau khi thu nhỏ)


def _darker(hex_color: str, k: float = 0.82) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (int(r * k), int(g * k), int(b * k))


def _canvas(w: int, h: int):
    im = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def _save(im: Image.Image, path: Path) -> None:
    w, h = round(im.width / SS * HD), round(im.height / SS * HD)
    im.resize((w, h), Image.LANCZOS).save(path)


def S(*v):
    """Nhân toạ độ với hệ số siêu lấy mẫu."""
    return [x * SS for x in v]


@dataclass
class Look:
    """Ngoại hình một nhân vật — chỉ cần đổi các trường này để có nhân vật mới."""
    key: str
    name: str
    skin: str = "#F6C9A0"
    hair: str = "#3B2A20"
    hair_style: str = "lon_xoan"          # lon_xoan | toc_bac | duoi_ngua | hoi | ngan
    top: str = "#1FA7A0"                   # màu áo
    top_style: str = "hoodie"              # hoodie | ao_blouse | quan_phuc | ao_choang | ao_thun
    pants: str = "#2E3A59"
    shoes: str = "#F2F2F2"
    glasses: bool = False
    hat: str = ""                          # "" | mu_sat | vuong_mien | mu_len
    beard: bool = False
    accent: str = "#FFC23C"                # màu điểm nhấn (dây rút, huy hiệu...)
    build: str = "thuong"                  # thuong | to_con (vạm vỡ) | nho (trẻ em)
    gender: str = "nam"                    # nam | nu — chọn giọng bản ngữ phù hợp
    role: str = ""                         # vai trò gợi ý (hiển thị trong app / prompt LLM)
    extra: dict = field(default_factory=dict)   # tie, apron, stethoscope, lashes, iris, scarf...


CAST = [
    # ----- dàn chính -----
    Look("bo", "Bơ", hair="#4A2F23", glasses=True, role="người dẫn chuyện / người học", extra={"iris": "#4E342E"}),
    Look("mai", "Mai", skin="#F8D2B0", hair="#3A2622", hair_style="duoi_ngua", top="#FF6F61", top_style="ao_thun",
         pants="#34427A", accent="#FFD166", gender="nu", role="cô bạn giỏi ngoại ngữ / người giảng",
         extra={"lashes": True, "iris": "#6B4226"}),
    Look("giao_su", "Giáo sư", skin="#F1C7A5", hair="#E8E8E8", hair_style="toc_bac", top="#FFFFFF",
         top_style="ao_blouse", pants="#4A4E69", glasses=True, beard=True, accent="#5B8DEF", role="khoa học"),
    Look("linh", "Người lính", skin="#C98E63", hair="#2B2B2B", hair_style="ngan", top="#5E7D3A",
         top_style="quan_phuc", pants="#4B5E2E", shoes="#3A2F25", hat="mu_sat", accent="#C9B458", role="lịch sử"),
    Look("vua", "Nhà vua", skin="#F3CDA8", hair="#8A5A2B", hair_style="ngan", top="#B3263E", top_style="ao_choang",
         pants="#6B1F2E", shoes="#3A2F25", hat="vuong_mien", beard=True, accent="#F5C542", role="lịch sử, quyền lực"),
    Look("ong_gia", "Ông cụ", skin="#E9C19E", hair="#D9D9D9", hair_style="hoi", top="#8D6E63", top_style="ao_thun",
         pants="#5D4037", shoes="#3E2723", beard=True, glasses=True, accent="#BCAAA4", role="người lớn tuổi"),
    # ----- 15 nhân vật mới: đời sống, công việc, học tập, thể thao, du lịch -----
    Look("ong_chu", "Ông chủ", skin="#F0C8A0", hair="#2E2E2E", hair_style="ngan", top="#2B3A55", top_style="vest",
         pants="#2B3A55", shoes="#1E1E1E", accent="#C0392B", extra={"tie": "#C0392B", "iris": "#3E2723"},
         role="công sở, phỏng vấn, đàm phán"),
    Look("co_tap_hoa", "Cô tạp hoá", skin="#EFC29B", hair="#4B2E24", hair_style="toc_bui", top="#7FB069",
         top_style="tap_de", pants="#5C4B51", gender="nu", extra={"apron": "#F4A261", "lashes": True},
         role="mua sắm, mặc cả, chợ"),
    Look("co_giao", "Cô giáo", skin="#F6D0AE", hair="#2C1B18", hair_style="toc_dai", top="#FFFFFF",
         top_style="ao_blouse", pants="#3D5A80", glasses=True, gender="nu", accent="#EE6C4D",
         extra={"lashes": True}, role="trường học, ngữ pháp"),
    Look("ban_gym", "Bạn tập gym", skin="#D9A066", hair="#1F1F1F", hair_style="toc_dung", top="#E63946",
         top_style="ao_ba_lo", pants="#222831", shoes="#00ADB5", build="to_con", role="thể thao, sức khoẻ"),
    Look("dau_bep", "Đầu bếp", skin="#F2C9A1", hair="#3B2A20", hair_style="ngan", top="#FAFAFA",
         top_style="ao_dau_bep", pants="#2F2F2F", shoes="#1E1E1E", hat="mu_dau_bep", accent="#E63946",
         beard=True, role="nấu ăn, nhà hàng"),
    Look("bac_si", "Bác sĩ", skin="#EBC6A4", hair="#1B1B1B", hair_style="toc_bob", top="#FFFFFF",
         top_style="ao_bac_si", pants="#4A90A4", gender="nu", accent="#4A90A4",
         extra={"stethoscope": True, "lashes": True}, role="bệnh viện, sức khoẻ"),
    Look("y_ta", "Y tá", skin="#F7D3B5", hair="#5A3825", hair_style="toc_bui", top="#9AD1D4", top_style="ao_y_ta",
         pants="#9AD1D4", hat="mu_y_ta", gender="nu", extra={"lashes": True}, role="bệnh viện"),
    Look("tai_xe", "Bác tài xế", skin="#C68B59", hair="#2B2B2B", hair_style="ngan", top="#3C6E71", top_style="ao_khoac",
         pants="#353535", hat="mu_luoi_trai", extra={"cap": "#F4A259"}, role="giao thông, taxi, hỏi đường"),
    Look("hoc_sinh", "Học sinh", skin="#F8D5B8", hair="#2A1E1A", hair_style="dau_dinh", top="#FFFFFF",
         top_style="dong_phuc", pants="#1D3557", extra={"scarf": "#E63946"}, role="trường học, thi cử"),
    Look("nhan_vien", "Chị nhân viên", skin="#F4CFAE", hair="#6B3E26", hair_style="toc_bob", top="#8E7DBE",
         top_style="vest", pants="#3F3D56", shoes="#1E1E1E", gender="nu", extra={"tie": "#F2E9E4", "lashes": True},
         role="văn phòng, khách sạn, lễ tân"),
    Look("barista", "Anh barista", skin="#E3B38A", hair="#3A2A1F", hair_style="toc_xoan", top="#F5EBE0",
         top_style="tap_de", pants="#403D39", extra={"apron": "#6F4E37", "apron_logo": True},
         role="quán cà phê"),
    Look("du_khach", "Khách du lịch", skin="#F9D9C4", hair="#D4A373", hair_style="toc_dai", top="#FFB703",
         top_style="ao_thun", pants="#219EBC", hat="mu_luoi_trai", gender="nu", accent="#FB8500",
         extra={"cap": "#FB8500", "lashes": True, "iris": "#2A6F97"}, role="du lịch, sân bay, khách sạn"),
    Look("cong_nhan", "Anh công nhân", skin="#B97A56", hair="#2B2B2B", hair_style="ngan", top="#F77F00",
         top_style="ao_khoac", pants="#264653", shoes="#3A2F25", hat="mu_bao_ho", build="to_con",
         role="công trường, việc làm"),
    Look("ba_noi", "Bà nội", skin="#EDC7A7", hair="#E0E0E0", hair_style="toc_bui", top="#9C6644", top_style="ao_khoac",
         pants="#6D4C41", glasses=True, gender="nu", role="gia đình, truyền thống"),
    Look("be_na", "Bé Na", skin="#FBD9BF", hair="#3B2418", hair_style="hai_bim", top="#FF8FAB", top_style="ao_thun",
         pants="#6A4C93", build="nho", gender="nu", accent="#FFE66D", extra={"lashes": True},
         role="trẻ em, gia đình, trường học"),
]


# ---------------- vẽ từng bộ phận ----------------
SKIN_ARMS = ("ao_ba_lo",)      # áo không tay → cánh tay màu da


def draw_body(look: Look, out: Path):
    W, H = 200, 270
    im, d = _canvas(W, H)
    lw = LW * SS
    X = look.extra
    wide = 12 if look.build == "to_con" else 0          # vạm vỡ: vai rộng hơn
    # cổ (để đầu nối liền thân) + thân: vai rộng, eo thon
    d.rounded_rectangle(S(80, 0, 120, 46), radius=10 * SS, fill=look.skin, outline=LINE, width=lw)
    d.rectangle(S(84, 30, 116, 40), fill=_darker(look.skin, 0.85))
    torso = _smooth([(30 - wide, 44), (100, 28), (170 + wide, 44), (180 + wide, 90), (162, 262), (38, 262),
                     (20 - wide, 90)], 8)
    ts = look.top_style
    _poly(d, torso, look.skin if ts == "ao_ba_lo" else look.top)
    shade = _darker(look.top)
    if ts == "hoodie":
        d.pieslice(S(40, -30, 160, 70), 0, 180, fill=shade, outline=LINE, width=lw)        # mũ trùm sau cổ
        for x in (82, 118):                                                                 # dây rút
            d.line(S(x, 40, x, 110), fill=look.accent, width=6 * SS)
            d.ellipse(S(x - 7, 104, x + 7, 118), fill=look.accent, outline=LINE, width=3 * SS)
        d.rounded_rectangle(S(58, 170, 142, 222), radius=18 * SS, fill=shade, outline=LINE, width=4 * SS)  # túi
    elif ts in ("ao_blouse", "ao_bac_si"):
        d.polygon(S(100, 16, 70, 16, 100, 120), fill="#DDE3EA", outline=LINE)             # ve áo
        d.polygon(S(100, 16, 130, 16, 100, 120), fill="#DDE3EA", outline=LINE)
        d.line(S(100, 120, 100, 262), fill=LINE, width=4 * SS)
        d.rectangle(S(118, 150, 150, 158), fill=look.accent)                                 # bút túi áo
        d.rounded_rectangle(S(112, 140, 156, 190), radius=6 * SS, outline=LINE, width=4 * SS)
        if X.get("stethoscope"):
            d.arc(S(56, 20, 144, 150), 20, 160, fill="#37474F", width=7 * SS)
            d.ellipse(S(126, 120, 150, 144), fill="#B0BEC5", outline=LINE, width=4 * SS)
    elif ts == "quan_phuc":
        d.line(S(100, 20, 100, 262), fill=LINE, width=4 * SS)
        for y in (70, 120, 170, 220):
            d.ellipse(S(94, y - 6, 106, y + 6), fill=look.accent)
        d.rounded_rectangle(S(36, 200, 164, 222), radius=4 * SS, fill="#3A2F25")            # thắt lưng
        d.rectangle(S(88, 198, 112, 224), fill=look.accent, outline=LINE, width=3 * SS)
        d.polygon(S(120, 60, 150, 60, 146, 90, 124, 90), fill=shade, outline=LINE)          # túi ngực
    elif ts == "ao_choang":
        d.rectangle(S(40, 22, 160, 60), fill="#F4F1EA", outline=LINE, width=4 * SS)         # cổ lông
        for x in range(52, 160, 22):
            d.ellipse(S(x - 4, 36, x + 4, 44), fill=LINE)
        d.line(S(100, 60, 100, 262), fill=look.accent, width=8 * SS)
    elif ts == "vest":        # áo vest + sơ mi trắng + cà vạt
        d.polygon(S(72, 30, 128, 30, 100, 150), fill="#FFFFFF", outline=LINE)
        tie = X.get("tie", look.accent)
        d.polygon(S(92, 40, 108, 40, 104, 52, 112, 128, 100, 142, 88, 128, 96, 52), fill=tie, outline=LINE)
        for sx in (-1, 1):   # ve áo
            d.polygon(S(100 + sx * 28, 30, 100 + sx * 52, 44, 100 + sx * 16, 150, 100 + sx * 4, 150), fill=shade,
                      outline=LINE)
        for y in (178, 212):
            d.ellipse(S(94, y - 6, 106, y + 6), fill=LINE)
        d.rectangle(S(126, 90, 150, 100), fill="#FFFFFF")                                    # khăn túi ngực
    elif ts == "tap_de":      # tạp dề (bán hàng, barista)
        apron = X.get("apron", "#F4A261")
        d.rounded_rectangle(S(46, 80, 154, 262), radius=16 * SS, fill=apron, outline=LINE, width=lw)
        d.line(S(66, 80, 84, 30), fill=apron, width=10 * SS)
        d.line(S(134, 80, 116, 30), fill=apron, width=10 * SS)
        d.rounded_rectangle(S(70, 170, 130, 214), radius=10 * SS, fill=_darker(apron), outline=LINE, width=4 * SS)
        if X.get("apron_logo"):
            d.ellipse(S(86, 104, 114, 132), fill="#FFFFFF", outline=LINE, width=3 * SS)
    elif ts == "ao_ba_lo":    # áo ba lỗ thể thao
        tank = look.top
        _poly(d, _smooth([(56, 50), (78, 40), (100, 76), (122, 40), (144, 50), (162, 262), (38, 262)], 6), tank)
        d.line(S(40, 150, 160, 150), fill=_darker(tank, 0.7), width=6 * SS)
        # cơ ngực/bụng
        d.arc(S(60, 90, 100, 130), 20, 160, fill=_darker(tank, 0.75), width=4 * SS)
        d.arc(S(100, 90, 140, 130), 20, 160, fill=_darker(tank, 0.75), width=4 * SS)
    elif ts == "ao_dau_bep":  # áo đầu bếp 2 hàng cúc
        d.line(S(100, 30, 100, 262), fill=_darker(look.top, 0.85), width=4 * SS)
        for y in (80, 130, 180):
            for x in (80, 120):
                d.ellipse(S(x - 6, y - 6, x + 6, y + 6), fill=look.accent, outline=LINE, width=2 * SS)
        d.rounded_rectangle(S(66, 28, 134, 48), radius=8 * SS, fill=_darker(look.top, 0.9), outline=LINE, width=4 * SS)
    elif ts == "dong_phuc":   # đồng phục học sinh: sơ mi + khăn quàng/nơ
        d.polygon(S(76, 30, 100, 60, 124, 30), fill="#FFFFFF", outline=LINE)
        d.line(S(100, 60, 100, 262), fill=LINE, width=4 * SS)
        scarf = X.get("scarf", "#E63946")
        d.polygon(S(84, 42, 116, 42, 100, 62), fill=scarf, outline=LINE)
        d.polygon(S(96, 58, 104, 58, 112, 110, 100, 104, 88, 110), fill=scarf, outline=LINE)
        d.rounded_rectangle(S(118, 80, 152, 112), radius=4 * SS, outline=LINE, width=3 * SS)
    elif ts == "ao_khoac":    # áo khoác khoá kéo
        d.line(S(100, 30, 100, 262), fill=LINE, width=5 * SS)
        for y in range(50, 250, 18):
            d.line(S(96, y, 104, y), fill="#B0BEC5", width=3 * SS)
        d.rounded_rectangle(S(40, 30, 160, 58), radius=12 * SS, fill=shade, outline=LINE, width=4 * SS)
        for x in (52, 124):
            d.rounded_rectangle(S(x, 170, x + 26, 214), radius=6 * SS, outline=LINE, width=4 * SS)
    elif ts == "ao_y_ta":
        d.polygon(S(76, 30, 100, 64, 124, 30), fill=_darker(look.top, 0.85), outline=LINE)
        d.rectangle(S(122, 90, 150, 100), fill="#E63946")
        d.rectangle(S(131, 81, 141, 109), fill="#E63946")
    else:  # ao_thun
        d.arc(S(70, -10, 130, 44), 0, 180, fill=LINE, width=4 * SS)
        d.ellipse(S(84, 110, 116, 142), fill=look.accent, outline=LINE, width=3 * SS)     # logo tròn
    _save(im, out / "body.png")
    return {"pivot": [100, 250]}


def _smooth(pts, n=10):
    """Đường cong kín Catmull-Rom qua các điểm điều khiển → polygon mượt."""
    out, m = [], len(pts)
    for i in range(m):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % m], pts[(i + 2) % m]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    return out


def _poly(d, pts, fill, outline=True, width=LW):
    flat = [v * SS for p in pts for v in p]
    d.polygon(flat, fill=fill)
    if outline:
        d.line(flat + flat[:2], fill=LINE, width=width * SS, joint="curve")


def _face_shape(cx, cy, w, h, chin=0.22, n=72):
    """Mặt trái xoan: phía trên tròn, phía dưới thon dần về cằm."""
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x, y = math.cos(t), math.sin(t)
        narrow = 1 - chin * max(0.0, y) ** 1.6
        pts.append((cx + w / 2 * x * narrow, cy + h / 2 * y))
    return pts


HEAD_W, HEAD_H = 300, 340
FCX, FCY, FW, FH = 150, 190, 210, 238        # tâm, rộng, cao khuôn mặt


def _hair_back(d, look):
    h = look.hair
    hs = look.hair_style
    if hs == "toc_dai":         # tóc dài thẳng buông qua vai
        _poly(d, _smooth([(40, 170), (46, 90), (100, 50), (150, 42), (200, 50), (254, 90), (260, 170), (266, 300),
                          (236, 336), (200, 300), (100, 300), (64, 336), (34, 300)], 8), h)
    elif hs == "toc_bob":
        _poly(d, _smooth([(38, 180), (46, 90), (100, 50), (150, 42), (200, 50), (254, 90), (262, 180), (256, 262),
                          (214, 272), (86, 272), (44, 262)], 8), h)
    elif hs == "hai_bim":
        for sx in (-1, 1):
            cx = 150 + sx * 128
            _poly(d, _smooth([(cx - 26, 150), (cx + 26, 150), (cx + 30, 240), (cx, 300), (cx - 30, 240)], 6), h)
            d.ellipse(S(cx - 14, 138, cx + 14, 166), fill=look.accent, outline=LINE, width=4 * SS)
    elif hs == "toc_bui":
        d.ellipse(S(112, 6, 188, 76), fill=h, outline=LINE, width=LW * SS)          # búi tóc
        d.arc(S(120, 14, 180, 68), 200, 300, fill=_lighter(h), width=5 * SS)
    elif hs == "duoi_ngua":
        _poly(d, _smooth([(200, 120), (262, 150), (285, 240), (262, 325), (228, 300), (236, 220), (205, 170)]), h)
        d.ellipse(S(206, 128, 234, 156), fill=look.accent, outline=LINE, width=4 * SS)
    elif look.hair_style in ("lon_xoan", "ngan"):
        _poly(d, _smooth([(52, 190), (48, 110), (100, 60), (150, 48), (206, 60), (252, 110), (248, 190), (230, 150),
                          (70, 150)]), h)


def _hair_front(d, look):
    h, hl = look.hair, _lighter(look.hair)
    hs = look.hair_style
    if hs == "lon_xoan":     # Bơ: mái xéo phồng + lọn tóc dựng (dấu hiệu nhận diện)
        pts = [(46, 170), (50, 100), (96, 58), (160, 46), (222, 68), (256, 118), (254, 176), (236, 132),
               (206, 116), (170, 128), (128, 108), (96, 132), (70, 124)]
        _poly(d, _smooth(pts), h)
        _poly(d, _smooth([(110, 70), (160, 58), (205, 80), (170, 76), (130, 84)], 6), hl, outline=False)
        d.arc(S(142, 4, 196, 58), 100, 340, fill=LINE, width=(LW + 3) * SS)
        d.arc(S(145, 7, 193, 55), 100, 340, fill=h, width=(LW - 2) * SS)
    elif hs == "duoi_ngua":  # Mai: mái thưa rủ + tóc hai bên má
        pts = [(44, 230), (40, 120), (88, 62), (156, 46), (222, 64), (262, 122), (258, 232), (236, 180), (226, 128),
               (190, 108), (150, 132), (118, 112), (86, 126), (70, 180)]
        _poly(d, _smooth(pts), h)
        _poly(d, _smooth([(100, 72), (150, 60), (196, 76), (150, 74)], 6), hl, outline=False)
    elif hs == "ngan":
        pts = [(52, 160), (56, 98), (104, 62), (160, 54), (214, 68), (250, 110), (250, 162), (230, 128),
               (196, 110), (150, 118), (104, 110), (72, 128)]
        _poly(d, _smooth(pts), h)
    elif hs in ("toc_dai", "toc_bob", "toc_bui", "hai_bim"):   # mái rẽ ngôi + phủ đỉnh đầu
        pts = [(42, 200), (44, 116), (92, 60), (156, 46), (220, 62), (262, 118), (258, 204), (238, 150),
               (214, 118), (168, 104), (150, 122), (128, 104), (84, 120), (62, 160)]
        _poly(d, _smooth(pts), h)
        _poly(d, _smooth([(104, 68), (152, 56), (198, 72), (152, 70)], 6), hl, outline=False)
    elif hs == "toc_dung":    # tóc dựng nhọn (năng động)
        pts = [(50, 150), (40, 104), (70, 90), (60, 50), (104, 66), (116, 22), (148, 56), (178, 16), (190, 60),
               (234, 40), (228, 86), (262, 100), (250, 150), (220, 120), (150, 108), (80, 122)]
        _poly(d, pts, h)
        _poly(d, [(118, 40), (140, 64), (122, 66)], hl, outline=False)
    elif hs == "toc_xoan":    # tóc xoăn bồng
        for (x, y, r) in ((70, 110, 34), (100, 72, 38), (150, 58, 40), (200, 72, 38), (230, 110, 34),
                          (54, 150, 26), (246, 150, 26), (126, 96, 30), (176, 96, 30)):
            d.ellipse(S(x - r, y - r, x + r, y + r), fill=h, outline=LINE, width=LW * SS)
        for (x, y, r) in ((100, 72, 30), (150, 58, 32), (200, 72, 30), (126, 96, 24), (176, 96, 24)):
            d.ellipse(S(x - r, y - r, x + r, y + r), fill=h)
    elif hs == "dau_dinh":    # đầu đinh sát
        _poly(d, _smooth([(60, 140), (62, 96), (104, 64), (150, 56), (196, 64), (238, 96), (240, 140), (150, 120)], 8),
              h, outline=False)
    elif hs in ("toc_bac", "hoi"):  # hói đỉnh, tóc bồng hai bên
        for sx in (-1, 1):
            base = 150 + sx * 104
            _poly(d, _smooth([(base, 120), (base + sx * 34, 140), (base + sx * 40, 190), (base + sx * 16, 228),
                              (base - sx * 6, 200), (base - sx * 4, 150)], 6), h)


def _lighter(hex_color, k=1.35):
    hc = hex_color.lstrip("#")
    r, g, b = (int(hc[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % tuple(min(255, int(c * k + 18)) for c in (r, g, b))


def draw_head(look: Look, out: Path):
    im, d = _canvas(HEAD_W, HEAD_H)
    lw = LW * SS
    _hair_back(d, look)
    # tai
    for ex in (FCX - FW // 2 + 4, FCX + FW // 2 - 4):
        d.ellipse(S(ex - 20, FCY - 10, ex + 20, FCY + 34), fill=look.skin, outline=LINE, width=lw)
    face = _face_shape(FCX, FCY, FW, FH)
    _poly(d, face, look.skin)
    # má hồng + mũi
    for mx in (FCX - 62, FCX + 62):
        d.ellipse(S(mx - 20, FCY + 40, mx + 20, FCY + 56), fill="#F4978E")
    d.arc(S(FCX - 9, FCY + 10, FCX + 9, FCY + 34), 300, 80, fill=_darker(look.skin, 0.7), width=5 * SS)
    if look.beard:
        _poly(d, _smooth([(FCX - 92, FCY + 20), (FCX - 70, FCY + 92), (FCX, FCY + 128), (FCX + 70, FCY + 92),
                          (FCX + 92, FCY + 20), (FCX + 50, FCY + 70), (FCX, FCY + 78), (FCX - 50, FCY + 70)], 6),
              look.hair if look.hair_style != "lon_xoan" else "#6D4C41")
    _hair_front(d, look)
    if look.hat == "mu_sat":
        _poly(d, _smooth([(34, 150), (46, 84), (100, 40), (150, 32), (200, 40), (254, 84), (266, 150)], 8),
              _darker(look.top, 0.9))
        d.rounded_rectangle(S(22, 138, 278, 162), radius=10 * SS, fill=_darker(look.top, 0.75), outline=LINE, width=lw)
    elif look.hat == "mu_dau_bep":
        _poly(d, _smooth([(72, 110), (60, 60), (90, 20), (124, 34), (150, 6), (178, 34), (212, 20), (240, 60),
                          (228, 110)], 8), "#FFFFFF")
        d.rounded_rectangle(S(70, 96, 230, 128), radius=8 * SS, fill="#F1F3F5", outline=LINE, width=lw)
    elif look.hat == "mu_luoi_trai":
        _poly(d, _smooth([(48, 124), (58, 70), (110, 40), (150, 36), (196, 44), (244, 76), (252, 124)], 8),
              look.extra.get("cap", look.accent))
        d.chord(S(130, 96, 290, 150), 180, 360, fill=_darker(look.extra.get("cap", look.accent)), outline=LINE, width=lw)
        d.ellipse(S(142, 30, 158, 46), fill=_darker(look.extra.get("cap", look.accent)), outline=LINE, width=3 * SS)
    elif look.hat == "mu_bao_ho":
        _poly(d, _smooth([(40, 128), (50, 70), (100, 36), (150, 30), (200, 36), (250, 70), (260, 128)], 8), "#FFC300")
        d.rounded_rectangle(S(26, 116, 274, 138), radius=10 * SS, fill="#E6A700", outline=LINE, width=lw)
        d.line(S(150, 34, 150, 118), fill="#E6A700", width=10 * SS)
    elif look.hat == "mu_y_ta":
        d.polygon(S(96, 56, 204, 56, 190, 92, 110, 92), fill="#FFFFFF", outline=LINE)
        d.rectangle(S(142, 62, 158, 86), fill="#E63946")
        d.rectangle(S(138, 66, 162, 82), fill="#E63946")
    elif look.hat == "mu_len":
        _poly(d, _smooth([(46, 128), (56, 70), (104, 36), (150, 30), (196, 36), (244, 70), (254, 128)], 8),
              look.extra.get("cap", look.accent))
        d.rounded_rectangle(S(40, 110, 260, 140), radius=12 * SS, fill=_darker(look.extra.get("cap", look.accent)),
                            outline=LINE, width=lw)
        d.ellipse(S(130, 4, 170, 44), fill="#FFFFFF", outline=LINE, width=lw)
    elif look.hat == "vuong_mien":
        pts = [(80, 88), (74, 22), (110, 58), (150, 6), (190, 58), (226, 22), (220, 88)]
        _poly(d, pts, look.accent)
        for gx in (110, 150, 190):
            d.ellipse(S(gx - 9, 62, gx + 9, 80), fill="#E63946", outline=LINE, width=3 * SS)
    _save(im, out / "head.png")
    return {"pivot": [FCX, FCY + FH // 2 - 6],
            "face_anchor": {"brows": [FCX, FCY - 44], "eyes": [FCX, FCY - 8], "mouth": [FCX, FCY + 66]}}


def draw_limb(color: str, w: int, h: int, end: Optional[str], end_color: str, out: Path, name: str,
              stripe: Optional[str] = None):
    """Chi có đầu khớp bo tròn; 'end' = bàn tay/bàn chân vẽ liền ở đầu dưới."""
    extra = 34 if end else 0
    im, d = _canvas(w + 48, h + extra)
    lw = LW * SS
    d.rounded_rectangle(S(12, 4, 12 + w, h), radius=w // 2 * SS, fill=color, outline=LINE, width=lw)
    if stripe:
        d.rectangle(S(12 + lw // SS, h - 34, 12 + w - lw // SS, h - 24), fill=stripe)
    if end == "tay":
        cx = 12 + w // 2
        d.ellipse(S(cx - 24, h - 20, cx + 24, h + 28), fill=end_color, outline=LINE, width=lw)
        d.ellipse(S(cx + 10, h - 12, cx + 30, h + 10), fill=end_color, outline=LINE, width=4 * SS)   # ngón cái
    elif end == "chan":
        d.rounded_rectangle(S(4, h - 16, 12 + w + 22, h + 30), radius=18 * SS, fill=end_color, outline=LINE, width=lw)
    _save(im, out / name)
    return {"pivot": [12 + w // 2, 22]}


def draw_face(out: Path, look: Look) -> dict:
    face = {"eyes": {}, "mouth": {}, "brows": {}}
    white, iris = "#FFFFFF", look.extra.get("iris", "#5B3A29")
    lashes = look.extra.get("lashes", False)

    def eyes(kind):
        im, d = _canvas(200, 96)
        for cx in (58, 142):
            if kind == "nham":
                d.arc(S(cx - 24, 22, cx + 24, 62), 20, 160, fill=LINE, width=8 * SS)
            elif kind == "nheo":
                d.arc(S(cx - 24, 34, cx + 24, 80), 200, 340, fill=LINE, width=8 * SS)
            else:
                rx, ry = (28, 36) if kind == "to" else (22, 30)
                d.ellipse(S(cx - rx, 48 - ry, cx + rx, 48 + ry), fill=white, outline=LINE, width=5 * SS)
                ir = 12 if kind == "to" else 16
                d.ellipse(S(cx - ir + 2, 52 - ir - 2, cx + ir + 2, 52 + ir - 2), fill=iris)
                d.ellipse(S(cx - 7 + 2, 52 - 9, cx + 7 + 2, 52 + 5), fill=LINE)
                d.ellipse(S(cx + 3, 52 - ir + 1, cx + 11, 52 - ir + 9), fill=white)
                d.arc(S(cx - rx - 2, 48 - ry - 2, cx + rx + 2, 48 + ry + 2), 200, 340, fill=LINE, width=8 * SS)
                if lashes:
                    side = -1 if cx < 100 else 1
                    d.line(S(cx + side * (rx - 2), 48 - ry + 10, cx + side * (rx + 12), 48 - ry), fill=LINE, width=6 * SS)
        _save(im, out / f"eyes_{kind}.png")
        face["eyes"][kind] = f"eyes_{kind}.png"

    def mouth(kind):
        im, d = _canvas(120, 70)
        if kind == "ngam":
            d.arc(S(38, 0, 82, 34), 25, 155, fill=LINE, width=6 * SS)
        elif kind in ("vua", "to"):
            box = (42, 10, 78, 42) if kind == "vua" else (34, 4, 86, 62)
            d.ellipse(S(*box), fill="#8C2B3C", outline=LINE, width=5 * SS)
            x0, y0, x1, y1 = box
            d.chord(S(x0 + 6, y1 - 18, x1 - 6, y1 + 4), 180, 360, fill="#F28B9B")
        elif kind == "buon":
            d.arc(S(38, 26, 82, 64), 205, 335, fill=LINE, width=6 * SS)
        elif kind == "cuoi":
            d.chord(S(30, -14, 90, 50), 0, 180, fill="#8C2B3C", outline=LINE, width=5 * SS)
            d.rectangle(S(40, 18, 80, 25), fill=white)
        _save(im, out / f"mouth_{kind}.png")
        face["mouth"][kind] = f"mouth_{kind}.png"

    def brows(kind):
        im, d = _canvas(200, 44)
        col = look.hair if look.hair_style not in ("toc_bac", "hoi") else "#9E9E9E"
        for cx, sgn in ((58, 1), (142, -1)):
            if kind == "cau":
                a, b = (cx - 20, 14 - 8 * sgn), (cx + 20, 14 + 8 * sgn)
            elif kind == "buon":
                a, b = (cx - 20, 20 + 8 * sgn), (cx + 20, 20 - 8 * sgn)
            elif kind == "nhuong":
                a, b = (cx - 20, 14), (cx + 20, 8)
            else:
                a, b = (cx - 20, 22), (cx + 20, 18) if sgn > 0 else (cx + 20, 22)
                if sgn < 0:
                    a, b = (cx - 20, 18), (cx + 20, 22)
            d.line(S(*a, *b), fill=col, width=10 * SS)
        _save(im, out / f"brows_{kind}.png")
        face["brows"][kind] = f"brows_{kind}.png"

    for k in ("mo", "nham", "to", "nheo"):
        eyes(k)
    for k in ("ngam", "vua", "to", "buon", "cuoi"):
        mouth(k)
    for k in ("binh_thuong", "cau", "nhuong", "buon"):
        brows(k)
    return face


def draw_glasses(out: Path):
    im, d = _canvas(200, 90)
    for cx in (60, 140):
        d.ellipse(S(cx - 36, 9, cx + 36, 81), outline=LINE, width=7 * SS)
    d.line(S(96, 40, 104, 40), fill=LINE, width=7 * SS)
    _save(im, out / "glasses.png")


def build(look: Look) -> Path:
    out = CHAR_DIR / look.key
    out.mkdir(parents=True, exist_ok=True)
    body = draw_body(look, out)
    head = draw_head(look, out)
    thick = 10 if look.build == "to_con" else 0
    sleeve = look.skin if look.top_style in SKIN_ARMS else look.top
    long_sleeve = look.top_style in ("ao_blouse", "ao_bac_si", "ao_choang", "vest", "ao_dau_bep", "ao_khoac",
                                     "quan_phuc")
    arm = draw_limb(sleeve, 58 + thick, 130, None, look.skin, out, "arm.png")
    fore = draw_limb(look.top if long_sleeve else look.skin, 52 + thick, 118, "tay", look.skin, out, "forearm.png",
                     stripe="#FFFFFF" if look.top_style == "vest" else None)
    leg = draw_limb(look.pants, 66 + thick // 2, 170, "chan", look.shoes, out, "leg.png")
    face = draw_face(out, look)
    if look.glasses:
        draw_glasses(out)
        face["glasses"] = {"on": "glasses.png"}
    rig = {
        "name": look.name, "height": 720,
        "parts": [
            {"name": "body", "image": "body.png", "pivot": body["pivot"], "parent": None, "z": 3},
            {"name": "leg_l", "image": "leg.png", "pivot": leg["pivot"], "parent": "body", "offset": [-40, -12], "z": 1},
            {"name": "leg_r", "image": "leg.png", "pivot": leg["pivot"], "parent": "body", "offset": [40, -12], "z": 1},
            {"name": "head", "image": "head.png", "pivot": head["pivot"], "parent": "body", "offset": [0, -222], "z": 5},
            {"name": "arm_l", "image": "arm.png", "pivot": arm["pivot"], "parent": "body", "offset": [-74, -208],
             "z": 2, "rest": 12},
            {"name": "forearm_l", "image": "forearm.png", "pivot": fore["pivot"], "parent": "arm_l",
             "offset": [0, 104], "z": 2},
            {"name": "arm_r", "image": "arm.png", "pivot": arm["pivot"], "parent": "body", "offset": [74, -208],
             "z": 6, "rest": -12},
            {"name": "forearm_r", "image": "forearm.png", "pivot": fore["pivot"], "parent": "arm_r",
             "offset": [0, 104], "z": 6},
        ],
        "face": face,
        "face_anchor": {**head["face_anchor"], "glasses": head["face_anchor"]["eyes"]},
        "hand": {"part": "forearm_r", "point": [fore["pivot"][0], 122]},     # điểm cầm đạo cụ
        "expressions": {
            "vui": {"eyes": "nheo", "mouth": "cuoi", "mouth_talk": "cuoi", "brows": "nhuong"},
            "soc": {"eyes": "to", "mouth": "to", "brows": "nhuong"},
            "buon": {"mouth": "buon", "brows": "buon"},
            "gian": {"brows": "cau", "mouth": "ngam"},
            "nghi": {"eyes": "nheo", "brows": "cau"},
        },
    }
    _scale_rig(rig, HD)
    rig["stature"] = {"nho": 0.78}.get(look.build, 1.0)       # trẻ em thấp hơn
    rig["gender"] = look.gender
    rig["role"] = look.role
    (out / "rig.json").write_text(json.dumps(rig, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def _scale_rig(rig: dict, k: float) -> None:
    """Toạ độ thiết kế → toạ độ ảnh HD đã lưu."""
    sc = lambda v: [round(x * k, 1) for x in v]  # noqa: E731
    rig["height"] = round(rig["height"] * k)
    for p in rig["parts"]:
        p["pivot"] = sc(p["pivot"])
        if "offset" in p:
            p["offset"] = sc(p["offset"])
    rig["face_anchor"] = {k2: sc(v) for k2, v in rig["face_anchor"].items()}
    rig["hand"]["point"] = sc(rig["hand"]["point"])


def build_all() -> None:
    for look in CAST:
        build(look)


def model_sheet(path: Path, per_row: int = 7) -> Path:
    """Bảng giới thiệu dàn nhân vật (tư thế + tên + mã dùng trong kịch bản)."""
    from .character import load
    from .images import font
    cell, h = 300, 470
    rows = (len(CAST) + per_row - 1) // per_row
    sheet = Image.new("RGB", (cell * per_row, h * rows), "#F4F1EA")
    d = ImageDraw.Draw(sheet)
    poses = ["vay_tay", "chi_tay", "dung", "vui_mung", "suy_nghi", "dung", "chi_tay"]
    for i, look in enumerate(CAST):
        ch = load(look.key)
        im = ch.render(poses[i % len(poses)], 0.4, expression="vui" if i % 2 == 0 else "")
        im = im.crop(im.getbbox())
        im.thumbnail((cell - 30, int(360 * ch.stature)), Image.LANCZOS)
        x0, y0 = (i % per_row) * cell, (i // per_row) * h
        sheet.paste(im, (x0 + (cell - im.width) // 2, y0 + 380 - im.height), im)
        d.text((x0 + cell // 2, y0 + 412), look.name, font=font(28, "Bold"), fill="#1E1A2B", anchor="mm")
        d.text((x0 + cell // 2, y0 + 446), look.key, font=font(22, "Bold"), fill="#6C757D", anchor="mm")
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    return path


if __name__ == "__main__":
    build_all()
    from .config import ROOT
    model_sheet(ROOT / "docs" / "cast_sheet.png")
    print("Đã tạo:", ", ".join(l.key for l in CAST))
