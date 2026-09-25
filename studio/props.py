"""Đạo cụ cầm tay — vẽ vector phẳng cùng phong cách nhân vật. Điểm cầm = giữa-đáy ảnh."""
import math
from functools import lru_cache

from PIL import Image, ImageDraw

from .cast import LINE, S, SS

W = H = 180


def _new():
    im = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def _done(im):
    from .cast import HD
    return im.resize((int(W * HD), int(H * HD)), Image.LANCZOS)


def _lw(k=6):
    return k * SS


def phone(d):
    d.rounded_rectangle(S(60, 20, 120, 150), 14 * SS, fill="#2B2D42", outline=LINE, width=_lw())
    d.rounded_rectangle(S(68, 34, 112, 130), 6 * SS, fill="#8ECAE6")


def money(d):
    for i, dy in enumerate((0, 14, 28)):
        d.rounded_rectangle(S(30, 60 + dy, 150, 120 + dy), 8 * SS, fill="#7CB518", outline=LINE, width=_lw(5))
    d.ellipse(S(75, 92, 105, 122), fill="#5C8001", outline=LINE, width=_lw(4))


def coin(d):
    d.ellipse(S(40, 40, 140, 140), fill="#FFC23C", outline=LINE, width=_lw())
    d.ellipse(S(60, 60, 120, 120), outline="#E09F00", width=_lw(5))


def bomb(d):
    d.ellipse(S(40, 50, 140, 150), fill="#2B2D42", outline=LINE, width=_lw())
    d.rectangle(S(80, 36, 100, 56), fill="#555", outline=LINE, width=_lw(4))
    d.arc(S(95, 5, 145, 55), 180, 270, fill="#8D6E63", width=_lw(5))
    d.ellipse(S(88, 2, 108, 22), fill="#FF9F1C")


def clock(d):
    d.ellipse(S(30, 30, 150, 150), fill="#FFFFFF", outline=LINE, width=_lw())
    d.line(S(90, 90, 90, 50), fill=LINE, width=_lw(6))
    d.line(S(90, 90, 120, 100), fill="#E63946", width=_lw(5))


def book(d):
    d.rounded_rectangle(S(35, 40, 145, 140), 6 * SS, fill="#3A86FF", outline=LINE, width=_lw())
    d.line(S(90, 40, 90, 140), fill=LINE, width=_lw(4))
    d.rectangle(S(100, 60, 135, 72), fill="#FFFFFF")


def coffee(d):
    d.rounded_rectangle(S(55, 60, 125, 150), 10 * SS, fill="#FFFFFF", outline=LINE, width=_lw())
    d.arc(S(110, 80, 150, 125), 270, 90, fill=LINE, width=_lw(6))
    d.rectangle(S(58, 80, 122, 100), fill="#8D6E63")
    for x in (75, 100):
        d.arc(S(x - 10, 15, x + 10, 55), 90, 270, fill="#B0B0B0", width=_lw(4))


def sword(d):
    d.polygon(S(84, 5, 96, 5, 96, 120, 90, 132, 84, 120), fill="#DDE3EA", outline=LINE)
    d.rectangle(S(60, 120, 120, 132), fill="#F5C542", outline=LINE, width=_lw(4))
    d.rectangle(S(84, 132, 96, 170), fill="#6D4C41", outline=LINE, width=_lw(4))


def flask(d):
    d.polygon(S(75, 20, 105, 20, 105, 70, 145, 150, 35, 150, 75, 70), fill="#FFFFFF", outline=LINE)
    d.polygon(S(55, 110, 125, 110, 145, 150, 35, 150), fill="#80ED99")
    d.line(S(75, 20, 75, 70, 35, 150, 145, 150, 105, 70, 105, 20), fill=LINE, width=_lw(5))


def pizza(d):
    d.pieslice(S(10, -40, 170, 150), 60, 120, fill="#FFD166", outline=LINE, width=_lw())
    for x, y in ((80, 110), (100, 120), (90, 95)):
        d.ellipse(S(x - 8, y - 8, x + 8, y + 8), fill="#E63946")


def flag(d):
    d.rectangle(S(40, 10, 48, 170), fill="#6D4C41", outline=LINE, width=_lw(3))
    d.rectangle(S(48, 14, 150, 80), fill="#E63946", outline=LINE, width=_lw(5))
    d.regular_polygon((99 * SS, 47 * SS, 18 * SS), 5, fill="#FFC23C")


