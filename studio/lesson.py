"""Bài học ngoại ngữ dạng short (Anh / Trung / Hàn) → danh sách cảnh cho bộ dựng video.

Mỗi bài học = 1 file JSON cho 1 ngôn ngữ (1 kênh). Cấu trúc video (20-45 giây):
  hook → [sai/đúng | từ vựng | hội thoại | quiz]... → kết (kêu gọi lưu/bình luận)
Giọng: lời giảng tiếng Việt + giọng BẢN NGỮ đọc câu mẫu 2 lần (thường, rồi chậm).
"""
import json
import re
from pathlib import Path
from typing import List

from .langs import LANGS
from .script import Project, Scene

NARRATOR, FRIEND = "bo", "mai"
BG_BY_TOPIC = {"cafe": "quan_ca_phe", "an": "phong_khach", "du_lich": "thanh_pho", "cong_so": "van_phong",
               "mua_sam": "thanh_pho", "truong": "phong_thi_nghiem"}


_CJK_PUNCT = str.maketrans({"。": ".", "，": ",", "？": "?", "！": "!", "：": ":", "；": ";", "、": ","})


def _roman(lang: str, text: str) -> str:
    try:
        out = LANGS[lang].romanize(text).translate(_CJK_PUNCT)
        return " ".join(out.replace(" .", ".").replace(" ,", ",").replace(" ?", "?").split())
    except Exception:  # noqa: BLE001 - thiếu thư viện phiên âm
        return ""


def _native(lang, text, speed=1.0):
    return {"lang": lang, "text": text, "speed": speed}


def _vi(text):
    return {"lang": "vi", "text": text, "speed": 1.1}


def expand(lesson: dict) -> Project:
    lang = lesson["lang"]
    L = LANGS[lang]
    bg = lesson.get("background") or BG_BY_TOPIC.get(lesson.get("topic_key", ""), "thanh_pho")
    ep = f" #{lesson['episode']}" if lesson.get("episode") else ""
    scenes: List[Scene] = []

    def add(text, speech, card=None, **kw):
        kw.setdefault("character", NARRATOR)
        kw.setdefault("background", bg)
        scenes.append(Scene(text=text, speech=speech, card=card or {}, **kw))

    add(lesson["hook"], [_vi(lesson["hook"])], overlay=f"{lesson.get('series', '')}{ep}".strip(),
        action="bat_ngo", beat="hook")
    for it in lesson["items"]:
        t = it["type"]
        if t == "sai_dung":
            add("Đừng nói:", [_vi("Đừng nói"), _native(lang, it["wrong"])],
                {"lang": lang, "foreign": it["wrong"], "roman": _roman(lang, it["wrong"]),
                 "meaning": it.get("wrong_note", ""), "mark": "sai"}, action="run_so", beat="sai")
            add("Hãy nói: " + it["meaning"], [_vi("Hãy nói"), _native(lang, it["right"]), {"pause": 0.3},
                                              _native(lang, it["right"], 0.75), _vi(it["meaning"])],
                {"lang": lang, "foreign": it["right"], "roman": _roman(lang, it["right"]),
                 "meaning": it["meaning"], "mark": "dung"}, action="chi_tay", expression="vui", beat="dung")
            if it.get("note"):
                add(it["note"], [_vi(it["note"])], action="suy_nghi", beat="giai_thich",
                    card={"lang": lang, "foreign": it["right"], "roman": _roman(lang, it["right"]),
                          "meaning": it["meaning"], "mark": "dung"})
        elif t == "tu_vung":
            add(it["meaning"], [_native(lang, it["word"]), {"pause": 0.3}, _native(lang, it["word"], 0.75),
                                _vi(it["meaning"])],
                {"lang": lang, "foreign": it["word"], "roman": _roman(lang, it["word"]),
                 "meaning": it["meaning"], "mark": "tu"}, action="chi_tay", prop=it.get("prop", ""), beat="tu_vung")
        elif t == "hoi_thoai":
            for i, line in enumerate(it["lines"]):
                who = 1 if line.get("who", "A") == "A" else 2
                add(line["meaning"], [_native(lang, line["text"]), _vi(line["meaning"])],
                    {"lang": lang, "foreign": line["text"], "roman": _roman(lang, line["text"]),
                     "meaning": line["meaning"], "mark": "thoai"},
                    character=NARRATOR, character2=FRIEND, speaker=who,
                    action="chi_tay" if who == 1 else "dung", action2="vay_tay" if who == 2 else "dung",
                    beat="hoi_thoai")
        elif t == "quiz":
            add(it["question"], [_vi(it["question"]), {"pause": 3.0}],
                {"lang": lang, "foreign": "?", "roman": "", "meaning": it["question"], "mark": "quiz_q"},
                action="suy_nghi", beat="quiz")
            add(it["meaning"], [_native(lang, it["answer"]), {"pause": 0.3}, _native(lang, it["answer"], 0.75)],
                {"lang": lang, "foreign": it["answer"], "roman": _roman(lang, it["answer"]),
                 "meaning": it["meaning"], "mark": "dung"}, action="vui_mung", beat="quiz_dap_an")
    cta = lesson.get("cta") or "Lưu video lại để ôn nhé! Bạn muốn học chủ đề gì tiếp theo?"
    add(cta, [_vi(cta)], action="vay_tay", expression="vui", beat="ket", overlay="LƯU LẠI ĐỂ ÔN")
    tags = lesson.get("hashtags") or L.hashtags
    return Project(title=lesson["title"], language=lang, topic=lesson.get("topic", ""),
                   description=lesson.get("description", ""), hashtags=tags, scenes=scenes)


