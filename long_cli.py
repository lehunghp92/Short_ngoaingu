"""Dựng VIDEO DÀI cùng chủ đề từ dòng lệnh.

  python long_cli.py --fmt tron_chu_de --title "Tiếng Hàn đi chợ & cà phê" examples/lessons/giao_tiep/taphoa-muabanh_ko.json examples/lessons/cafe_ko.json
  python long_cli.py --fmt luyen_nghe examples/lessons/**/*_ko.json
  python long_cli.py --generate "Du lịch Hàn Quốc 5 ngày" --lang ko --parts 5 --style giao_tiep
Định dạng: tron_chu_de | phim_tinh_huong | luyen_nghe | on_tap | flashcard
"""
import argparse
import glob

from studio import lesson, longform

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--fmt", default="tron_chu_de", choices=list(longform.FORMATS))
    ap.add_argument("--title", default="")
    ap.add_argument("--generate", help="chủ đề lớn để LLM viết nhiều phần")
    ap.add_argument("--lang", default="ko")
    ap.add_argument("--parts", type=int, default=5)
    ap.add_argument("--style", default="giao_tiep")
    ap.add_argument("--layout", default="ngang", choices=["ngang", "doc"])
    ap.add_argument("--quality", default="fullhd", choices=["fullhd", "nhap"])
    ap.add_argument("--native", default="auto", choices=["auto", "qwen", "piper"])
    ap.add_argument("--no-one-voice", action="store_true")
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--per-chapter", type=int, default=10)
    a = ap.parse_args()
    if a.generate:
        lessons = longform.generate_long(a.generate, a.lang, a.parts, a.style)
    else:
        files = [f for pat in a.files for f in (glob.glob(pat, recursive=True) or [pat])]
        lessons = [lesson.load(f) for f in files]
    title = a.title or a.generate or lessons[0].get("series") or lessons[0]["title"]
    opts = longform.LongOptions(layout=a.layout, quality=a.quality, one_voice=not a.no_one_voice,
                                native_engine=a.native, repeats=a.repeats, per_chapter=a.per_chapter)
    res = longform.build_long(lessons, a.fmt, title, opts)
    print(f"\nVIDEO: {res['video']} ({res['duration'] / 60:.1f} phút)\nChương:\n{res['chapters']}")
    for k in ("srt", "thumbnail", "pdf", "description"):
        print(f"{k}: {res[k]}")