def lightbulb(d):
    d.ellipse(S(45, 20, 135, 110), fill="#FFE066", outline=LINE, width=_lw())
    d.rectangle(S(70, 105, 110, 140), fill="#B0B0B0", outline=LINE, width=_lw(5))


# ---------- đồ vật cho tình huống giao tiếp hằng ngày ----------
def banh_quy(d):          # hộp bánh quy
    d.rounded_rectangle(S(30, 50, 150, 160), 10 * SS, fill="#E76F51", outline=LINE, width=_lw())
    d.rectangle(S(30, 80, 150, 104), fill="#F4A261")
    for x, y in ((60, 130), (90, 126), (120, 132)):
        d.ellipse(S(x - 14, y - 14, x + 14, y + 14), fill="#E9C46A", outline=LINE, width=_lw(3))
        d.ellipse(S(x - 4, y - 4, x + 4, y + 4), fill="#6D4C41")


def banh_mi(d):
    d.chord(S(15, 60, 165, 150), 180, 360, fill="#E9C46A", outline=LINE, width=_lw())
    d.rectangle(S(15, 104, 165, 124), fill="#E9C46A", outline=LINE, width=_lw(4))
    for x in (55, 90, 125):
        d.arc(S(x - 16, 70, x + 16, 100), 200, 340, fill="#C98E48", width=_lw(4))


def sua(d):               # hộp sữa
    d.polygon(S(55, 40, 125, 40, 140, 64, 140, 165, 40, 165, 40, 64), fill="#FFFFFF", outline=LINE)
    d.line(S(55, 40, 125, 40, 140, 64, 140, 165, 40, 165, 40, 64, 55, 40), fill=LINE, width=_lw(5))
    d.rectangle(S(40, 96, 140, 134), fill="#8ECAE6")
    d.ellipse(S(76, 104, 104, 128), fill="#FFFFFF")


def nuoc(d):              # chai nước
    d.rounded_rectangle(S(64, 10, 116, 30), 4 * SS, fill="#219EBC", outline=LINE, width=_lw(4))
    d.rounded_rectangle(S(52, 30, 128, 170), 22 * SS, fill="#CAF0F8", outline=LINE, width=_lw())
    d.rectangle(S(52, 80, 128, 116), fill="#219EBC")


def mi_goi(d):            # gói mì
    d.rounded_rectangle(S(20, 50, 160, 150), 16 * SS, fill="#FFB703", outline=LINE, width=_lw())
    d.arc(S(50, 70, 130, 130), 200, 340, fill="#E63946", width=_lw(8))
    d.arc(S(50, 86, 130, 146), 200, 340, fill="#E63946", width=_lw(8))


def tao(d):
    d.ellipse(S(35, 45, 145, 160), fill="#E63946", outline=LINE, width=_lw())
    d.line(S(90, 50, 96, 22), fill="#6D4C41", width=_lw(6))
    d.ellipse(S(98, 20, 132, 40), fill="#52B788", outline=LINE, width=_lw(3))
    d.ellipse(S(58, 66, 78, 90), fill="#FF8FA3")


def chuoi(d):
    for k, dx in enumerate((0, 18, 36)):
        pts = [(40 + dx, 60), (70 + dx, 130), (120 + dx, 150), (150, 140 - k * 4), (118 + dx, 128), (86 + dx, 108),
               (62 + dx, 56)]
        d.polygon([v * SS for p in pts for v in p], fill="#FFD166", outline=LINE)
        d.line([v * SS for p in pts + pts[:1] for v in p], fill=LINE, width=_lw(4))
    d.rectangle(S(40, 44, 90, 62), fill="#6D4C41", outline=LINE, width=_lw(3))


def ao_thun(d):
    d.polygon(S(55, 30, 125, 30, 165, 60, 145, 88, 128, 76, 128, 160, 52, 160, 52, 76, 35, 88, 15, 60),
              fill="#3A86FF", outline=LINE)
    d.line(S(55, 30, 125, 30, 165, 60, 145, 88, 128, 76, 128, 160, 52, 160, 52, 76, 35, 88, 15, 60, 55, 30),
           fill=LINE, width=_lw(5))
    d.arc(S(70, 14, 110, 50), 20, 160, fill=LINE, width=_lw(5))


def ve(d):                # vé tàu / vé máy bay
    d.rounded_rectangle(S(15, 50, 165, 130), 12 * SS, fill="#FFFFFF", outline=LINE, width=_lw())
    d.rectangle(S(15, 50, 60, 130), fill="#FB8500")
    d.line(S(60, 55, 60, 125), fill=LINE, width=_lw(3))
    for y in (74, 92, 110):
        d.line(S(75, y, 150, y), fill="#8D99AE", width=_lw(5))