def expand_dialogue(lesson: dict, voice_a: str = "", voice_b: str = "", voice_n: str = "",
                    native_engine: str = "auto", one_voice: bool = True, vi_engine: str = "vieneu") -> Project:
    """Mọi phong cách dạy học (xem studio/teach_styles.py) → danh sách cảnh.
    A (trái) / B (phải) là nhân vật trên màn hình; N là người dẫn chỉ có giọng.
    Thẻ học được giữ lại qua các lượt nói tiếp theo để người xem kịp đọc."""
    from .character import load as load_char
    from .teach_styles import STYLES
    lang = lesson["lang"]
    L = LANGS[lang]
    style = STYLES.get(lesson.get("style", "hoi_thoai"), STYLES["hoi_thoai"])
    cast = {"A": style.cast[0] or NARRATOR, "B": style.cast[1], **lesson.get("cast", {})}
    voices = auto_voices(cast, voice_a, voice_b, voice_n, vi_engine)
    genders = {k: load_char(v).gender for k, v in cast.items() if v}
    bg = lesson.get("background") or BG_BY_TOPIC.get(lesson.get("topic_key", ""), "thanh_pho")
    ep = f" #{lesson['episode']}" if lesson.get("episode") else ""
    badge = f"NGÀY {lesson['day']}/30" if lesson.get("day") else f"{lesson.get('series', '')}{ep}".strip()
    from .langs import native_voice
    from .cast import CAST
    names = {l.key: l.name for l in CAST}

    def nat_voice(who, lg=lang):
        if one_voice:   # 1 nhân vật = 1 giọng: nhân bản giọng Việt của chính nhân vật sang ngoại ngữ
            return "clone:" + voices[who if who in voices else "A"]
        return native_voice(lg, genders.get(who, "nu"), native_engine)

    chat_app = lesson.get("chat_app") or ("kakao" if lang == "ko" else "wechat" if lang == "zh" else "imessage") \
        if style.key == "chat" else ""
    scenes, card, msgs, quiz = [], {}, [], {}
    # SHORT: không có màn mở đầu riêng — "Tập trước" chỉ là nhãn nhỏ ở cảnh đầu (không đọc)
    if lesson.get("previously"):
        badge = f"{badge} · Tập trước: {lesson['previously']}" if badge else f"Tập trước: {lesson['previously']}"
    for i, t in enumerate(lesson["turns"]):
        who = t.get("who", "A")
        speech, slide = [], None
        if t.get("sfx"):
            speech.append({"sfx": t["sfx"]})
        if t.get("say"):
            speech.append(_vi(t["say"]))
        mark = t.get("mark", "dung" if t.get("native") else "")
        nv = nat_voice(who)
        if t.get("compare"):          # 🌏 1 nghĩa – 3 ngôn ngữ
            items = []
            for c in t["compare"]:
                items.append({"lang": c["lang"], "foreign": c["text"], "roman": _roman(c["lang"], c["text"])})
                speech += [{**_native(c["lang"], c["text"]), "voice": nat_voice(who, c["lang"])}, {"pause": 0.5}]
            slide = {"kind": "compare", "meaning": t.get("meaning", ""), "items": items}
        elif t.get("anatomy"):        # 🔤 mổ xẻ chữ
            a = dict(t["anatomy"])
            a.setdefault("roman", _roman(lang, a.get("word", "")))
            if a.get("word"):
                speech += [{**_native(lang, a["word"]), "voice": nv}, {"pause": 0.4},
                           {**_native(lang, a["word"], 0.75), "voice": nv}]
            slide = {"kind": "anatomy", **a}
        elif t.get("pron"):           # 🎤 phát âm: thanh điệu / khẩu hình
            pr = dict(t["pron"])
            items = []
            for it in pr.get("items", []):
                items.append({**it, "roman": it.get("roman") or _roman(lang, it["text"])})
                speech += [{**_native(lang, it["text"], float(it.get("speed", 0.85))), "voice": nv},
                           {"pause": float(pr.get("pause", 0.8))}]
            slide = {"kind": "pron", **pr, "items": items}
        elif t.get("breakdown"):      # 🎬 câu thoại phim / lời bài hát → tách từng từ
            b = dict(t["breakdown"])
            speech += [{**_native(lang, b["sentence"]), "voice": nv}, {"pause": 0.5},
                       {**_native(lang, b["sentence"], 0.75), "voice": nv}]
            slide = {"kind": "breakdown", **b}
        elif t.get("native"):
            card = {"lang": lang, "foreign": t["native"], "roman": _roman(lang, t["native"]),
                    "meaning": t.get("meaning", ""), "mark": mark, "tag": t.get("tag", "")}
            if quiz.get("options") and mark != "quiz_q":      # công bố đáp án trắc nghiệm
                card.update(options=quiz["options"], answer=quiz.get("answer", -1), reveal=True,
                            picked=t.get("picked", quiz.get("answer", -1)), tag=t.get("tag") or quiz.get("tag", ""))
                if "sfx" not in t:
                    speech.insert(0, {"sfx": "dung" if card["picked"] == card["answer"] else "sai"})
                quiz = {}
            speech.append({**_native(lang, t["native"]), "voice": nv})
            slow_repeat = mark in ("dung", "tu") or (mark == "thoai" and style.key in ("giao_tiep", "nhap_vai"))
            if style.key == "chat":
                slow_repeat = False
                msgs.append({"text": t["native"], "meaning": t.get("meaning", ""), "roman": card["roman"],
                             "side": "me" if who == "A" else "other"})
                speech.insert(0, {"sfx": "pop"})
            if t.get("repeat", slow_repeat):
                speech += [{"pause": 0.3}, {**_native(lang, t["native"], 0.75), "voice": nv}]
            if t.get("shadow"):
                card["shadow"] = True
                speech.append({"pause": float(t["shadow"])})
        elif mark == "quiz_q":
            card = {"lang": lang, "foreign": "?", "roman": "", "meaning": t.get("say", ""), "mark": "quiz_q",
                    "tag": t.get("tag", "")}
            if t.get("options"):      # trắc nghiệm A/B/C
                card["options"] = t["options"]
                quiz = {"options": t["options"], "answer": int(t.get("answer", 0)), "tag": t.get("tag", "")}
            for _ in range(3):        # đếm ngược 3-2-1 có tiếng tích tắc
                speech += [{"sfx": "tick"}, {"pause": 0.94}]
        elif t.get("clear_card"):
            card = {}
        if style.key == "chat" and not slide and msgs:
            slide = {"kind": "chat", "app": chat_app, "messages": list(msgs[-6:]),
                     "title": names.get(cast["B"], "") if cast["B"] else "", "cast": [cast["A"], cast["B"]],
                     "speaker": 1 if who == "A" else (2 if who == "B" else 0),
                     "typing": t.get("typing", "")}
        if not speech:
            continue
        speech.append({"pause": float(t.get("gap", 0.3))})     # nghỉ ngắn giữa các lượt → nhịp tự nhiên
        on_a, on_b = who == "A", who == "B"
        act, react = t.get("action", "chi_tay"), t.get("react", "dung")
        if slide:
            slide["lang"] = lang
            slide.setdefault("cast", [cast["A"], cast["B"]])
            slide.setdefault("speaker", 1 if on_a else (2 if on_b else 0))
        scenes.append(Scene(
            text=t.get("say", ""), speech=speech, card=dict(card) if not slide else {}, beat=t.get("beat", style.key),
            background=t.get("background") or bg, prop=t.get("prop", "") if on_a else "",
            item=t.get("item", ""), price=t.get("price", ""),
            overlay=(badge if i == 0 or (slide and slide["kind"] != "chat" and badge) else t.get("overlay", "")),
            character=cast["A"], character2=cast["B"] or "",
            speaker=1 if on_a else (2 if on_b else 0), voice=voices[who if who in voices else "A"],
            action=act if on_a else react, action2=act if on_b else react,
            expression=t.get("expression", "") if on_a else "",
            expression2=t.get("expression", "") if on_b else "",
            position="giua" if not cast["B"] else "trai", slide=slide or {},
        ))
    # SHORT: không có màn kết riêng — "Tập sau" là nhãn nhỏ ở cảnh cuối (không đọc thêm)
    if lesson.get("next") and scenes:
        scenes[-1].overlay = f"Tập sau: {lesson['next']}"
    # Vào thẳng nội dung: cảnh mở đầu (chỉ lời Việt) hiện luôn thẻ nội dung đầu tiên làm "teaser"
    if scenes and not scenes[0].card and not scenes[0].slide:
        nxt = next((x for x in scenes[1:4] if x.card or x.slide), None)
        if nxt is not None and nxt.card:
            scenes[0].card = {**nxt.card, "shadow": False, "reveal": False, "teaser": True}
            if scenes[0].card.get("mark") == "quiz_q":
                scenes[0].card["meaning"] = nxt.card.get("meaning", "")
        elif nxt is not None and nxt.slide:
            scenes[0].slide = dict(nxt.slide)
    return Project(title=lesson["title"], language=lang, topic=lesson.get("topic", ""),
                   description=lesson.get("description", ""), hashtags=lesson.get("hashtags") or L.hashtags,
                   scenes=scenes)


