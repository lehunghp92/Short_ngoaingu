"""Shorts Studio — giao diện PC.  Chạy:  python app.py   (tự mở trình duyệt http://127.0.0.1:7860)

Tab 1: Kênh học ngoại ngữ (Anh/Trung/Hàn) — hội thoại 2 nhân vật hoặc giảng 1 người
Tab 2: Video giải thích (kiểu infographic)
Tab 3: Tài liệu kỹ thuật kênh
"""
import json
from pathlib import Path

import gradio as gr
import pandas as pd

from studio import character as charmod, images, lesson as lessonmod, tts
from studio.backgrounds import BACKGROUNDS
from studio.config import PROJECTS, ROOT, STYLES, RenderOptions
from studio.langs import LANGS
from studio.pipeline import build, slug
from studio.props import PROPS
from studio.cast import CAST
from studio.script import FORMULA, Project, Scene, generate_with_ollama, ollama_models, template
from studio.teach_styles import STYLES as TEACH
from studio import longform

LANG_CODES = ("en", "zh", "ko")
LANG_LABEL = {"en": "🇬🇧 Tiếng Anh", "zh": "🇨🇳 Tiếng Trung", "ko": "🇰🇷 Tiếng Hàn"}
LIB_DIRS = [ROOT / "examples" / "lessons", PROJECTS / "_lessons"]
CHAR_CHOICES = [(f"{l.name} — {l.role}", l.key) for l in CAST]
from studio.teach_styles import FORMATS10
from studio import challenge, curriculum, resources
LEVEL_CHOICES = [(f"{v} — Anh {curriculum.LEVEL_NAMES['en'][i]} · Trung {curriculum.LEVEL_NAMES['zh'][i]} · Hàn "
                  f"{curriculum.LEVEL_NAMES['ko'][i]}", i + 1) for i, v in enumerate(curriculum.LEVEL_VI)]
STYLE_CHOICES = [(label, key) for key, label in FORMATS10] + \
    [(f"➕ {st.name}", st.key) for st in TEACH.values() if st.key not in dict(FORMATS10)]


# ================= Thư viện kịch bản có sẵn =================
def library() -> dict:
    """{tên hiển thị: {lang: đường dẫn}} — file đặt tên <chủ-đề>_<en|zh|ko>.json"""
    lib = {}
    for folder in LIB_DIRS:
        for f in sorted(folder.rglob("*.json")) if folder.exists() else []:
            stem, _, lg = f.stem.rpartition("_")
            if lg not in LANG_CODES:
                continue
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            st = d.get("style", "hoi_thoai" if "turns" in d else "giang")
            kind = TEACH[st].name if st in TEACH else st
            where = "mẫu" if "examples" in f.parts else "của tôi"
            lib.setdefault(f"{stem} · {kind} · {where}", {})[lg] = str(f)
    return lib


def on_lib_refresh():
    keys = list(library())
    return gr.update(choices=keys, value=keys[0] if keys else None)


def on_lib_load(key):
    files = library().get(key, {})
    return [Path(files[lg]).read_text(encoding="utf-8") if lg in files else "" for lg in LANG_CODES]


def on_llm_generate(topic, langs, level, model, style, cast_a, cast_b):
    if not topic.strip():
        raise gr.Error("Nhập chủ đề")
    outs = {}
    for lg in langs:
        try:
            d = lessonmod.generate(topic, lg, level, model, style=style, cast_a=cast_a, cast_b=cast_b)
        except Exception as e:  # noqa: BLE001
            raise gr.Error(f"Không gọi được Ollama ({e}). Cài https://ollama.com rồi: ollama pull {model}")
        d.setdefault("series", f"{LANGS[lg].name_vi.capitalize()} – {topic}")
        path = PROJECTS / "_lessons" / f"{slug(topic)}-{style}_{lg}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        outs[lg] = json.dumps(d, ensure_ascii=False, indent=2)
    return [outs.get(lg, gr.update()) for lg in LANG_CODES]


# ================= Giọng đọc =================
def on_engine(engine):
    vs = ["auto"] + tts.voices_for(engine)
    a = b = "auto"
    note = "" if tts.engine_available(engine) else f"⚠️ Chưa cài module `{engine}` — xem README."
    return gr.update(choices=vs, value=a), gr.update(choices=vs, value=b), note


def on_preview(voice, text):
    voice = "vieneu:Hải Đăng" if voice == "auto" else voice
    out = PROJECTS / "_preview" / "voice.wav"
    tts.synthesize(text, voice, out, 1.0)
    return str(out)


