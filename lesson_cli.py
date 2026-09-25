"""Dựng video bài học ngoại ngữ.

  python lesson_cli.py examples/lessons/cafe_ko.json            # 1 bài
  python lesson_cli.py examples/lessons/                       # cả thư mục → mỗi ngôn ngữ vào kênh riêng
  python lesson_cli.py --generate "đi siêu thị" --langs en,zh,ko  # sinh bằng Ollama rồi dựng cả 3 kênh
"""
import argparse
import json
from pathlib import Path

from studio import lesson
from studio.config import PROJECTS, RenderOptions
from studio.langs import LANGS
from studio.pipeline import build


def build_one(data: dict, vi_voice: str, voice_b: str = "", voice_n: str = "", quality: str = "fullhd",
              native: str = "auto", one_voice: bool = True) -> dict:
    L = LANGS[data["lang"]]
    proj = lesson.to_project(data, vi_voice, voice_b, voice_n, native, one_voice)
    return build(proj, next((s.voice for s in proj.scenes if s.voice), "vieneu:Hải Đăng"), "card", RenderOptions(watermark=L.handle, quality=quality), speed=1.0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?")
    ap.add_argument("--generate", help="chủ đề để sinh bài bằng Ollama")
    ap.add_argument("--langs", default="en,zh,ko")
    ap.add_argument("--level", default="người mới bắt đầu")
    ap.add_argument("--model", default="qwen2.5:7b")
    ap.add_argument("--vi-voice", default="auto", help="giọng Việt của A ('auto' = theo giới tính nhân vật)")
    ap.add_argument("--vi-voice-b", default="auto", help="giọng Việt của B")
    ap.add_argument("--vi-voice-n", default="auto", help="giọng người dẫn N (không xuất hiện)")
    ap.add_argument("--style", default="hoi_thoai", help="phong cách dạy khi --generate (xem studio/teach_styles.py)")
    ap.add_argument("--quality", default="fullhd", choices=["fullhd", "nhap"])
    ap.add_argument("--native", default="auto", choices=["auto", "qwen", "piper"],
                    help="module giọng bản ngữ khi tắt --one-voice")
    ap.add_argument("--no-one-voice", action="store_true",
                    help="TẮT chế độ 1 nhân vật = 1 giọng (dùng giọng bản ngữ riêng cho câu ngoại ngữ)")
    a = ap.parse_args()
    items = []
    if a.generate:
        for lg in a.langs.split(","):
            d = lesson.generate(a.generate, lg, a.level, a.model, style=a.style)
            out = PROJECTS / "_lessons" / f"{a.generate}_{lg}.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            print("Đã sinh", out, "— HÃY KIỂM TRA lại câu chữ trước khi đăng!")
            items.append(d)
    elif a.path:
        p = Path(a.path)
        items = [lesson.load(f) for f in (sorted(p.glob("*.json")) if p.is_dir() else [p])]
    for d in items:
        res = build_one(d, a.vi_voice, a.vi_voice_b, a.vi_voice_n, a.quality, a.native, not a.no_one_voice)
        print(f"[{d['lang']}] {res['video']} ({res['duration']:.1f}s)")