FEMALE_VOICES = ["Trúc Ly", "Ngọc Huyền", "Mai Anh", "Đoan Trang", "Ngọc Linh"]
MALE_VOICES = ["Hải Đăng", "Thiện Minh", "Quốc Tuấn", "Xuân Vĩnh", "Adam"]
AUTO = "auto"


def auto_voices(cast: dict, voice_a: str = AUTO, voice_b: str = AUTO, voice_n: str = AUTO,
                engine: str = "vieneu") -> dict:
    """Mỗi nhân vật 1 giọng CỐ ĐỊNH, đúng giới tính, không trùng nhau trong cùng clip.
    Giọng nào để 'auto' (hoặc trống) sẽ được chọn tự động."""
    from .character import load as load_char
    chosen, used = {}, set()
    for key, given in (("A", voice_a), ("B", voice_b), ("N", voice_n)):
        if given and given != AUTO:
            chosen[key] = given
            used.add(given.split(":", 1)[-1])
    for key, given in (("A", voice_a), ("B", voice_b), ("N", voice_n)):
        if key in chosen:
            continue
        ch = cast.get(key)
        gender = load_char(ch).gender if ch else "nam"
        pool = FEMALE_VOICES if gender == "nu" else MALE_VOICES
        if key == "N":
            pool = ["Thiện Minh", "Ngọc Linh", "Thanh Bình"]      # giọng kể chuyện cho người dẫn
        name = next((n for n in pool if n not in used), pool[0])
        used.add(name)
        chosen[key] = f"{engine}:{name}"
    return chosen


