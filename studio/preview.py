"""Xem nhanh bảng tư thế của nhân vật:  python -m studio.preview mau  -> preview_<tên>.png"""
import sys

from PIL import Image, ImageDraw

from . import character as c
from .images import font

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "mau"
    ch = c.load(name)
    acts = c.ACTION_LABELS
    cell = 360
    sheet = Image.new("RGB", (cell * 5, (cell + 40) * ((len(acts) + 4) // 5)), "#F4F1EA")
    d = ImageDraw.Draw(sheet)
    for i, a in enumerate(acts):
        img = ch.render(a, 0.45, mouth_open=0.5)
        img = img.crop(img.getbbox())
        img.thumbnail((cell - 40, cell - 40))
        x, y = (i % 5) * cell, (i // 5) * (cell + 40)
        sheet.paste(img, (x + (cell - img.width) // 2, y + cell - img.height), img)
        d.text((x + cell // 2, y + cell + 18), a, font=font(28, "Bold"), fill="#1B1B1B", anchor="mm")
    out = f"preview_{name}.png"
    sheet.save(out)
    print("Đã lưu", out)
