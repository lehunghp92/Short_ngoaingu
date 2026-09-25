"""DỰNG HÀNG LOẠT + BÁO CÁO — chạy trên máy có GPU để kiểm tra giọng Qwen & tốc độ.

  python batch_render.py                                   # 8 kịch bản mẫu trong examples/lessons/formats10
  python batch_render.py examples/lessons/giao_tiep/*.json --quality nhap
  python batch_render.py --native piper --no-one-voice     # máy không có Qwen: giọng Piper (nhanh, để thử bố cục)

Kết quả ở projects/_batch/<thời gian>/:
  bao_cao.md / bao_cao.csv : mỗi video — thời lượng ước lượng vs thực tế, thời gian dựng, tốc độ (x thời gian thực),
                             giọng từng nhân vật, cảnh báo rà soát (nếu có)
  *.mp4                    : bản sao các video để xem nhanh
Trước khi dựng, mỗi kịch bản được rà soát bằng quy tắc (studio/review.py); lỗi nặng → bỏ qua file đó.
"""
import argparse
import csv
import glob
import json
import shutil
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from studio import gpu, lesson, review, tts  # noqa: E402
from studio.config import PROJECTS, RenderOptions  # noqa: E402
from studio.langs import LANGS  # noqa: E402
from studio.pipeline import build  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("files", nargs="*")
ap.add_argument("--quality", default="fullhd", choices=["fullhd", "nhap"])
ap.add_argument("--native", default="auto", help="auto | qwen | piper — giọng bản ngữ khi tắt one-voice")
ap.add_argument("--no-one-voice", action="store_true", help="không nhân bản giọng Việt sang ngoại ngữ")
ap.add_argument("--vi-engine", default="vieneu", choices=["vieneu", "omnivoice"])
ap.add_argument("--speed", type=float, default=1.0)
a = ap.parse_args()

files = sorted(a.files or glob.glob("examples/lessons/formats10/*.json"))
out = PROJECTS / "_batch" / datetime.now().strftime("%Y%m%d-%H%M")
out.mkdir(parents=True, exist_ok=True)
one_voice = not a.no_one_voice
qwen = tts.engine_available("qwen")
if one_voice and not qwen:
    print("⚠️  Chưa cài Qwen3-TTS → không nhân bản được giọng; chuyển sang giọng bản ngữ riêng (--no-one-voice).")
    one_voice = False

env = {"GPU (PyTorch CUDA)": gpu.cuda_info() or "không", "Mã hoá NVENC": "có" if gpu.nvenc_ok() else "không (CPU)",
       "Qwen3-TTS": "đã cài" if qwen else "chưa cài", "1 nhân vật = 1 giọng": "bật" if one_voice else "tắt",
       "Giọng Việt": a.vi_engine, "Chất lượng": a.quality}
print("\n".join(f"{k:22}: {v}" for k, v in env.items()), flush=True)

rows = []
for f in files:
    d = json.loads(Path(f).read_text(encoding="utf-8"))
    d.setdefault("lang", Path(f).stem.rpartition("_")[2])
    issues = review.check_rules(d)
    errs = [i for i in issues if i["muc"] == "LỖI"]
    row = {"file": Path(f).name, "lang": d["lang"], "style": d.get("style", ""), "uoc_luong_s": review.estimate_seconds(d),
           "thuc_te_s": "", "dung_mat_s": "", "toc_do": "", "giong": "", "canh_bao": "; ".join(
               f"L{i['turn']}: {i['van_de']}" for i in issues), "video": "", "trang_thai": ""}
    if errs:
        row["trang_thai"] = "BỎ QUA (lỗi kịch bản)"
        rows.append(row)
        print("✗", f, row["canh_bao"], flush=True)
        continue
    try:
        t0 = time.time()
        proj = lesson.to_project(d, "auto", "auto", "auto", a.native, one_voice, a.vi_engine)
        voices = {}
        for s in proj.scenes:
            who = {1: "A", 2: "B"}.get(s.speaker, "N")
            voices.setdefault(who, s.voice)
        res = build(proj, proj.scenes[0].voice or f"{a.vi_engine}:Hải Đăng", "card",
                    RenderOptions(watermark=LANGS[d["lang"]].handle, quality=a.quality), speed=a.speed,
                    progress=lambda p, m: None)
        dt = time.time() - t0
        dst = out / Path(res["video"]).name
        shutil.copy(res["video"], dst)
        dur = res["duration"]
        row.update(thuc_te_s=round(dur, 1), dung_mat_s=round(dt, 1), toc_do=f"{dur / dt:.2f}x",
                   giong=", ".join(f"{k}={v}" for k, v in sorted(voices.items())), video=dst.name,
                   trang_thai="OK" if 40 <= dur <= 50 else ("NGẮN" if dur < 40 else "DÀI"))
        print(f"✓ {f}: {dur:.1f}s video, dựng {dt:.0f}s ({dur / dt:.2f}x thời gian thực)", flush=True)
    except Exception as e:  # noqa: BLE001
        row["trang_thai"] = f"LỖI: {e}"
        traceback.print_exc()
    rows.append(row)

with open(out / "bao_cao.csv", "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
ok = [r for r in rows if r["dung_mat_s"]]
tot_v, tot_t = sum(r["thuc_te_s"] for r in ok), sum(r["dung_mat_s"] for r in ok)
md = ["# Báo cáo dựng hàng loạt", "", f"*{datetime.now():%d/%m/%Y %H:%M}*", ""]
md += [f"- **{k}**: {v}" for k, v in env.items()]
if ok:
    md += [f"- **Tổng**: {len(ok)} video, {tot_v:.0f}s video trong {tot_t:.0f}s ({tot_v / tot_t:.2f}x thời gian thực, "
           f"~{tot_t / len(ok):.0f}s/video)"]
md += ["", "| Kịch bản | Ước lượng | Thực tế | Dựng mất | Tốc độ | Trạng thái | Giọng |", "|---|---|---|---|---|---|---|"]
md += [f"| {r['file']} | {r['uoc_luong_s']}s | {r['thuc_te_s']}s | {r['dung_mat_s']}s | {r['toc_do']} | {r['trang_thai']} | "
       f"{r['giong']} |" for r in rows]
warn = [r for r in rows if r["canh_bao"]]
if warn:
    md += ["", "## Cảnh báo rà soát", ""] + [f"- **{r['file']}**: {r['canh_bao']}" for r in warn]
(out / "bao_cao.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print(f"\nBáo cáo: {out / 'bao_cao.md'}")
