"""Nhân vật hoạt hình cắt ghép (cutout/puppet) — kỹ thuật dựng kiểu kênh infographic.

Một nhân vật = thư mục `assets/characters/<tên>/` gồm:
  - các file PNG nền trong suốt cho từng BỘ PHẬN (đầu, thân, tay trên/dưới, chân...)
  - `rig.json`: khớp xoay (pivot), quan hệ cha-con, thứ tự lớp, biến thể mắt/miệng
Chuyển động (`ACTIONS`) = keyframe góc xoay từng khớp, nội suy mượt. Miệng nhép theo âm lượng
giọng đọc, mắt tự chớp. Bạn chỉ cần VẼ các bộ phận theo `CHARACTER_GUIDE.md` rồi thay PNG.
"""
import json
import math
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from PIL import Image, ImageDraw

from .config import ASSETS

CHAR_DIR = ASSETS / "characters"

# ---------------- Thư viện động tác (góc xoay độ, dương = theo chiều kim đồng hồ) ----------------
# Mỗi động tác: danh sách (thời điểm giây, {khớp: góc}), "loop": lặp lại; "bob": nhún người (px).
ACTIONS: Dict[str, dict] = {
    "dung": {"loop": True, "bob": 4, "keys": [
        (0.0, {"arm_l": 8, "arm_r": -8, "head": -2}), (1.2, {"arm_l": 12, "arm_r": -12, "head": 2}),
        (2.4, {"arm_l": 8, "arm_r": -8, "head": -2})]},
    "di_bo": {"loop": True, "bob": 10, "move": 1, "keys": [
        (0.0, {"leg_l": 25, "leg_r": -25, "arm_l": -25, "arm_r": 25}),
        (0.35, {"leg_l": -25, "leg_r": 25, "arm_l": 25, "arm_r": -25}),
        (0.7, {"leg_l": 25, "leg_r": -25, "arm_l": -25, "arm_r": 25})]},
    "chay": {"loop": True, "bob": 18, "move": 2.2, "keys": [
        (0.0, {"leg_l": 45, "leg_r": -45, "arm_l": -60, "forearm_l": -60, "arm_r": 60, "forearm_r": 60, "body": 8}),
        (0.22, {"leg_l": -45, "leg_r": 45, "arm_l": 60, "forearm_l": -60, "arm_r": -60, "forearm_r": 60, "body": 8}),
        (0.44, {"leg_l": 45, "leg_r": -45, "arm_l": -60, "forearm_l": -60, "arm_r": 60, "forearm_r": 60, "body": 8})]},
    "chi_tay": {"loop": False, "keys": [
        (0.0, {"arm_r": -8}), (0.3, {"arm_r": -100, "forearm_r": -10, "head": 6}),
        (99, {"arm_r": -100, "forearm_r": -10, "head": 6})]},
    "vay_tay": {"loop": True, "keys": [
        (0.0, {"arm_r": -150, "forearm_r": -20}), (0.25, {"arm_r": -150, "forearm_r": 30}),
        (0.5, {"arm_r": -150, "forearm_r": -20})]},
    "suy_nghi": {"loop": False, "keys": [
        (0.0, {}), (0.4, {"arm_r": -35, "forearm_r": -140, "head": -10}),
        (99, {"arm_r": -35, "forearm_r": -140, "head": -10})], "expression": "nghi"},
    "bat_ngo": {"loop": False, "bob": 0, "keys": [
        (0.0, {}), (0.15, {"arm_l": 140, "arm_r": -140, "forearm_l": 30, "forearm_r": -30, "head": 0}),
        (99, {"arm_l": 140, "arm_r": -140, "forearm_l": 30, "forearm_r": -30})], "expression": "soc", "jump": 40},
    "vui_mung": {"loop": True, "bob": 0, "jump": 60, "keys": [
        (0.0, {"arm_l": 150, "arm_r": -150}), (0.3, {"arm_l": 170, "arm_r": -170}),
        (0.6, {"arm_l": 150, "arm_r": -150})], "expression": "vui"},
    "buon": {"loop": False, "keys": [
        (0.0, {}), (0.6, {"head": 18, "arm_l": 4, "arm_r": -4, "body": 6}),
        (99, {"head": 18, "arm_l": 4, "arm_r": -4, "body": 6})], "expression": "buon"},
    "run_so": {"loop": True, "keys": [
        (0.0, {"body": -3, "arm_l": 20, "arm_r": -20}), (0.06, {"body": 3, "arm_l": 24, "arm_r": -24}),
        (0.12, {"body": -3, "arm_l": 20, "arm_r": -20})], "expression": "soc"},
}
ACTION_LABELS = list(ACTIONS)