def to_project(lesson: dict, voice_a: str = "", voice_b: str = "", voice_n: str = "",
               native_engine: str = "auto", one_voice: bool = True, vi_engine: str = "vieneu") -> Project:
    if "turns" in lesson:
        return expand_dialogue(lesson, voice_a, voice_b, voice_n, native_engine, one_voice, vi_engine)
    if not voice_a or voice_a == AUTO:
        voice_a = f"{vi_engine}:Hải Đăng"
    proj = expand(lesson)
    from .langs import native_voice
    for s in proj.scenes:
        for seg in s.speech:
            if seg.get("lang") not in (None, "vi") and "voice" not in seg:
                seg["voice"] = ("clone:" + voice_a) if one_voice and voice_a and voice_a != AUTO else \
                    native_voice(seg["lang"], "nu", native_engine)
    return proj


DIALOGUE_PROMPT = """Bạn viết kịch bản video short 40-50 giây dạy {lang_vi} cho người Việt, dạng HỘI THOẠI 2 nhân vật:
A = Bơ (người học, tò mò, hài hước), B = Mai (cô giáo, giỏi {lang_vi}). Chủ đề: "{topic}". Trình độ: {level}.
Quy tắc:
- 10-13 lượt nói. Lượt 1 là HOOK của A (<= 14 từ, gây tò mò, ví dụ "Mai ơi, sao người Hàn nghe mình nói xong lại cười?").
- Lời thoại tiếng Việt ("say") ngắn, tự nhiên, 5-16 từ.
- Khi dạy câu {lang_vi}, lượt đó có "native" (câu {lang_vi} CHÍNH XÁC, <= 10 từ) và "meaning" (nghĩa Việt), "mark": "dung";
  câu sai/kém tự nhiên dùng "mark": "sai". Có 1 lượt quiz: B hỏi ("mark":"quiz_q"), lượt sau A hoặc B trả lời bằng "native".
- Dạy 2-3 câu/từ, có 1 cặp sai-đúng. Lượt cuối: kêu gọi lưu video / bình luận.
- "action" chọn trong: dung, chi_tay, vay_tay, suy_nghi, bat_ngo, vui_mung, buon, run_so. "expression": vui|soc|buon|gian|nghi|"".
Chỉ trả JSON:
{{"title":"tiêu đề <= 60 ký tự","description":"...","turns":[{{"who":"A","say":"...","action":"suy_nghi"}},
{{"who":"B","say":"...","native":"...","meaning":"...","mark":"dung","action":"chi_tay"}}]}}"""