def on_style(style):
    st = TEACH[style]
    return (gr.update(value=st.cast[0] or "bo"), gr.update(value=st.cast[1] or None),
            f"**Dùng khi:** {st.when}\n\n**Hook mẫu:** “{st.hook_idea}”")


# ================= Rà soát trước khi đăng =================
REVIEW_DIR = PROJECTS / "_review"


def _editor_lessons(texts):
    out = []
    for lg, txt in zip(LANG_CODES, texts):
        if txt and txt.strip():
            try:
                d = json.loads(txt)
            except json.JSONDecodeError as e:
                raise gr.Error(f"JSON {lg} lỗi: {e}")
            d["lang"] = lg
            out.append(d)
    if not out:
        raise gr.Error("Chưa có kịch bản nào")
    return out


def on_review(en, zh, ko, use_llm, model, progress=gr.Progress()):
    from studio import review
    rows, notes = [], []
    for d in _editor_lessons((en, zh, ko)):
        lg = d["lang"]
        notes.append(f"- **{LANG_LABEL[lg]}**: ước lượng **~{review.estimate_seconds(d):.0f}s** (mục tiêu 40–50s)")
        rows += [[LANG_LABEL[lg], i["turn"], i["muc"], i["van_de"], ""] for i in review.check_rules(d)]
        if use_llm:
            progress(0.5, desc=f"LLM đang soát câu {lg}…")
            try:
                for x in review.review_llm(d, model):
                    rows.append([LANG_LABEL[lg], x["turn"], "LLM", f"{x['cau']} — {x['loi']}",
                                 f"{x['de_xuat']} {('(' + x['nghia_de_xuat'] + ')') if x['nghia_de_xuat'] else ''}".strip()])
            except Exception as e:  # noqa: BLE001
                notes.append(f"- ⚠️ Không gọi được Ollama để soát {lg}: {e}")
    if not rows:
        notes.append("- ✅ Không phát hiện vấn đề nào.")
    df = pd.DataFrame(rows, columns=["Kênh", "Lượt", "Mức", "Vấn đề", "Đề xuất"])
    return df, "\n".join(notes)


def on_sheet_export(en, zh, ko):
    from studio import review
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    files = []
    for d in _editor_lessons((en, zh, ko)):
        f = REVIEW_DIR / f"{slug(d.get('title', 'bai'))}_{d['lang']}.json"
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        files.append(str(f))
    name = slug(json.loads(next(t for t in (en, zh, ko) if t and t.strip())).get("title", "bai"))
    return str(review.export_sheet(files, REVIEW_DIR / f"duyet_{name}.csv"))


def on_sheet_import(path):
    from studio import review
    if not path:
        raise gr.Error("Chọn file CSV đã duyệt")
    changes = review.import_sheet(Path(path))
    texts = {}
    import csv as _csv
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for row in _csv.DictReader(fh):
            texts[row["lang"]] = row["file"]
    out = []
    for lg in LANG_CODES:
        f = texts.get(lg)
        out.append(Path(f).read_text(encoding="utf-8") if f and Path(f).exists() else gr.update())
    msg = "\n".join(f"- {c}" for c in changes) or "Không có ô nào được sửa."
    return out + [f"**Đã áp dụng {len(changes)} sửa đổi:**\n{msg}"]


def on_lesson_build(en, zh, ko, voice_a, voice_b, voice_n, speed, quality, native_engine, one_voice, engine,
                    progress=gr.Progress()):
    vids, notes = [None, None, None], []
    for i, (lg, txt) in enumerate(zip(LANG_CODES, (en, zh, ko))):
        if not txt or not txt.strip():
            continue
        try:
            data = json.loads(txt)
        except json.JSONDecodeError as e:
            raise gr.Error(f"JSON {lg} lỗi: {e}")
        data["lang"] = lg
        proj = lessonmod.to_project(data, voice_a, voice_b, voice_n, native_engine, one_voice,
                                    engine if engine in ("vieneu", "omnivoice") else "vieneu")
        res = build(proj, next((s.voice for s in proj.scenes if s.voice), "vieneu:Hải Đăng"), "card", RenderOptions(watermark=LANGS[lg].handle, quality=quality), speed=speed,
                    progress=lambda f, m, lg=lg: progress(f, desc=f"[{lg}] {m}"))
        vids[i] = res["video"]
        warn = "" if 40 <= res["duration"] <= 50 else " ⚠️ ngoài khoảng 40–50s: thêm/bớt lượt thoại"
        notes.append(f"- **{LANGS[lg].channel}**: {res['duration']:.1f}s{warn} · `{res['folder']}/export`")
    if not notes:
        raise gr.Error("Chưa có kịch bản nào")
    return vids + ["\n".join(notes)]


