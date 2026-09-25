"""Kịch bản: mô hình dữ liệu, công thức kiểu The Infographics Show rút gọn cho short,
và sinh kịch bản bằng LLM chạy LOCAL qua Ollama (mã nguồn mở, tuỳ chọn).
"""
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

import requests

# Công thức 6 nhịp cho video 35–55 giây. Mỗi nhịp 1–2 cảnh, mỗi cảnh 1 câu (2–4 giây).
FORMULA = [
    ("hook", "Câu hỏi 'Điều gì xảy ra nếu...' hoặc con số gây sốc. <= 12 từ. Không chào hỏi."),
    ("dat_ban_vao", "Đặt NGƯỜI XEM vào tình huống, ngôi 'bạn'."),
    ("leo_thang_1", "Hậu quả/sự thật đầu tiên, có con số cụ thể."),
    ("leo_thang_2", "Tình huống tệ hơn / thú vị hơn."),
    ("leo_thang_3", "Cao trào."),
    ("twist", "Sự thật bất ngờ ít người biết."),
    ("ket_vong_lap", "Câu kết nối ngược về hook để người xem xem lại; hoặc câu hỏi cho phần bình luận."),
]


@dataclass
class Scene:
    text: str                       # lời đọc
    visual: str = ""                # mô tả hình (tiếng Anh cho Stable Diffusion)
    overlay: str = ""               # chữ lớn trên màn hình (con số / từ khoá), để trống nếu không cần
    beat: str = ""
    image: str = ""                 # đường dẫn ảnh (được điền khi dựng)
    # Nhân vật (để trống = cảnh không có nhân vật). Ảnh cảnh khi đó là PHÔNG NỀN.
    character: str = ""             # tên thư mục trong assets/characters (VD "mau")
    action: str = "dung"            # động tác: xem studio/character.py ACTIONS
    expression: str = ""            # vui | soc | buon | gian | nghi (trống = theo động tác)
    position: str = "giua"          # trai | giua | phai
    prop: str = ""                  # đạo cụ cầm tay: xem studio/props.py PROPS
    background: str = ""            # phông nền có sẵn: xem studio/backgrounds.py (trống = tự động/AI)
    character2: str = ""            # nhân vật thứ 2 (đứng bên phải, quay vào nhân vật 1)
    action2: str = "dung"
    expression2: str = ""
    # --- Bài học ngoại ngữ ---
    card: dict = field(default_factory=dict)     # {"lang","foreign","roman","meaning","mark": sai|dung|tu|quiz_q|quiz_a}
    speech: list = field(default_factory=list)   # [{"lang":"vi"|"en"|..., "text": "...", "speed": 1.0} | {"pause": 1.5}]
    speaker: int = 1                             # 1 hoặc 2: nhân vật nào đang nói (nhép miệng)
    voice: str = ""                              # giọng tiếng Việt riêng của cảnh (hội thoại 2 người)
    item: str = ""                               # đồ vật đang được nói tới / chỉ tay vào (xem studio/props.py)
    price: str = ""                              # thẻ giá cạnh đồ vật, VD "3.000원", "¥15", "$2.50"
    # Màn slide cho video dài: {"kind": title|toc|chapter|recap|outro, "title", "subtitle", "items", "lang"}
    slide: dict = field(default_factory=dict)
    caption_span: list = field(default_factory=list)   # [start, end] đoạn lời tiếng Việt (điền khi dựng)
    native_spans: list = field(default_factory=list)   # [[start, end], ...] đoạn giọng bản ngữ
    audio: str = ""
    duration: float = 0.0


@dataclass
class Project:
    title: str
    language: str = "vi"            # "vi" | "en"
    topic: str = ""
    scenes: List[Scene] = field(default_factory=list)
    description: str = ""
    hashtags: List[str] = field(default_factory=list)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Project":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    @classmethod
    def from_dict(cls, d: dict) -> "Project":
        d = dict(d)
        d["scenes"] = [Scene(**{k: v for k, v in s.items() if k in Scene.__dataclass_fields__})
                       for s in d.get("scenes", [])]
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