@dataclass
class Part:
    name: str
    image: Image.Image
    pivot: tuple          # điểm khớp trong ảnh bộ phận (px)
    parent: Optional[str]
    offset: tuple         # vị trí khớp so với khớp của bộ phận cha (px, trong hệ toạ độ cha)
    z: int
    rest: float = 0.0     # góc nghỉ


class Character:
    def __init__(self, folder: Path):
        rig = json.loads((folder / "rig.json").read_text(encoding="utf-8"))
        self.name = rig.get("name", folder.name)
        self.height = rig.get("height", 700)
        self.parts: Dict[str, Part] = {}
        for p in rig["parts"]:
            self.parts[p["name"]] = Part(p["name"], Image.open(folder / p["image"]).convert("RGBA"),
                                         tuple(p["pivot"]), p.get("parent"), tuple(p.get("offset", (0, 0))),
                                         p.get("z", 0), p.get("rest", 0.0))
        # biến thể mặt: {"eyes": {"mo": "eyes_open.png", ...}, "mouth": {...}}
        self.face = {slot: {k: Image.open(folder / v).convert("RGBA") for k, v in variants.items()}
                     for slot, variants in rig.get("face", {}).items()}
        self.face_anchor = {slot: tuple(v) for slot, v in rig.get("face_anchor", {}).items()}
        self.expressions = rig.get("expressions", {})
        self.root = next(n for n, p in self.parts.items() if p.parent is None)
        self.hand = rig.get("hand")
        self.stature = rig.get("stature", 1.0)
        self.gender = rig.get("gender", "nam")
        self.role = rig.get("role", "")   # {"part": "forearm_r", "point": [x, y]} — điểm cầm đạo cụ

    # ---------- tư thế ----------
    @staticmethod
    def pose_at(action: str, t: float) -> dict:
        a = ACTIONS.get(action, ACTIONS["dung"])
        keys = a["keys"]
        span = keys[-1][0]
        if a.get("loop") and span > 0:
            t = t % span
        t = min(t, span)
        for (t0, p0), (t1, p1) in zip(keys, keys[1:]):
            if t0 <= t <= t1:
                u = 0 if t1 == t0 else (t - t0) / (t1 - t0)
                u = u * u * (3 - 2 * u)   # ease in-out
                joints = set(p0) | set(p1)
                return {j: p0.get(j, 0) + (p1.get(j, 0) - p0.get(j, 0)) * u for j in joints}
        return dict(keys[-1][1])

    def render(self, action: str, t: float, mouth_open: float = 0.0, expression: str = "",
               flip: bool = False, scale: float = 1.0, prop: Optional[Image.Image] = None) -> Image.Image:
        """Trả về ảnh RGBA của nhân vật, gốc toạ độ = bàn chân ở giữa đáy ảnh."""
        pose = self.pose_at(action, t)
        expression = expression or ACTIONS.get(action, {}).get("expression", "")
        size = int(self.height * 1.9)
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        origin = (size / 2, size * 0.78)
        world = {}

        def transform(name):
            if name in world:
                return world[name]
            p = self.parts[name]
            ang = p.rest + pose.get(name, 0.0)
            if p.parent is None:
                pos, total = origin, ang
            else:
                ppos, pang = transform(p.parent)
                r = math.radians(pang)
                ox, oy = p.offset
                pos = (ppos[0] + ox * math.cos(r) - oy * math.sin(r),
                       ppos[1] + ox * math.sin(r) + oy * math.cos(r))
                total = pang + ang
            world[name] = (pos, total)
            return world[name]

        for name in sorted(self.parts, key=lambda n: self.parts[n].z):
            p = self.parts[name]
            pos, ang = transform(name)
            img = p.image
            if name == "head" and self.face:
                img = self._face(img, t, mouth_open, expression)
            self._paste_rotated(canvas, img, p.pivot, pos, ang)
            if prop is not None and self.hand and name == self.hand["part"]:
                hx, hy = self.hand["point"]
                r = math.radians(ang)
                dx, dy = hx - p.pivot[0], hy - p.pivot[1]
                hp = (pos[0] + dx * math.cos(r) - dy * math.sin(r), pos[1] + dx * math.sin(r) + dy * math.cos(r))
                # đạo cụ: điểm cầm = giữa-đáy ảnh đạo cụ, giữ gần thẳng đứng (xoay 30% theo tay)
                self._paste_rotated(canvas, prop, (prop.width // 2, int(prop.height * 0.8)), hp, ang * 0.3)
        bbox = canvas.getbbox() or (0, 0, 1, 1)
        out = canvas
        if flip:
            out = out.transpose(Image.FLIP_LEFT_RIGHT)
        if scale != 1.0:
            out = out.resize((int(out.width * scale), int(out.height * scale)), Image.LANCZOS)
        return out

    @staticmethod
    def _paste_rotated(canvas, img, pivot, pos, ang):
        # xoay quanh pivot: mở rộng ảnh sao cho pivot nằm ở tâm rồi rotate
        w, h = img.size
        px, py = int(round(pivot[0])), int(round(pivot[1]))
        R = int(math.hypot(max(px, w - px), max(py, h - py))) + 2
        big = Image.new("RGBA", (2 * R, 2 * R), (0, 0, 0, 0))
        big.paste(img, (R - px, R - py))
        rot = big.rotate(-ang, resample=Image.BICUBIC)
        canvas.alpha_composite(rot, (int(pos[0] - R), int(pos[1] - R)))

    def _face(self, head, t, mouth_open, expression):
        head = head.copy()
        exp = self.expressions.get(expression, {})
        blink = (t % 3.2) < 0.12
        eyes = "nham" if blink and "nham" in self.face.get("eyes", {}) else exp.get("eyes", "mo")
        if mouth_open > 0.55:
            mouth = exp.get("mouth_talk_big", "to")
        elif mouth_open > 0.2:
            mouth = exp.get("mouth_talk", "vua")
        else:
            mouth = exp.get("mouth", "ngam")
        for slot, key in (("brows", exp.get("brows", "binh_thuong")), ("eyes", eyes), ("mouth", mouth),
                          ("glasses", "on")):
            variants = self.face.get(slot, {})
            v = variants.get(key) or next(iter(variants.values()), None)
            if v is not None:
                ax, ay = self.face_anchor.get(slot, (head.width // 2, head.height // 2))
                head.alpha_composite(v, (int(ax - v.width / 2), int(ay - v.height / 2)))
        return head


def load(name: str) -> Character:
    folder = CHAR_DIR / name
    if not (folder / "rig.json").exists():
        from . import cast
        look = next((l for l in cast.CAST if l.key == name), None)
        if look is not None:
            cast.build(look)
        elif name == "mau":
            make_sample(folder)
        else:
            raise FileNotFoundError(f"Không thấy nhân vật {folder}")
    return Character(folder)


def available() -> List[str]:
    from . import cast
    names = sorted(p.name for p in CHAR_DIR.glob("*") if (p / "rig.json").exists()) if CHAR_DIR.exists() else []
    return [l.key for l in cast.CAST] + [n for n in names if n not in {l.key for l in cast.CAST}]


def mouth_envelope(wav_path: str, fps: int) -> np.ndarray:
    """Độ mở miệng 0..1 cho từng khung hình, từ âm lượng giọng đọc (lip-sync đơn giản)."""
    with wave.open(wav_path, "rb") as wf:
        sr, n = wf.getframerate(), wf.getnframes()
        a = np.frombuffer(wf.readframes(n), dtype=np.int16).astype(np.float32) / 32768
    hop = max(1, sr // fps)
    frames = len(a) // hop
    rms = np.array([np.sqrt(np.mean(a[i * hop:(i + 1) * hop] ** 2)) for i in range(frames)])
    if rms.max() > 0:
        rms = rms / np.percentile(rms[rms > 0], 90) if (rms > 0).any() else rms
    return np.clip(rms, 0, 1)


# ---------------- Nhân vật mẫu (vẽ bằng code — THAY bằng bản vẽ của bạn) ----------------
def make_sample(folder: Path, skin="#FFD7B5", shirt="#2D7DD2", pants="#1B2A41", line="#1B1B1B") -> None:
    folder.mkdir(parents=True, exist_ok=True)
    LW = 8

    def part(fname, size, draw_fn):
        im = Image.new("RGBA", size, (0, 0, 0, 0))
        draw_fn(ImageDraw.Draw(im), size)
        im.save(folder / fname)

    def limb(color, w, h):
        return lambda d, s: d.rounded_rectangle([LW, LW, s[0] - LW, s[1] - LW], radius=w // 2,
                                                fill=color, outline=line, width=LW)
    part("body.png", (190, 260), lambda d, s: d.rounded_rectangle([LW, LW, s[0] - LW, s[1] - LW], 70,
                                                                  fill=shirt, outline=line, width=LW))
    part("head.png", (250, 250), lambda d, s: d.ellipse([LW, LW, s[0] - LW, s[1] - LW], fill=skin,
                                                        outline=line, width=LW))
    part("arm.png", (60, 140), limb(shirt, 60, 140))
    part("forearm.png", (54, 130), lambda d, s: (limb(skin, 54, 130)(d, s)))
    part("leg.png", (70, 200), limb(pants, 70, 200))
    # biến thể mặt
    def eyes(kind):
        def f(d, s):
            for cx in (45, 125):
                if kind == "nham":
                    d.line([cx - 20, 40, cx + 20, 40], fill=line, width=8)
                elif kind == "to":
                    d.ellipse([cx - 26, 14, cx + 26, 66], fill="white", outline=line, width=6)
                    d.ellipse([cx - 9, 31, cx + 9, 49], fill=line)
                elif kind == "nheo":
                    d.arc([cx - 22, 22, cx + 22, 62], 200, 340, fill=line, width=8)
                else:
                    d.ellipse([cx - 17, 23, cx + 17, 57], fill=line)
                    d.ellipse([cx - 5, 28, cx + 5, 38], fill="white")
        return f
    def mouth(kind):
        def f(d, s):
            if kind == "ngam":
                d.arc([20, 0, 100, 50], 20, 160, fill=line, width=8)
            elif kind == "vua":
                d.ellipse([35, 10, 85, 45], fill="#7A1F1F", outline=line, width=6)
            elif kind == "to":
                d.ellipse([28, 2, 92, 58], fill="#7A1F1F", outline=line, width=6)
            elif kind == "buon":
                d.arc([20, 25, 100, 75], 200, 340, fill=line, width=8)
            elif kind == "cuoi":
                d.chord([20, -10, 100, 55], 0, 180, fill="#7A1F1F", outline=line, width=6)
        return f
    def brows(kind):
        def f(d, s):
            for cx, sgn in ((45, 1), (125, -1)):
                if kind == "cau":
                    d.line([cx - 20, 20 - 8 * sgn, cx + 20, 20 + 8 * sgn], fill=line, width=8)
                elif kind == "nhuong":
                    d.line([cx - 20, 14, cx + 20, 8], fill=line, width=8)
                elif kind == "buon":
                    d.line([cx - 20, 20 + 8 * sgn, cx + 20, 20 - 8 * sgn], fill=line, width=8)
                else:
                    d.line([cx - 20, 18, cx + 20, 18], fill=line, width=8)
        return f
    face = {"eyes": {}, "mouth": {}, "brows": {}}
    for k in ("mo", "nham", "to", "nheo"):
        part(f"eyes_{k}.png", (170, 80), eyes(k)); face["eyes"][k] = f"eyes_{k}.png"
    for k in ("ngam", "vua", "to", "buon", "cuoi"):
        part(f"mouth_{k}.png", (120, 80), mouth(k)); face["mouth"][k] = f"mouth_{k}.png"
    for k in ("binh_thuong", "cau", "nhuong", "buon"):
        part(f"brows_{k}.png", (170, 40), brows(k)); face["brows"][k] = f"brows_{k}.png"
    rig = {
        "name": "Nhân vật mẫu", "height": 700,
        "parts": [
            {"name": "body", "image": "body.png", "pivot": [95, 240], "parent": None, "z": 3},
            {"name": "leg_l", "image": "leg.png", "pivot": [35, 20], "parent": "body", "offset": [-45, -10], "z": 1},
            {"name": "leg_r", "image": "leg.png", "pivot": [35, 20], "parent": "body", "offset": [45, -10], "z": 1},
            {"name": "head", "image": "head.png", "pivot": [125, 235], "parent": "body", "offset": [0, -230], "z": 5},
            {"name": "arm_l", "image": "arm.png", "pivot": [30, 25], "parent": "body", "offset": [-80, -205], "z": 2, "rest": 10},
            {"name": "forearm_l", "image": "forearm.png", "pivot": [27, 20], "parent": "arm_l", "offset": [0, 100], "z": 2},
            {"name": "arm_r", "image": "arm.png", "pivot": [30, 25], "parent": "body", "offset": [80, -205], "z": 6, "rest": -10},
            {"name": "forearm_r", "image": "forearm.png", "pivot": [27, 20], "parent": "arm_r", "offset": [0, 100], "z": 6},
        ],
        "face": face,
        "face_anchor": {"brows": [125, 70], "eyes": [125, 115], "mouth": [125, 180]},
        "expressions": {
            "vui": {"eyes": "nheo", "mouth": "cuoi", "mouth_talk": "cuoi", "brows": "nhuong"},
            "soc": {"eyes": "to", "mouth": "to", "brows": "nhuong"},
            "buon": {"mouth": "buon", "brows": "buon"},
            "gian": {"brows": "cau", "mouth": "ngam"},
            "nghi": {"eyes": "nheo", "brows": "cau"},
        },
    }
    (folder / "rig.json").write_text(json.dumps(rig, ensure_ascii=False, indent=2), encoding="utf-8")