def ho_chieu(d):
    d.rounded_rectangle(S(45, 25, 135, 160), 10 * SS, fill="#1D3557", outline=LINE, width=_lw())
    d.ellipse(S(70, 60, 110, 100), outline="#F4D35E", width=_lw(4))
    d.line(S(62, 120, 118, 120), fill="#F4D35E", width=_lw(4))


def va_li(d):
    d.rounded_rectangle(S(65, 15, 115, 45), 10 * SS, outline=LINE, width=_lw(6))
    d.rounded_rectangle(S(30, 40, 150, 165), 16 * SS, fill="#8338EC", outline=LINE, width=_lw())
    for x in (65, 115):
        d.line(S(x, 50, x, 155), fill="#5A189A", width=_lw(5))


def thuoc(d):             # hộp thuốc
    d.rounded_rectangle(S(35, 55, 145, 150), 10 * SS, fill="#FFFFFF", outline=LINE, width=_lw())
    d.rectangle(S(80, 72, 100, 132), fill="#E63946")
    d.rectangle(S(60, 92, 120, 112), fill="#E63946")


def hoa_don(d):           # hoá đơn
    d.polygon(S(45, 20, 135, 20, 135, 160, 120, 150, 105, 160, 90, 150, 75, 160, 60, 150, 45, 160), fill="#FFFFFF",
              outline=LINE)
    for y in (46, 66, 86, 106):
        d.line(S(58, y, 122, y), fill="#8D99AE", width=_lw(4))
    d.line(S(58, 130, 122, 130), fill="#E63946", width=_lw(6))


def the_phong(d):         # thẻ phòng khách sạn
    d.rounded_rectangle(S(25, 55, 155, 135), 12 * SS, fill="#2A9D8F", outline=LINE, width=_lw())
    d.rectangle(S(25, 75, 155, 90), fill="#264653")
    d.rounded_rectangle(S(110, 104, 142, 124), 4 * SS, fill="#E9C46A")


def ban_do(d):
    d.polygon(S(20, 40, 70, 25, 110, 40, 160, 25, 160, 150, 110, 165, 70, 150, 20, 165), fill="#CAFFBF", outline=LINE)
    d.line(S(70, 25, 70, 150), fill=LINE, width=_lw(3))
    d.line(S(110, 40, 110, 165), fill=LINE, width=_lw(3))
    d.ellipse(S(118, 60, 146, 88), fill="#E63946", outline=LINE, width=_lw(3))


def bat_pho(d):           # bát mì/phở
    d.chord(S(20, 40, 160, 160), 0, 180, fill="#FFFFFF", outline=LINE, width=_lw())
    d.ellipse(S(20, 80, 160, 110), fill="#F4A261", outline=LINE, width=_lw(4))
    d.line(S(110, 20, 60, 95), fill="#8D6E63", width=_lw(5))
    d.line(S(126, 22, 76, 97), fill="#8D6E63", width=_lw(5))


def the_ngan_hang(d):
    d.rounded_rectangle(S(20, 55, 160, 140), 12 * SS, fill="#3A0CA3", outline=LINE, width=_lw())
    d.rounded_rectangle(S(36, 78, 64, 100), 4 * SS, fill="#FFD166")
    d.line(S(36, 120, 140, 120), fill="#FFFFFF", width=_lw(4))


PROPS = {"dien_thoai": phone, "tien": money, "dong_xu": coin, "bom": bomb, "dong_ho": clock,
         "sach": book, "ca_phe": coffee, "kiem": sword, "binh_thi_nghiem": flask, "pizza": pizza,
         "co": flag, "bong_den": lightbulb,
         # đồ vật tình huống hằng ngày
         "banh_quy": banh_quy, "banh_mi": banh_mi, "sua": sua, "nuoc": nuoc, "mi_goi": mi_goi, "tao": tao,
         "chuoi": chuoi, "ao_thun": ao_thun, "ve": ve, "ho_chieu": ho_chieu, "va_li": va_li, "thuoc": thuoc,
         "hoa_don": hoa_don, "the_phong": the_phong, "ban_do": ban_do, "bat_pho": bat_pho,
         "the_ngan_hang": the_ngan_hang}


@lru_cache(maxsize=None)
def get(name: str) -> Image.Image:
    im, d = _new()
    PROPS[name](d)
    return _done(im)