PROMPT = """Bạn là biên kịch cho kênh video ngắn giải thích theo phong cách The Infographics Show.
Viết kịch bản video dọc {seconds} giây bằng {lang} về chủ đề: "{topic}".

Quy tắc:
- Theo đúng các nhịp sau, mỗi nhịp 1-2 cảnh:
{beats}
- Mỗi cảnh là MỘT câu ngắn (8-16 từ), đọc mất 2-4 giây. Tổng {min_scenes}-{max_scenes} cảnh.
- Dùng ngôi "bạn", giọng kể hấp dẫn, có con số cụ thể, KHÔNG bịa số liệu nếu không chắc — khi đó dùng "ước tính".
- "visual": mô tả MỘT hình minh hoạ đơn giản bằng TIẾNG ANH (nhân vật, vật thể, bối cảnh), không có chữ.
- "overlay": 1-4 từ hoặc con số in lớn trên màn hình (có thể để trống).
- "character": nhân vật chính của cảnh, chọn trong: {chars} ("bo" là người dẫn chuyện).
- "action": động tác, chọn MỘT trong: {actions}.
- "prop": đạo cụ cầm tay (có thể trống), chọn trong: {props}.
- "background": phông nền, chọn trong: {bgs}.
- Cảnh đối thoại/đối đầu: thêm "character2" và "action2".
- "visual": khi có nhân vật, mô tả PHÔNG NỀN/bối cảnh (không vẽ người).

Chỉ trả về JSON hợp lệ, không giải thích:
{{"title": "...", "description": "...", "hashtags": ["#..."],
 "scenes": [{{"beat": "hook", "text": "...", "visual": "...", "overlay": "...", "character": "bo", "action": "bat_ngo", "prop": "", "background": "thanh_pho"}}]}}"""


def build_prompt(topic: str, language: str = "vi", seconds: int = 45) -> str:
    beats = "\n".join(f"  {i + 1}. {b}: {d}" for i, (b, d) in enumerate(FORMULA))
    n = max(8, round(seconds / 3.2))
    from .backgrounds import BACKGROUNDS
    from .cast import CAST
    from .character import ACTION_LABELS
    from .props import PROPS
    return PROMPT.format(actions=", ".join(ACTION_LABELS), chars=", ".join(l.key for l in CAST),
                         props=", ".join(PROPS), bgs=", ".join(BACKGROUNDS), topic=topic, seconds=seconds, beats=beats, min_scenes=n - 2, max_scenes=n + 2,
                         lang="tiếng Việt" if language == "vi" else "English")


def _extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("LLM không trả về JSON")
    return json.loads(m.group(0))


def generate_with_ollama(topic: str, language: str = "vi", seconds: int = 45,
                         model: str = "qwen2.5:7b", host: str = "http://localhost:11434") -> Project:
    """Cần cài Ollama (https://ollama.com) và `ollama pull qwen2.5:7b` (hoặc model khác)."""
    r = requests.post(f"{host}/api/generate", json={
        "model": model, "prompt": build_prompt(topic, language, seconds), "stream": False,
        "format": "json", "options": {"temperature": 0.8}}, timeout=600)
    r.raise_for_status()
    d = _extract_json(r.json()["response"])
    d.setdefault("title", topic)
    return Project.from_dict({**d, "topic": topic, "language": language})


def template(topic: str, language: str = "vi") -> Project:
    """Khung kịch bản trống theo công thức — để tự viết khi không dùng LLM."""
    hints = {b: d for b, d in FORMULA}
    return Project(title=topic, topic=topic, language=language, scenes=[
        Scene(beat=b, text=f"[{hints[b]}]", visual="", overlay="") for b, _ in FORMULA])


def ollama_models(host: str = "http://localhost:11434") -> Optional[list]:
    try:
        return [m["name"] for m in requests.get(f"{host}/api/tags", timeout=3).json()["models"]]
    except Exception:  # noqa: BLE001 - Ollama chưa chạy
        return None
