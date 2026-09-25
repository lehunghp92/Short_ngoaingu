"""Dựng video từ dòng lệnh:  python cli.py examples/khong_ngu_11_ngay.json --voice "vi-vais1000 (Việt, nữ)" """
import argparse

from studio.config import RenderOptions
from studio.pipeline import build
from studio.script import Project
from studio.tts import available_voices

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--voice", default=available_voices()[0], choices=available_voices())
    ap.add_argument("--images", default="card", choices=["card", "sd"])
    ap.add_argument("--style", default="infographic")
    ap.add_argument("--watermark", default="")
    ap.add_argument("--music", default="")
    a = ap.parse_args()
    res = build(Project.load(a.project), a.voice, a.images,
                RenderOptions(style=a.style, watermark=a.watermark, music=a.music))
    print(res)
