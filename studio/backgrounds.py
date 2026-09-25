"""Thư viện phông nền phẳng (không cần GPU) — cùng bảng màu, có 'sàn' ở đáy cho nhân vật đứng.
Dùng qua cột `background` của cảnh; để trống = tự động (hoặc SD nếu bật)."""
import random
from pathlib import Path

from PIL import Image, ImageDraw

from .config import HEIGHT, WIDTH

W, H = WIDTH, int(HEIGHT * 0.62)
LINE = "#1E1A2B"


def _sky(d, top, bottom):
    for y in range(H):
        t = y / H
        c = tuple(int(a + (b - a) * t) for a, b in zip(top, bottom))
        d.line([0, y, W, y], fill=c)


def _floor(d, color):
    d.rectangle([0, H - 110, W, H], fill=color)
    d.line([0, H - 110, W, H - 110], fill=LINE, width=6)


def thanh_pho(d, r):
    _sky(d, (126, 200, 227), (206, 236, 245))
    for i in range(9):
        x = i * 125 - 20 + r.randint(-10, 10)
        h = r.randint(260, 620)
        col = r.choice(["#5C6B8A", "#6C7A99", "#48587A", "#7D8BA8"])
        d.rectangle([x, H - 110 - h, x + 115, H - 110], fill=col, outline=LINE, width=5)
        for wy in range(H - 90 - h, H - 140, 55):
            for wx in (x + 18, x + 64):
                d.rectangle([wx, wy, wx + 30, wy + 30], fill=r.choice(["#FFE066", "#BFD7EA"]))
    _floor(d, "#4A4E69")


def rung(d, r):
    _sky(d, (150, 215, 170), (220, 240, 210))
    for i in range(12):
        x = r.randint(-60, W)
        y = H - 110
        d.rectangle([x + 40, y - 150, x + 70, y], fill="#6D4C41", outline=LINE, width=4)
        d.polygon([x - 30, y - 120, x + 55, y - r.randint(420, 560), x + 140, y - 120],
                  fill=r.choice(["#2D6A4F", "#40916C", "#1B4332"]), outline=LINE)
    _floor(d, "#74A57F")


def phong_thi_nghiem(d, r):
    d.rectangle([0, 0, W, H], fill="#E7ECEF")
    for x in range(0, W, 120):
        d.line([x, 0, x, H - 110], fill="#D5DDE3", width=4)
    d.rectangle([60, H - 330, W - 60, H - 250], fill="#8D99AE", outline=LINE, width=6)   # bàn
    for i, x in enumerate(range(120, W - 100, 170)):
        c = ["#80ED99", "#FF8FAB", "#8ECAE6", "#FFD166", "#CDB4DB"][i % 5]
        d.rounded_rectangle([x, H - 430, x + 60, H - 330], 12, fill=c, outline=LINE, width=5)
    _floor(d, "#ADB5BD")


def vu_tru(d, r):
    d.rectangle([0, 0, W, H], fill="#0B1026")
    for _ in range(160):
        x, y, s = r.randint(0, W), r.randint(0, H), r.choice([2, 3, 4, 6])
        d.ellipse([x, y, x + s, y + s], fill="#FFFFFF")
    d.ellipse([W - 360, 90, W - 80, 370], fill="#E76F51", outline=LINE, width=6)
    d.arc([W - 420, 190, W - 20, 280], 160, 380, fill="#F4A261", width=10)
    d.chord([-300, H - 260, W + 300, H + 500], 180, 360, fill="#9A8C98", outline=LINE, width=6)


def sa_mac(d, r):
    _sky(d, (255, 209, 102), (255, 240, 200))
    d.ellipse([W - 300, 80, W - 120, 260], fill="#FFF3C4")
    for x in (80, 700):
        d.rounded_rectangle([x, H - 420, x + 60, H - 110], 30, fill="#52B788", outline=LINE, width=5)
        d.rounded_rectangle([x - 60, H - 330, x, H - 300], 15, fill="#52B788", outline=LINE, width=5)
    d.chord([-400, H - 330, W + 400, H + 400], 180, 360, fill="#E9C46A", outline=LINE, width=5)
    _floor(d, "#DDA15E")


def bien(d, r):
    _sky(d, (135, 206, 235), (220, 245, 255))
    d.rectangle([0, H - 420, W, H - 110], fill="#219EBC")
    for y in range(H - 400, H - 130, 60):
        for x in range(r.randint(-40, 0), W, 160):
            d.arc([x, y, x + 80, y + 30], 200, 340, fill="#8ECAE6", width=6)
    _floor(d, "#F4D58D")