# ================= Tab video dài =================
def lib_for_lang(lang):
    return [k for k, files in library().items() if lang in files]


def on_long_lang(lang):
    return gr.update(choices=lib_for_lang(lang), value=[])


def on_long_build(lang, fmt, src, picks, topic, n_parts, style, level, model, title, layout, quality, one_voice,
                  engine, repeats, pause, per_chapter, target_min, music, progress=gr.Progress()):
    if src == "llm":
        if not topic.strip():
            raise gr.Error("Nhập chủ đề lớn cho video dài")
        progress(0, desc="LLM đang lên dàn ý và viết từng phần…")
        try:
            lessons = longform.generate_long(topic, lang, int(n_parts), style, level, model)
        except Exception as e:  # noqa: BLE001
            raise gr.Error(f"Không gọi được Ollama ({e})")
        for i, les in enumerate(lessons):
            p = PROJECTS / "_lessons" / f"{slug(topic)}-p{i + 1}-{style}_{lang}.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(les, ensure_ascii=False, indent=2), encoding="utf-8")
        title = title or topic
    else:
        lib = library()
        lessons = []
        for key in picks or []:
            d = json.loads(Path(lib[key][lang]).read_text(encoding="utf-8"))
            d["lang"] = lang
            lessons.append(d)
        if not lessons:
            raise gr.Error("Chọn ít nhất 1 kịch bản cùng chủ đề")
        title = title or lessons[0].get("series") or lessons[0].get("title", "Video dài")
    opts = longform.LongOptions(layout=layout, quality=quality, one_voice=one_voice,
                                vi_engine=engine if engine in ("vieneu", "omnivoice") else "vieneu",
                                repeats=int(repeats), pause=float(pause), per_chapter=int(per_chapter),
                                target_minutes=float(target_min), music=music)
    res = longform.build_long(lessons, fmt, title, opts, progress=lambda f, m: progress(f, desc=m))
    info = (f"**{res['duration'] / 60:.1f} phút** · thư mục `{res['folder']}`\n\n"
            f"**Mốc chương (dán vào mô tả YouTube):**\n```\n{res['chapters']}\n```")
    return res["video"], res["thumbnail"], [res["srt"], res["pdf"], res["description"], res["thumbnail"]], info


# ================= Tab video giải thích =================
COLS = ["beat", "text", "overlay", "visual", "character", "action", "expression", "position", "prop",
        "background", "character2", "action2"]
GUIDE = "\n\n".join((ROOT / f).read_text(encoding="utf-8") for f in ("FORMATS10.md", "CURRICULUM.md", "LONGFORM.md", "LANGUAGE_CHANNELS.md", "TECHNIQUES.md",
                                                                   "CHARACTER_GUIDE.md") if (ROOT / f).exists())


def _to_df(p: Project) -> pd.DataFrame:
    return pd.DataFrame([[getattr(s, c) for c in COLS] for s in p.scenes], columns=COLS)


def _from_ui(title, lang, desc, tags, df) -> Project:
    val = lambda v, d="": d if v is None or str(v) in ("", "nan", "None") else str(v)  # noqa: E731
    scenes = [Scene(beat=val(r.beat), text=val(r.text).strip(), overlay=val(r.overlay), visual=val(r.visual),
                    character=val(r.character), action=val(r.action, "dung"), expression=val(r.expression),
                    position=val(r.position, "giua"), prop=val(r.prop), background=val(r.background),
                    character2=val(r.character2), action2=val(r.action2, "dung"))
              for r in df.itertuples() if val(r.text).strip()]
    return Project(title=title or "video", language=lang, description=desc,
                   hashtags=[t for t in tags.replace(",", " ").split() if t], scenes=scenes)


def _fill(p: Project):
    return p.title, p.language, p.description, " ".join(p.hashtags), _to_df(p)


def on_generate(topic, lang, seconds, model):
    if not topic.strip():
        raise gr.Error("Nhập chủ đề trước")
    try:
        return _fill(generate_with_ollama(topic, lang, int(seconds), model))
    except Exception as e:  # noqa: BLE001
        raise gr.Error(f"Không gọi được Ollama ({e}).")


def on_build(title, lang, desc, tags, df, voice, speed, img_mode, style, watermark, music, progress=gr.Progress()):
    p = _from_ui(title, lang, desc, tags, df)
    if not p.scenes:
        raise gr.Error("Kịch bản chưa có cảnh nào")
    if img_mode == "sd" and not images.sd_available():
        raise gr.Error("Chưa cài Stable Diffusion: pip install -r requirements-gpu.txt")
    res = build(p, voice, img_mode, RenderOptions(style=style, watermark=watermark, music=music or ""),
                speed=speed, progress=lambda f, m: progress(f, desc=m))
    return res["video"], res["cover"], f"Thời lượng **{res['duration']:.1f}s** · `{res['folder']}`"