def load(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ---------------- Sinh bài học bằng LLM local (Ollama) ----------------
LESSON_PROMPT = """Bạn là giáo viên {lang_vi} cho người Việt, làm video short 30-40 giây trên TikTok/YouTube Shorts.
Chủ đề: "{topic}". Trình độ: {level}.
Tạo 1 bài học JSON gồm: hook tiếng Việt gây tò mò (<= 14 từ, ví dụ "90% người Việt nói sai câu này!"),
2-3 mục trong các loại sau, và câu kết kêu gọi lưu video.
Loại mục:
- sai_dung: {{"type":"sai_dung","wrong":"câu người Việt hay nói sai/kém tự nhiên","right":"câu tự nhiên của người bản xứ","meaning":"nghĩa tiếng Việt","note":"giải thích ngắn tiếng Việt"}}
- tu_vung: {{"type":"tu_vung","word":"...","meaning":"..."}}
- hoi_thoai: {{"type":"hoi_thoai","lines":[{{"who":"A","text":"...","meaning":"..."}},{{"who":"B","text":"...","meaning":"..."}}]}}  (2-4 câu)
- quiz: {{"type":"quiz","question":"câu hỏi tiếng Việt","answer":"đáp án {lang_vi}","meaning":"nghĩa"}}
Yêu cầu: câu {lang_vi} CHÍNH XÁC, tự nhiên, ngắn (<= 10 từ). Không phiên âm (app tự làm).
Chỉ trả JSON:
{{"title":"tiêu đề video tiếng Việt <= 60 ký tự","hook":"...","items":[...],"cta":"...","description":"..."}}"""


LEVEL_ALIASES = {"người mới bắt đầu": 1, "sơ cấp": 2, "trung cấp": 3, "trung cao cấp": 4, "cao cấp": 5}


def level_num(level) -> int:
    """'2', 2, 'Level 2 · Sơ cấp', 'sơ cấp' → 2."""
    if isinstance(level, int):
        return max(1, min(5, level))
    m = re.search(r"[1-5]", str(level))
    return int(m.group()) if m else LEVEL_ALIASES.get(str(level).strip().lower(), 1)


def generate(topic: str, lang: str, level="1", model: str = "qwen2.5:7b",
             host: str = "http://localhost:11434", dialogue: bool = True, style: str = "hoi_thoai",
             cast_a: str = "", cast_b: str = "", use_resources: bool = True, use_examples: bool = False,
             max_above: float = 0.25) -> dict:
    """Sinh bài học theo PHONG CÁCH + KHUNG NỘI DUNG level 1-5 (studio/curriculum.py) bằng LLM local (Ollama).
    Sau khi sinh, đếm từ vượt level (danh sách HSK/TOPIK/CEFR); vượt quá `max_above` → yêu cầu LLM viết lại 1 lần."""
    from .curriculum import LEVEL_NAMES, LEVEL_VI, brief
    from .resources import check_level
    import requests
    from .backgrounds import BACKGROUNDS
    from .cast import CAST
    from .props import PROPS
    from .script import _extract_json
    from .teach_styles import STYLE_PROMPT, STYLES, TURN_SCHEMA
    st = STYLES.get(style if dialogue else "giang", STYLES["hoi_thoai"])
    names = {l.key: f"{l.name} ({l.role})" for l in CAST}
    a, b = cast_a or st.cast[0], cast_b or st.cast[1]
    lv = level_num(level)
    prompt = STYLE_PROMPT.format(lang_vi=LANGS[lang].name_vi, style_name=st.name, rules=st.rules, topic=topic,
                                 level=f"{LEVEL_VI[lv - 1]} ({LEVEL_NAMES[lang][lv - 1]})", cast_a=names.get(a, a), cast_b=names.get(b, "không có") if b else "không có",
                                 hook_idea=st.hook_idea, bgs=", ".join(BACKGROUNDS), props=", ".join(PROPS),
                                 schema=TURN_SCHEMA)
    prompt += "\n\nKHUNG NỘI DUNG (bắt buộc tuân theo):\n" + brief(st.key, lang, lv, topic, use_resources, use_examples)

    def ask(p):
        r = requests.post(f"{host}/api/generate", json={"model": model, "prompt": p, "stream": False,
                                                        "format": "json", "options": {"temperature": 0.75}},
                          timeout=600)
        r.raise_for_status()
        return _extract_json(r.json()["response"])

    d = ask(prompt)
    d.update(lang=lang, topic=topic, style=st.key, cast={"A": a, "B": b}, level=lv)
    chk = check_level(d, lv) if use_resources else {}
    if chk.get("ratio", 0) > max_above and chk.get("above"):
        fix = (prompt + "\n\nBản trước dùng từ VƯỢT trình độ: " + ", ".join(chk["above"][:15]) +
               ". Viết lại toàn bộ JSON, thay các từ đó bằng từ đơn giản hơn đúng level.")
        d2 = ask(fix)
        d2.update(lang=lang, topic=topic, style=st.key, cast={"A": a, "B": b}, level=lv)
        chk2 = check_level(d2, lv)
        if chk2["ratio"] <= chk["ratio"]:
            d, chk = d2, chk2
    if chk:
        d["level_check"] = {"above": chk["above"][:20], "ratio": chk["ratio"]}
    return d