def phong_khach(d, r):
    d.rectangle([0, 0, W, H], fill="#F2E8CF")
    d.rectangle([140, 160, 520, 460], fill="#8ECAE6", outline=LINE, width=8)        # cửa sổ
    d.line([330, 160, 330, 460], fill=LINE, width=6)
    d.rounded_rectangle([600, H - 420, 1000, H - 180], 30, fill="#E07A5F", outline=LINE, width=6)  # sofa
    _floor(d, "#A98467")


def lau_dai(d, r):
    _sky(d, (190, 170, 230), (240, 225, 250))
    d.rectangle([180, H - 620, 900, H - 110], fill="#ADB5BD", outline=LINE, width=6)
    for x in range(180, 900, 90):
        d.rectangle([x, H - 660, x + 50, H - 620], fill="#ADB5BD", outline=LINE, width=5)
    d.rounded_rectangle([470, H - 320, 610, H - 110], 60, fill="#6D4C41", outline=LINE, width=6)
    _floor(d, "#6A994E")


def chien_truong(d, r):
    _sky(d, (160, 160, 150), (210, 200, 180))
    for _ in range(5):
        x = r.randint(0, W)
        d.ellipse([x - 120, 80, x + 120, 220], fill="#8D8D8D")
    for x in range(-40, W, 160):
        d.polygon([x, H - 110, x + 60, H - 200, x + 120, H - 110], fill="#7F5539", outline=LINE)
    _floor(d, "#606C38")


def van_phong(d, r):
    d.rectangle([0, 0, W, H], fill="#DDE5ED")
    d.rectangle([80, 120, W - 80, 420], fill="#A9D6E5", outline=LINE, width=6)
    for x in range(80, W - 80, 230):
        d.line([x, 120, x, 420], fill=LINE, width=5)
    d.rectangle([100, H - 330, W - 100, H - 270], fill="#6C757D", outline=LINE, width=6)
    _floor(d, "#8E9AAF")


def quan_ca_phe(d, r):
    d.rectangle([0, 0, W, H], fill="#EAD7C3")
    for x in range(0, W, 60):
        d.line([x, 0, x, H - 360], fill="#E0CBB4", width=3)
    d.rounded_rectangle([90, 110, 560, 430], 24, fill="#2F3E46", outline=LINE, width=8)      # bảng menu
    for i, y in enumerate(range(170, 410, 55)):
        d.line([130, y, 130 + r.randint(200, 360), y], fill="#F4F1DE", width=10)
    d.ellipse([700, 130, 960, 390], fill="#FFFFFF", outline=LINE, width=8)                   # logo cốc
    d.rounded_rectangle([780, 210, 880, 320], 16, fill="#8D6E63", outline=LINE, width=6)
    d.rectangle([0, H - 360, W, H - 110], fill="#9C6644", outline=LINE, width=6)             # quầy
    for x in range(120, W, 220):
        d.rounded_rectangle([x, H - 420, x + 70, H - 360], 10, fill="#FFFFFF", outline=LINE, width=5)
    _floor(d, "#7F5539")


# ---------- bối cảnh giao tiếp hằng ngày (có đồ vật thật trên kệ/quầy) ----------
def _shelves(d, x0, x1, ys, color="#B08968"):
    for y in ys:
        d.rectangle([x0, y, x1, y + 22], fill=color, outline=LINE, width=5)
    d.rectangle([x0 - 10, ys[0] - 330, x0 + 10, ys[-1] + 22], fill=color, outline=LINE, width=5)
    d.rectangle([x1 - 10, ys[0] - 330, x1 + 10, ys[-1] + 22], fill=color, outline=LINE, width=5)