# ================= Giao diện =================
models = ollama_models() or ["qwen2.5:7b"]
default_engine = "vieneu" if tts.engine_available("vieneu") else "piper"

with gr.Blocks(title="Shorts Studio") as demo:
    from studio.gpu import summary as gpu_summary
    gr.Markdown("# 🎬 Shorts Studio\nVideo short giáo dục — mã nguồn mở, chạy trên PC\n\n" + gpu_summary())

    with gr.Tab("🌏 Kênh học ngoại ngữ"):
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### ① Kịch bản")
                src = gr.Radio([("Có sẵn trong thư viện", "lib"), ("Sinh bằng LLM (Ollama)", "llm")],
                               value="lib", label="Nguồn kịch bản")
                with gr.Group(visible=True) as g_lib:
                    lib_keys = list(library())
                    lib = gr.Dropdown(lib_keys, value=lib_keys[0] if lib_keys else None, label="Chủ đề có sẵn")
                    with gr.Row():
                        b_load = gr.Button("📂 Mở", variant="secondary")
                        b_ref = gr.Button("🔄 Làm mới")
                with gr.Group(visible=False) as g_llm:
                    topic = gr.Textbox(label="Chủ đề", placeholder="VD: hỏi đường, đi siêu thị, phỏng vấn")
                    tstyle = gr.Dropdown(STYLE_CHOICES, value="giao_tiep", label="Định dạng (10 kiểu thu hút nhất + phong cách khác)")
                    style_note = gr.Markdown(f"**Dùng khi:** {TEACH['giao_tiep'].when}")
                    with gr.Row():
                        cast_a = gr.Dropdown(CHAR_CHOICES, value="bo", label="Nhân vật A (trái)")
                        cast_b = gr.Dropdown(CHAR_CHOICES, value="mai", label="Nhân vật B (phải)")
                    langs = gr.CheckboxGroup(list(LANG_CODES), value=list(LANG_CODES), label="Kênh")
                    level = gr.Dropdown(LEVEL_CHOICES, value=1, label="Trình độ (khung 5 level)")
                    model = gr.Dropdown(models, value=models[0], label="Model Ollama", allow_custom_value=True)
                    b_llm = gr.Button("✨ Sinh kịch bản", variant="primary")
                gr.Markdown("### ② Giọng đọc")
                engine = gr.Dropdown([(v, k) for k, v in tts.ENGINES.items() if k in ("vieneu", "omnivoice", "piper")],
                                     value=default_engine, label="Module TTS tiếng Việt")
                v0 = tts.voices_for(default_engine)
                v0 = ["auto"] + v0
                voice_a = gr.Dropdown(v0, value="auto",
                                      label="Giọng A — nhân vật bên trái")
                voice_b = gr.Dropdown(v0, value="auto",
                                      label="Giọng B — nhân vật bên phải")
                voice_n = gr.Dropdown(v0, value="auto",
                                      label="Giọng N — người dẫn (không xuất hiện)")
                engine_note = gr.Markdown()
                speed = gr.Slider(0.8, 1.3, value=1.0, step=0.05, label="Tốc độ giọng Việt")
                with gr.Accordion("🔊 Nghe thử giọng", open=False):
                    prev_text = gr.Textbox(value="Chào bạn, hôm nay mình học gọi cà phê nhé!", label="Câu thử")
                    with gr.Row():
                        b_pa, b_pb = gr.Button("Nghe giọng A"), gr.Button("Nghe giọng B")
                    prev_audio = gr.Audio(label="Kết quả", type="filepath")
                one_voice = gr.Checkbox(value=True, label="✅ Mỗi nhân vật chỉ 1 giọng (nhân bản giọng Việt sang Trung/Hàn/Anh "
                                        "bằng Qwen3-TTS Base, dự phòng OmniVoice)")
                native_engine = gr.Radio(
                    [("Tự động (Qwen3-TTS cho Trung/Hàn nếu đã cài)", "auto"), ("Qwen3-TTS (GPU, tự nhiên nhất)", "qwen"),
                     ("Piper (nhẹ, CPU)", "piper")], value="auto", label="Giọng bản ngữ (Anh/Trung/Hàn)")
                gr.Markdown("Qwen3-TTS: 🇨🇳 vivian (nữ) · dylan (nam) · 🇰🇷 sohee · 🇬🇧 serena · ryan — chọn theo giới tính nhân vật.")
                quality = gr.Radio([("Full-HD 1080×1920 (xuất bản)", "fullhd"), ("Nháp nhanh (xem thử)", "nhap")],
                                   value="fullhd", label="Chất lượng video")
                with gr.Accordion("🔎 Rà soát trước khi đăng", open=True):
                    rv_llm = gr.Checkbox(value=False, label="Dùng thêm LLM (Ollama) soát ngữ pháp, độ tự nhiên, nghĩa")
                    b_review = gr.Button("🔎 Rà soát kịch bản")
                    with gr.Row():
                        b_sheet = gr.Button("📤 Xuất bảng duyệt (CSV)")
                        sheet_in = gr.File(label="📥 Nhập bảng đã duyệt", file_types=[".csv"], height=90)
                    sheet_out = gr.File(label="Bảng duyệt cho người bản xứ (mở bằng Excel / Google Sheets)",
                                        height=90)
                b_build = gr.Button("🎬 Dựng video cho các kênh", variant="primary", size="lg")
            with gr.Column(scale=2):
                gr.Markdown("### Kịch bản từng kênh (JSON — sửa trực tiếp, **kiểm tra câu chữ trước khi đăng**)")
                with gr.Tabs():
                    editors = []
                    for lg in LANG_CODES:
                        with gr.Tab(LANG_LABEL[lg]):
                            editors.append(gr.Code(language="json", lines=24))
                with gr.Row():
                    vids = [gr.Video(label=LANG_LABEL[lg], height=460) for lg in LANG_CODES]
                info = gr.Markdown()
                rv_note = gr.Markdown()
                rv_table = gr.Dataframe(label="Kết quả rà soát", wrap=True)
        src.change(lambda s: (gr.update(visible=s == "lib"), gr.update(visible=s == "llm")), src, [g_lib, g_llm])
        b_load.click(on_lib_load, lib, editors)
        b_ref.click(on_lib_refresh, None, lib)
        b_llm.click(on_llm_generate, [topic, langs, level, model, tstyle, cast_a, cast_b], editors)
        tstyle.change(on_style, tstyle, [cast_a, cast_b, style_note])
        engine.change(lambda e: (*on_engine(e)[:2], gr.update(choices=["auto"] + tts.voices_for(e), value="auto"),
                                 on_engine(e)[2]), engine, [voice_a, voice_b, voice_n, engine_note])
        b_pa.click(on_preview, [voice_a, prev_text], prev_audio)
        b_pb.click(on_preview, [voice_b, prev_text], prev_audio)
        b_review.click(on_review, editors + [rv_llm, model], [rv_table, rv_note])
        b_sheet.click(on_sheet_export, editors, sheet_out)
        sheet_in.upload(on_sheet_import, sheet_in, editors + [rv_note])
        b_build.click(on_lesson_build, editors + [voice_a, voice_b, voice_n, speed, quality, native_engine, one_voice,
                                                  engine],
                      vids + [info])
        demo.load(on_lib_load, lib, editors)

    with gr.Tab("🎬 Video dài (YouTube)"):
        gr.Markdown("Ghép & mở rộng các bài **cùng chủ đề** thành video dài 8-60 phút: mở bài, mục lục, chương, "
                    "ôn nhanh cuối chương, kết bài. Xuất kèm **mốc chương, phụ đề SRT, thumbnail, PDF tóm tắt**.")
        with gr.Row():
            with gr.Column(scale=1):
                l_lang = gr.Radio([(LANG_LABEL[k], k) for k in LANG_CODES], value="ko", label="Kênh / ngôn ngữ")
                l_fmt = gr.Radio([(v, k) for k, v in longform.FORMATS.items()], value="tron_chu_de",
                                 label="Định dạng video dài")
                l_src = gr.Radio([("Chọn các bài có sẵn (cùng chủ đề)", "lib"), ("LLM viết nhiều phần", "llm")],
                                 value="lib", label="Nguồn nội dung")
                with gr.Group(visible=True) as lg_lib:
                    l_picks = gr.CheckboxGroup(lib_for_lang("ko"), label="Các bài ghép thành video (theo thứ tự chọn)")
                with gr.Group(visible=False) as lg_llm:
                    l_topic = gr.Textbox(label="Chủ đề lớn", placeholder="VD: Du lịch Hàn Quốc 5 ngày")
                    l_n = gr.Slider(2, 12, value=5, step=1, label="Số phần / chương")
                    l_style = gr.Dropdown(STYLE_CHOICES, value="giao_tiep", label="Phong cách mỗi phần")
                    l_level = gr.Dropdown(LEVEL_CHOICES, value=1, label="Trình độ (khung 5 level)")
                    l_model = gr.Dropdown(models, value=models[0], label="Model Ollama", allow_custom_value=True)
                l_title = gr.Textbox(label="Tiêu đề video (trống = tự đặt)")
            with gr.Column(scale=1):
                l_layout = gr.Radio([("Ngang 1920×1080 (YouTube)", "ngang"), ("Dọc 1080×1920", "doc")],
                                    value="ngang", label="Khung hình")
                l_quality = gr.Radio([("Full-HD (xuất bản)", "fullhd"), ("Nháp nhanh", "nhap")], value="fullhd",
                                     label="Chất lượng")
                l_engine = gr.Dropdown([(v, k) for k, v in tts.ENGINES.items() if k in ("vieneu", "omnivoice", "piper")],
                                       value=default_engine, label="Module giọng Việt")
                l_one = gr.Checkbox(value=True, label="Mỗi nhân vật 1 giọng (nhân bản giọng sang ngoại ngữ)")
                with gr.Accordion("Tuỳ chọn luyện nghe / flashcard / ôn tập", open=False):
                    l_rep = gr.Slider(1, 4, value=2, step=1, label="Số lần lặp mỗi câu (luyện nghe)")
                    l_pause = gr.Slider(1, 6, value=2.5, step=0.5, label="Khoảng lặng nói theo (giây)")
                    l_per = gr.Slider(3, 20, value=10, step=1, label="Số câu mỗi chương")
                    l_target = gr.Slider(0, 60, value=0, step=5,
                                         label="Luyện nghe: kéo dài tới N phút (lặp vòng các câu; 0 = không lặp)")
                    l_music = gr.Radio([("Tự động (bật cho luyện nghe)", "auto"), ("Bật", "on"), ("Tắt", "off")],
                                       value="auto", label="Nhạc nền dịu (tự tạo, không bản quyền)")
                l_go = gr.Button("🎬 Dựng video dài", variant="primary", size="lg")
        with gr.Row():
            l_video = gr.Video(label="Video dài", height=420)
            l_thumb = gr.Image(label="Thumbnail 1280×720", height=420)
        l_files = gr.File(label="Phụ đề SRT · PDF tóm tắt · mô tả YouTube · thumbnail", file_count="multiple")
        l_info = gr.Markdown()
        l_src.change(lambda s: (gr.update(visible=s == "lib"), gr.update(visible=s == "llm")), l_src, [lg_lib, lg_llm])
        l_lang.change(on_long_lang, l_lang, l_picks)
        l_go.click(on_long_build, [l_lang, l_fmt, l_src, l_picks, l_topic, l_n, l_style, l_level, l_model, l_title,
                                   l_layout, l_quality, l_one, l_engine, l_rep, l_pause, l_per, l_target, l_music],
                   [l_video, l_thumb, l_files, l_info])

    with gr.Tab("📚 Khung nội dung"):
        gr.Markdown("**10 định dạng × 5 level × 3 ngôn ngữ.** Chọn ô → xem *đề cương* gửi cho LLM (ngữ pháp, độ dài "
                    "câu, trọng tâm định dạng, từ vựng chuẩn HSK/TOPIK/CEFR, câu mẫu thật Tatoeba) → sinh cả series. "
                    "Kịch bản lưu vào thư viện (*của tôi*) để dựng ở tab 🌏. Toàn bộ khung: CURRICULUM.md.")
        with gr.Row():
            with gr.Column(scale=1):
                k_fmt = gr.Dropdown([(label, key) for key, label in FORMATS10], value="giao_tiep", label="Định dạng")
                k_lang = gr.Radio([(LANG_LABEL[k], k) for k in LANG_CODES], value="ko", label="Ngôn ngữ")
                k_level = gr.Dropdown(LEVEL_CHOICES, value=1, label="Level")
                k_topic = gr.Textbox(label="Chủ đề tập (trống = theo danh sách chủ đề của level)")
                k_ex = gr.Checkbox(value=True, label="Kèm câu mẫu thật từ Tatoeba (cần mạng)")
                k_show = gr.Button("🔍 Xem đề cương & danh sách tập")
                k_n = gr.Slider(1, 30, value=5, step=1, label="Số tập sinh bằng LLM")
                k_model = gr.Dropdown(models, value=models[0], label="Model Ollama", allow_custom_value=True)
                k_gen = gr.Button("✨ Sinh series bằng LLM", variant="primary")
            with gr.Column(scale=2):
                k_brief = gr.Textbox(label="Đề cương gửi LLM", lines=12)
                k_eps = gr.Dataframe(label="Danh sách tập", wrap=True)
                k_out = gr.Markdown()
        with gr.Accordion("Toàn bộ ma trận 150 ô", open=False):
            gr.Dataframe(pd.DataFrame(curriculum.matrix()), wrap=True)

        def on_k_show(fmt, lang, level, topic, ex, n):
            eps = curriculum.episodes(fmt, lang, int(level), int(n))
            if topic.strip():
                for e in eps:
                    e["topic"] = f"{topic} — {e['topic']}"
            return (curriculum.brief(fmt, lang, int(level), topic, with_examples=ex),
                    pd.DataFrame(eps)[["episode", "series", "topic", "focus"]])

        def on_k_gen(fmt, lang, level, topic, ex, n, model, progress=gr.Progress()):
            eps = curriculum.episodes(fmt, lang, int(level), int(n))
            rows = []
            for i, e in enumerate(eps):
                t = f"{topic} — {e['topic']}" if topic.strip() else e["topic"]
                progress(i / len(eps), desc=f"Tập {e['episode']}: {t}")
                try:
                    d = lessonmod.generate(t, lang, int(level), model, style=fmt, use_examples=ex)
                except Exception as err:  # noqa: BLE001
                    raise gr.Error(f"Không gọi được Ollama ({err})")
                d.update(series=e["series"], episode=e["episode"])
                f = PROJECTS / "_lessons" / f"{slug(e['series'])}-{e['episode']:02d}_{lang}.json"
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
                chk = d.get("level_check", {})
                rows.append(f"- #{e['episode']:02d} **{d.get('title', t)}** · vượt level {chk.get('ratio', 0):.0%} "
                            f"{' '.join(chk.get('above', [])[:6])} · `{f.name}`")
            return "\n".join(rows) + "\n\n➡️ Mở tab 🌏, bấm 🔄 Làm mới thư viện để dựng."

        k_show.click(on_k_show, [k_fmt, k_lang, k_level, k_topic, k_ex, k_n], [k_brief, k_eps])
        k_gen.click(on_k_gen, [k_fmt, k_lang, k_level, k_topic, k_ex, k_n, k_model], k_out)

    with gr.Tab("📅 Thử thách 30 ngày"):
        gr.Markdown("Lập **lịch 30 bài nối tiếp** (khó dần, ngày 7/14/21/28 ôn tập), rồi mỗi ngày sinh & dựng 1 short "
                    "có huy hiệu **NGÀY N/30**. Bài đã sinh được lưu lại, dựng lại không tốn LLM.")
        with gr.Row():
            with gr.Column(scale=1):
                c_lang = gr.Radio([(LANG_LABEL[k], k) for k in LANG_CODES], value="ko", label="Kênh")
                c_topic = gr.Textbox(label="Chủ đề thử thách", value="Giao tiếp cơ bản")
                c_level = gr.Dropdown(LEVEL_CHOICES, value=1, label="Trình độ (khung 5 level)")
                c_llm = gr.Checkbox(value=False, label="Lập lịch bằng LLM (tắt = khung 4 tuần mặc định)")
                c_model = gr.Dropdown(models, value=models[0], label="Model Ollama", allow_custom_value=True)
                c_plan_btn = gr.Button("🗓️ Lập / xem lịch 30 ngày")
                c_day = gr.Slider(1, 30, value=1, step=1, label="Ngày")
                c_quality = gr.Radio([("Full-HD", "fullhd"), ("Nháp nhanh", "nhap")], value="fullhd", label="Chất lượng")
                c_go = gr.Button("🎬 Sinh & dựng short của ngày này", variant="primary")
            with gr.Column(scale=2):
                c_table = gr.Dataframe(headers=["day", "topic", "goal"], label="Lịch 30 ngày", wrap=True)
                c_video = gr.Video(label="Short ngày N", height=460)
                c_json = gr.Code(language="json", label="Kịch bản ngày N", lines=12)

        def on_plan(lang, topic, level, use_llm, model):
            days = challenge.load_plan(topic, lang) if not use_llm else None
            try:
                days = days or challenge.make_plan(topic, lang, level, use_llm, model)
            except Exception as e:  # noqa: BLE001
                raise gr.Error(f"Không gọi được Ollama ({e})")
            return pd.DataFrame(days)

        def on_day(lang, topic, level, model, day, quality, progress=gr.Progress()):
            try:
                les = challenge.day_lesson(topic, lang, int(day), level, model)
            except Exception as e:  # noqa: BLE001
                raise gr.Error(f"Không sinh được bài ngày {day} ({e}). Cần Ollama đang chạy.")
            les["lang"] = lang
            proj = lessonmod.to_project(les, "auto", "auto", "auto")
            res = build(proj, proj.scenes[0].voice or "vieneu:Hải Đăng", "card",
                        RenderOptions(watermark=LANGS[lang].handle, quality=quality),
                        progress=lambda f, m: progress(f, desc=m))
            return res["video"], json.dumps(les, ensure_ascii=False, indent=2)

        c_plan_btn.click(on_plan, [c_lang, c_topic, c_level, c_llm, c_model], c_table)
        c_go.click(on_day, [c_lang, c_topic, c_level, c_model, c_day, c_quality], [c_video, c_json])

    with gr.Tab("💡 Video giải thích"):
        with gr.Row():
            topic2 = gr.Textbox(label="Chủ đề", scale=3)
            lang2 = gr.Radio(["vi", "en"], value="vi", label="Ngôn ngữ")
            seconds = gr.Slider(20, 90, value=45, step=5, label="Độ dài (giây)")
        with gr.Row():
            model2 = gr.Dropdown(models, value=models[0], label="Model Ollama", allow_custom_value=True)
            b_gen = gr.Button("✨ Sinh kịch bản (Ollama)", variant="primary")
            b_tpl = gr.Button("Khung trống")
            f_load = gr.File(label="Mở kịch bản .json", file_types=[".json"], height=80)
        title = gr.Textbox(label="Tiêu đề")
        with gr.Row():
            desc = gr.Textbox(label="Mô tả", lines=2, scale=3)
            tags = gr.Textbox(label="Hashtag", scale=2)
        table = gr.Dataframe(headers=COLS, column_count=(len(COLS), "fixed"), wrap=True, interactive=True)
        gr.Markdown(f"**Nhân vật:** {', '.join(charmod.available())} · **action:** {', '.join(charmod.ACTION_LABELS)}"
                    f"\n\n**prop:** {', '.join(PROPS)} · **background:** {', '.join(BACKGROUNDS)}")
        with gr.Row():
            with gr.Column():
                engine2 = gr.Dropdown([(v, k) for k, v in tts.ENGINES.items()], value=default_engine, label="Module TTS")
                voice2 = gr.Dropdown(v0, value=voice_a.value, label="Giọng đọc")
                speed2 = gr.Slider(0.8, 1.4, value=1.05, step=0.05, label="Tốc độ đọc")
                img_mode = gr.Radio([("Thẻ đồ hoạ / phông nền có sẵn", "card"), ("Stable Diffusion (GPU)", "sd")],
                                    value="card", label="Hình ảnh")
                style = gr.Dropdown(list(STYLES), value="infographic", label="Bộ nhận diện")
                watermark = gr.Textbox(label="Tên kênh", placeholder="@TenKenh")
                music = gr.File(label="Nhạc nền (tuỳ chọn)", file_types=["audio"], type="filepath")
                b_build2 = gr.Button("🎬 Dựng video", variant="primary")
            with gr.Column():
                video2 = gr.Video(label="Kết quả", height=560)
                cover2 = gr.Image(label="Ảnh bìa", height=200)
                info2 = gr.Markdown()
        ui = [title, lang2, desc, tags, table]
        b_gen.click(on_generate, [topic2, lang2, seconds, model2], ui)
        b_tpl.click(lambda t, l: _fill(template(t or "Chủ đề mới", l)), [topic2, lang2], ui)
        f_load.upload(lambda f: _fill(Project.load(f)), f_load, ui)
        engine2.change(lambda e: gr.update(choices=tts.voices_for(e), value=tts.voices_for(e)[0]), engine2, voice2)
        b_build2.click(on_build, ui + [voice2, speed2, img_mode, style, watermark, music], [video2, cover2, info2])
        demo.load(lambda: _fill(Project.load(ROOT / "examples" / "tien_giay_nhanvat.json")), None, ui)

    with gr.Tab("🧑‍🤝‍🧑 Nhân vật & phong cách"):
        gr.Image(str(ROOT / "docs" / "cast_sheet.png"), label="Dàn 21 nhân vật (mã dùng trong kịch bản)",
                 show_label=True, height=720)
        gr.Markdown("\n".join(f"- **{st.name}** — {st.when}. Mặc định: {st.cast[0]} & {st.cast[1] or '(1 người)'}"
                               for st in TEACH.values()))

    with gr.Tab("📘 Hướng dẫn"):
        gr.Markdown(GUIDE)

if __name__ == "__main__":
    demo.queue().launch(inbrowser=True, theme=gr.themes.Soft())
