"""📅 THỬ THÁCH 30 NGÀY — lịch học 30 bài nối tiếp, mỗi ngày 1 short có huy hiệu "NGÀY N/30".

Lịch lưu ở projects/_challenge/<slug>-<lang>/lich.json; bài của từng ngày lưu cạnh đó (ngay_07.json).
Lịch sinh bằng LLM (Ollama) hoặc lấy khung mặc định theo tuần (không cần LLM).
"""
import json
from pathlib import Path
from typing import List, Optional

from . import lesson as lessonmod
from .config import PROJECTS
from .curriculum import LEVEL_NAMES, LEVEL_VI
from .langs import LANGS
from .lesson import level_num
from .pipeline import slug

WEEKS = [   # khung mặc định: tuần 1 sinh tồn → tuần 4 tự tin trò chuyện
    ["Chào hỏi", "Giới thiệu bản thân", "Cảm ơn & xin lỗi", "Số đếm 1-10", "Hỏi giá", "Gọi món", "Ôn tập tuần 1"],
    ["Hỏi đường", "Đi taxi / xe buýt", "Khách sạn check-in", "Mua sắm quần áo", "Siêu thị / tạp hoá",
     "Quán cà phê", "Ôn tập tuần 2"],
    ["Thời gian & hẹn giờ", "Sở thích", "Thời tiết", "Gia đình", "Công việc", "Đi khám bệnh", "Ôn tập tuần 3"],
    ["Nhắn tin với bạn", "Rủ đi chơi", "Khen ngợi", "Kể chuyện hôm qua", "Kế hoạch cuối tuần", "Phỏng vấn nhẹ",
     "Ôn tập tuần 4"],
    ["Tổng ôn 30 ngày", "Tốt nghiệp thử thách!"],
]


def folder(topic: str, lang: str) -> Path:
    d = PROJECTS / "_challenge" / f"{slug(topic)}-{lang}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def default_plan(topic: str) -> List[dict]:
    days = [t for w in WEEKS for t in w][:30]
    return [{"day": i + 1, "topic": f"{topic} — {t}" if topic else t, "goal": f"Nói được 3 câu về: {t}"}
            for i, t in enumerate(days)]


def make_plan(topic: str, lang: str, level: str = "người mới bắt đầu", use_llm: bool = False,
              model: str = "qwen2.5:7b", host: str = "http://localhost:11434") -> List[dict]:
    days = default_plan(topic)
    if use_llm:
        import requests
        from .script import _extract_json
        prompt = (f"Lập lịch THỬ THÁCH 30 NGÀY học {LANGS[lang].name_vi} cho người Việt, chủ đề lớn \"{topic}\", "
                  f"trình độ {LEVEL_VI[level_num(level) - 1]} ({LEVEL_NAMES[lang][level_num(level) - 1]}). Mỗi ngày 1 chủ đề nhỏ, khó dần, ngày 7/14/21/28 là ôn tập, ngày 30 là tổng kết. "
                  "Chỉ trả JSON: {\"days\":[{\"day\":1,\"topic\":\"...\",\"goal\":\"nói được ...\"}, ...]}")
        r = requests.post(f"{host}/api/generate", json={"model": model, "prompt": prompt, "stream": False,
                                                        "format": "json"}, timeout=600)
        r.raise_for_status()
        got = _extract_json(r.json()["response"]).get("days", [])
        if len(got) >= 30:
            days = [{"day": i + 1, "topic": d.get("topic", ""), "goal": d.get("goal", "")} for i, d in enumerate(got[:30])]
    (folder(topic, lang) / "lich.json").write_text(json.dumps({"topic": topic, "lang": lang, "days": days},
                                                              ensure_ascii=False, indent=2), encoding="utf-8")
    return days


def load_plan(topic: str, lang: str) -> Optional[List[dict]]:
    f = folder(topic, lang) / "lich.json"
    return json.loads(f.read_text(encoding="utf-8"))["days"] if f.exists() else None


def day_lesson(topic: str, lang: str, day: int, level: str = "người mới bắt đầu", model: str = "qwen2.5:7b",
               host: str = "http://localhost:11434") -> dict:
    """Sinh (hoặc đọc lại) bài của ngày `day` theo phong cách thu_thach, gắn huy hiệu NGÀY N/30."""
    f = folder(topic, lang) / f"ngay_{day:02d}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    days = load_plan(topic, lang) or make_plan(topic, lang)
    d = days[max(0, min(29, day - 1))]
    les = lessonmod.generate(f"Ngày {day}/30: {d['topic']} ({d['goal']})", lang, level, model, host,
                             style="thu_thach")
    les.update(day=day, series="Thử thách 30 ngày")
    f.write_text(json.dumps(les, ensure_ascii=False, indent=2), encoding="utf-8")
    return les