def tiem_tap_hoa(d, r):
    d.rectangle([0, 0, W, H], fill="#FFF3D6")
    d.rectangle([0, 0, W, 90], fill="#E76F51")                                                # biển hiệu
    for x in range(0, W, 90):
        d.polygon([x, 90, x + 45, 140, x + 90, 90], fill="#F4A261" if (x // 90) % 2 else "#FFFFFF", outline=LINE)
    _shelves(d, 40, W - 40, [420, 640])
    d.rectangle([0, H - 330, W, H - 110], fill="#9C6644", outline=LINE, width=6)             # quầy thu ngân
    d.rectangle([W - 300, H - 420, W - 120, H - 330], fill="#6C757D", outline=LINE, width=5) # máy tính tiền
    d.rectangle([W - 280, H - 405, W - 140, H - 370], fill="#90E0EF")
    _floor(d, "#8D6E63")


def cho_trai_cay(d, r):
    _sky(d, (190, 227, 255), (240, 248, 255))
    d.polygon([0, 150, W // 2, 60, W, 150, W, 230, 0, 230], fill="#E63946", outline=LINE)   # mái bạt sọc
    for x in range(0, W, 120):
        d.polygon([x, 150, x + 60, 124, x + 60, 230, x, 230], fill="#FFFFFF")
    d.rectangle([60, H - 520, W - 60, H - 330], fill="#A5673F", outline=LINE, width=6)         # sạp
    for i in range(6):
        d.rectangle([90 + i * 155, H - 500, 220 + i * 155, H - 420], fill="#DDB892", outline=LINE, width=4)
    _floor(d, "#6C757D")


def nha_hang(d, r):
    d.rectangle([0, 0, W, H], fill="#F2E8CF")
    for x in range(0, W, 140):
        d.rectangle([x, 0, x + 70, H - 360], fill="#EBDCBF")
    d.rounded_rectangle([90, 120, 520, 470], 20, fill="#344E41", outline=LINE, width=8)      # bảng thực đơn
    for y in range(180, 440, 50):
        d.line([130, y, 130 + r.randint(200, 330), y], fill="#FEFAE0", width=10)
        d.ellipse([460, y - 10, 480, y + 10], fill="#FFD166")
    for x in (700, 900):                                                                      # đèn thả
        d.line([x, 0, x, 120], fill=LINE, width=5)
        d.chord([x - 60, 100, x + 60, 190], 180, 360, fill="#E9C46A", outline=LINE, width=5)
    d.rounded_rectangle([60, H - 330, W - 60, H - 280], 10, fill="#9C6644", outline=LINE, width=6)  # bàn ăn
    _floor(d, "#6F4E37")


def san_bay(d, r):
    d.rectangle([0, 0, W, H], fill="#E3F2FD")
    d.rectangle([0, 60, W, 420], fill="#90CAF9", outline=LINE, width=6)                      # kính lớn
    for x in range(0, W, 180):
        d.line([x, 60, x, 420], fill=LINE, width=5)
    d.polygon([620, 250, 900, 210, 960, 220, 700, 270], fill="#FFFFFF", outline=LINE)         # máy bay
    d.polygon([760, 230, 820, 160, 850, 165, 810, 236], fill="#FFFFFF", outline=LINE)
    d.rounded_rectangle([90, 470, 560, 640], 16, fill="#1D3557", outline=LINE, width=6)      # bảng giờ bay
    for i, y in enumerate(range(500, 620, 36)):
        d.line([120, y, 360, y], fill="#FFD166", width=12)
        d.line([400, y, 530, y], fill="#80ED99" if i % 2 else "#FF6B6B", width=12)
    d.rectangle([0, H - 330, W, H - 110], fill="#ADB5BD", outline=LINE, width=6)             # quầy check-in
    _floor(d, "#CED4DA")


def khach_san(d, r):
    d.rectangle([0, 0, W, H], fill="#F8EDEB")
    d.rounded_rectangle([W // 2 - 260, 90, W // 2 + 260, 200], 20, fill="#6D597A", outline=LINE, width=6)  # biển
    for x in (150, W - 150):                                                                  # cây cảnh
        d.rectangle([x - 40, H - 480, x + 40, H - 330], fill="#B56576", outline=LINE, width=5)
        d.ellipse([x - 90, H - 700, x + 90, H - 460], fill="#52B788", outline=LINE, width=5)
    d.rectangle([300, 300, 780, 470], fill="#E5989B", outline=LINE, width=6)                  # tủ chìa khoá
    for x in range(330, 760, 60):
        for y in (330, 400):
            d.rectangle([x, y, x + 36, y + 40], fill="#FFE5D9", outline=LINE, width=3)
    d.rectangle([0, H - 330, W, H - 110], fill="#B5838D", outline=LINE, width=6)            # quầy lễ tân
    d.ellipse([W // 2 - 30, H - 370, W // 2 + 30, H - 330], fill="#FFD166", outline=LINE, width=4)  # chuông
    _floor(d, "#6D597A")


def benh_vien(d, r):
    d.rectangle([0, 0, W, H], fill="#EAF4F4")
    d.rectangle([0, H - 520, W, H - 470], fill="#A4C3B2")
    d.rounded_rectangle([W // 2 - 90, 90, W // 2 + 90, 270], 20, fill="#FFFFFF", outline=LINE, width=6)
    d.rectangle([W // 2 - 20, 120, W // 2 + 20, 240], fill="#E63946")
    d.rectangle([W // 2 - 60, 160, W // 2 + 60, 200], fill="#E63946")
    d.rectangle([90, 330, 330, 560], fill="#FFFFFF", outline=LINE, width=6)                    # tủ thuốc
    for y in (400, 480):
        d.line([90, y, 330, y], fill=LINE, width=5)
    d.rectangle([0, H - 330, W, H - 110], fill="#CCE3DE", outline=LINE, width=6)
    _floor(d, "#6B9080")


def shop_quan_ao(d, r):
    d.rectangle([0, 0, W, H], fill="#FFF0F3")
    d.line([60, 250, W - 60, 250], fill=LINE, width=10)                                       # giá treo
    cols = ["#3A86FF", "#FF006E", "#FFBE0B", "#8338EC", "#06D6A0", "#FB5607"]
    for i, x in enumerate(range(110, W - 100, 150)):
        c = cols[i % len(cols)]
        d.line([x, 250, x, 285], fill=LINE, width=5)
        d.polygon([x - 55, 285, x + 55, 285, x + 70, 320, x + 45, 330, x + 45, 450, x - 45, 450, x - 45, 330,
                   x - 70, 320], fill=c, outline=LINE)
    d.rounded_rectangle([W - 300, 520, W - 100, H - 110], 20, fill="#CDB4DB", outline=LINE, width=6)  # phòng thử
    d.rectangle([0, H - 330, W - 320, H - 110], fill="#FFC8DD", outline=LINE, width=6)
    _floor(d, "#E5989B")


def ben_xe_buyt(d, r):
    _sky(d, (160, 210, 250), (225, 240, 255))
    for i in range(6):
        x = i * 190 - 30
        h = r.randint(260, 480)
        d.rectangle([x, H - 420 - h, x + 170, H - 420], fill=r.choice(["#6C7A99", "#8D99AE", "#5C6B8A"]),
                    outline=LINE, width=4)
    d.rectangle([80, H - 700, 110, H - 110], fill="#495057", outline=LINE, width=4)            # cột biển
    d.rounded_rectangle([40, H - 780, 250, H - 690], 14, fill="#2A9D8F", outline=LINE, width=6)
    d.rounded_rectangle([130, H - 755, 190, H - 715], 10, fill="#FFFFFF")
    d.rectangle([420, H - 560, W - 40, H - 530], fill="#6C757D", outline=LINE, width=5)        # mái chờ
    d.rectangle([440, H - 530, 460, H - 110], fill="#6C757D")
    d.rectangle([W - 80, H - 530, W - 60, H - 110], fill="#6C757D")
    d.rectangle([0, H - 150, W, H - 110], fill="#ADB5BD")
    _floor(d, "#495057")


# Đồ vật bày sẵn trong bối cảnh: (tên prop, x, y, cỡ px) — tăng cảm giác "không gian thật"
SCENE_ITEMS = {
    "tiem_tap_hoa": [("mi_goi", 110, 290, 130), ("banh_quy", 270, 290, 130), ("sua", 430, 290, 130),
                     ("nuoc", 590, 290, 130), ("banh_mi", 750, 300, 130), ("mi_goi", 900, 290, 130),
                     ("banh_quy", 110, 510, 130), ("nuoc", 270, 510, 130), ("sua", 430, 510, 130),
                     ("tao", 590, 520, 120), ("chuoi", 750, 510, 130), ("banh_quy", 900, 510, 130)],
    "cho_trai_cay": [(k, 100 + i * 155, 570, 120) for i, k in enumerate(["tao", "chuoi", "tao", "chuoi", "tao",
                                                                          "chuoi"])],
    "nha_hang": [("bat_pho", 660, 730, 150), ("ca_phe", 860, 720, 130)],
    "san_bay": [("va_li", 820, 590, 170)],
    "benh_vien": [("thuoc", 110, 342, 100), ("thuoc", 210, 342, 100), ("thuoc", 150, 420, 100)],
    "shop_quan_ao": [],
    "khach_san": [],
    "ben_xe_buyt": [],
    "quan_ca_phe": [],
}


BACKGROUNDS = {"tiem_tap_hoa": tiem_tap_hoa, "cho_trai_cay": cho_trai_cay, "nha_hang": nha_hang,
               "san_bay": san_bay, "khach_san": khach_san, "benh_vien": benh_vien, "shop_quan_ao": shop_quan_ao,
               "ben_xe_buyt": ben_xe_buyt, "quan_ca_phe": quan_ca_phe, "thanh_pho": thanh_pho, "rung": rung, "phong_thi_nghiem": phong_thi_nghiem,
               "vu_tru": vu_tru, "sa_mac": sa_mac, "bien": bien, "phong_khach": phong_khach,
               "lau_dai": lau_dai, "chien_truong": chien_truong, "van_phong": van_phong}


def generate(name: str, out: Path, seed: int = 0) -> Path:
    img = Image.new("RGB", (W, H))
    BACKGROUNDS[name](ImageDraw.Draw(img), random.Random(seed))
    if SCENE_ITEMS.get(name):
        from .props import get as get_prop
        for key, x, y, size in SCENE_ITEMS[name]:
            it = get_prop(key).copy()
            it.thumbnail((size, size), Image.LANCZOS)
            img.paste(it, (x, y), it)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out
