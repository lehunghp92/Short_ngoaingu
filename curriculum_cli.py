"""Khung nội dung 10 định dạng × 5 level × 3 ngôn ngữ.

  python curriculum_cli.py doc                          # xuất CURRICULUM.md
  python curriculum_cli.py fetch                        # tải trước danh sách từ HSK/TOPIK/CEFR (cần mạng 1 lần)
  python curriculum_cli.py brief phat_am ko 3 "đi chợ"  # xem đề cương sẽ gửi cho LLM
  python curriculum_cli.py series chat zh 2 --n 10 [--gen --model qwen2.5:7b]   # lên danh sách tập (và sinh bằng LLM)
"""
import argparse
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

from studio import curriculum, lesson, resources  # noqa: E402
from studio.config import PROJECTS, ROOT  # noqa: E402
from studio.pipeline import slug  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("cmd", choices=["doc", "fetch", "brief", "series"])
ap.add_argument("fmt", nargs="?")
ap.add_argument("lang", nargs="?")
ap.add_argument("level", nargs="?", type=int, default=1)
ap.add_argument("topic", nargs="?", default="")
ap.add_argument("--n", type=int, default=10)
ap.add_argument("--gen", action="store_true")
ap.add_argument("--examples", action="store_true", help="kèm câu mẫu thật từ Tatoeba")
ap.add_argument("--model", default="qwen2.5:7b")
a = ap.parse_args()

if a.cmd == "doc":
    curriculum.write_doc(ROOT / "CURRICULUM.md")
    print("Đã ghi CURRICULUM.md")
elif a.cmd == "fetch":
    for lg in ("en", "zh", "ko"):
        print(lg, len(resources.wordlist(lg)), "từ")
elif a.cmd == "brief":
    print(curriculum.brief(a.fmt, a.lang, a.level, a.topic, with_examples=a.examples))
else:
    eps = curriculum.episodes(a.fmt, a.lang, a.level, a.n)
    for e in eps:
        print(f"#{e['episode']:02d} {e['series']} — {e['topic']}")
        if a.gen:
            d = lesson.generate(e["topic"], a.lang, a.level, a.model, style=a.fmt, use_examples=a.examples)
            d.update(series=e["series"], episode=e["episode"])
            f = PROJECTS / "_lessons" / f"{slug(e['series'])}-{e['episode']:02d}_{a.lang}.json"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            print("   →", f, "· vượt level:", d.get("level_check", {}).get("ratio"))
