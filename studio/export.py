"""Xuất cho nhiều nền tảng: cùng một file MP4 (H.264/AAC 1080x1920, loudness -14 LUFS phù hợp mọi nền tảng)
kèm file mô tả/hashtag viết theo quy tắc riêng từng nền tảng."""
import shutil
from pathlib import Path

from .script import Project

PLATFORMS = {
    "youtube_shorts": {"max_sec": 180, "title_max": 100, "tags": 3, "extra": "#Shorts"},
    "tiktok": {"max_sec": 600, "title_max": 2200, "tags": 5, "extra": ""},
    "instagram_reels": {"max_sec": 180, "title_max": 2200, "tags": 5, "extra": ""},
    "facebook_reels": {"max_sec": 90, "title_max": 2200, "tags": 3, "extra": ""},
}


def export_all(project: Project, video: Path, out_dir: Path, duration: float) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    tags = [t if t.startswith("#") else "#" + t for t in project.hashtags]
    results = {}
    for name, rule in PLATFORMS.items():
        if duration > rule["max_sec"]:
            results[name] = f"BỎ QUA: video {duration:.0f}s > giới hạn {rule['max_sec']}s"
            continue
        dst = out_dir / f"{name}.mp4"
        shutil.copyfile(video, dst)
        hashtags = " ".join(tags[:rule["tags"]] + ([rule["extra"]] if rule["extra"] else []))
        title = project.title[:rule["title_max"]]
        body = f"{title}\n\n{project.description}\n\n{hashtags}".strip()
        (out_dir / f"{name}.txt").write_text(body, encoding="utf-8")
        results[name] = str(dst)
    return results
