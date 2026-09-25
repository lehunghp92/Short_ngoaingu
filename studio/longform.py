"""VIDEO DÀI cùng chủ đề (8-60 phút) cho YouTube — ghép & mở rộng từ các bài học short.

6 định dạng:
  tron_chu_de     📚 Bài học trọn chủ đề  : ghép nhiều bài cùng chủ đề + mở bài, mục lục, chương, ôn nhanh cuối chương
  phim_tinh_huong 🎭 Phim tình huống liền mạch: cùng 1 nhân vật chính đi qua nhiều bối cảnh (sân bay → khách sạn → ...)
  luyen_nghe      🎧 Luyện nghe thụ động  : Việt → bản ngữ → chậm → khoảng lặng nói theo; nền tối dịu mắt
  on_tap          🔁 Ôn tập tuần          : học 5 câu → quiz 5 câu, lặp lại theo nhóm
  flashcard       📝 Flashcard tốc độ     : từng từ/câu kèm hình đồ vật, nhanh gọn
  hon_hop         🎨 Hỗn hợp              : mỗi chương đổi kiểu (bài theo phong cách riêng → quiz A/B/C → nghe lại)
Luyện nghe: có nhạc nền dịu tự tạo và tuỳ chọn "kéo dài tới N phút" (lặp vòng các câu).
Đầu ra: video (mặc định NGANG 1920x1080), mốc chương YouTube, phụ đề SRT, thumbnail 1280x720, PDF tóm tắt.
Mỗi chương dựng thành 1 file riêng rồi ghép (chương lỗi chỉ cần dựng lại chương đó).
"""
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from PIL import Image, ImageDraw

from . import lesson as lessonmod
from .config import PROJECTS, RenderOptions
from .gpu import ffmpeg_exe
from .langs import LANGS, cjk_font, native_voice, roman_font
from .pipeline import build, slug
from .script import Project, Scene

FORMATS = {
    "tron_chu_de": "📚 Bài học trọn chủ đề (ghép nhiều bài + ôn tập)",
    "phim_tinh_huong": "🎭 Phim tình huống liền mạch (1 nhân vật, nhiều bối cảnh)",
    "luyen_nghe": "🎧 Luyện nghe thụ động (nghe – nhắc lại, 30-60 phút)",
    "on_tap": "🔁 Ôn tập tuần (học 5 câu → quiz 5 câu)",
    "flashcard": "📝 Flashcard tốc độ (từ/câu kèm hình)",
    "hon_hop": "🎨 Hỗn hợp định dạng (mỗi chương: bài học → đố vui A/B/C → nghe nhắc lại)",
}


@dataclass
class LongOptions:
    layout: str = "ngang"             # ngang 1920x1080 (YouTube) | doc 1080x1920
    quality: str = "fullhd"
    one_voice: bool = True
    native_engine: str = "auto"
    vi_engine: str = "vieneu"
    voice_a: str = "auto"
    voice_b: str = "auto"
    voice_n: str = "auto"
    speed: float = 1.0
    repeats: int = 2                  # luyện nghe: số lần lặp mỗi câu
    pause: float = 2.5                # luyện nghe/flashcard: khoảng lặng để người xem nói theo
    group: int = 5                    # ôn tập: số câu mỗi nhóm
    per_chapter: int = 10             # luyện nghe/flashcard: số câu mỗi chương
    target_minutes: float = 0         # luyện nghe: lặp vòng các câu tới khi đủ N phút (0 = không lặp)
    music: str = "auto"               # auto (bật cho luyện nghe) | on | off — nhạc nền tự tạo, không bản quyền


# ---------------- trích câu từ bài học ----------------
def extract_phrases(lesson: dict) -> List[dict]:
    out, seen = [], set()
    rows = []
    for t in lesson.get("turns", []):
        if t.get("native") and t.get("mark", "dung") not in ("sai", "quiz_q"):
            rows.append((t["native"], t.get("meaning", ""), t.get("item", "")))
    for it in lesson.get("items", []):
        for k in ("right", "word", "answer"):
            if it.get(k):
                rows.append((it[k], it.get("meaning", ""), it.get("prop", "")))
        for line in it.get("lines", []):
            rows.append((line["text"], line.get("meaning", ""), ""))
    for foreign, meaning, item in rows:
        if foreign in seen:
            continue
        seen.add(foreign)
        out.append({"foreign": foreign, "meaning": meaning, "item": item,
                    "roman": lessonmod._roman(lesson["lang"], foreign)})
    return out


# ---------------- các cảnh dựng sẵn ----------------
def _vi(text):
    return {"lang": "vi", "text": text, "speed": 1.0}


def _nat(lang, text, voice, speed=1.0):
    return {"lang": lang, "text": text, "speed": speed, "voice": voice}


def _slide(kind, speech, voice, **kw) -> Scene:
    return Scene(text=" ".join(x["text"] for x in speech if x.get("lang") == "vi"), speech=speech, voice=voice,
                 slide={"kind": kind, **kw})


def _card(lang, p, mark="dung", **kw) -> dict:
    return {"lang": lang, "foreign": p["foreign"], "roman": p.get("roman", ""), "meaning": p.get("meaning", ""),
            "mark": mark, **kw}


class _Ctx:
    def __init__(self, lang, opts: LongOptions, cast: dict):
        self.lang, self.o = lang, opts
        self.voices = lessonmod.auto_voices(cast, opts.voice_a, opts.voice_b, opts.voice_n, opts.vi_engine)
        self.cast = cast

    def nat_voice(self, who="N"):
        if self.o.one_voice:
            return "clone:" + self.voices[who]
        from .character import load
        g = load(self.cast[who]).gender if self.cast.get(who) else "nu"
        return native_voice(self.lang, g, self.o.native_engine)


def _recap(ctx: _Ctx, phrases: List[dict], title="ÔN NHANH") -> Scene:
    speech = [_vi("Cùng ôn nhanh nhé!")]
    for p in phrases[:6]:
        speech += [_nat(ctx.lang, p["foreign"], ctx.nat_voice("N")), {"pause": 0.9}]
    return _slide("recap", speech, ctx.voices["N"], title=title, items=phrases[:6], lang=ctx.lang)


def _listen_scene(ctx: _Ctx, p: dict, bg: str) -> Scene:
    nv = ctx.nat_voice("N")
    speech = [_vi(p["meaning"]), {"pause": 0.4}]
    for r in range(max(1, ctx.o.repeats)):
        speech += [_nat(ctx.lang, p["foreign"], nv), {"pause": 0.5}, _nat(ctx.lang, p["foreign"], nv, 0.75),
                   {"pause": ctx.o.pause}]
    return Scene(text=p["meaning"], speech=speech, voice=ctx.voices["N"], background=bg,
                 card=_card(ctx.lang, p, shadow=True), item=p.get("item", ""))


def _quiz_abc(ctx: _Ctx, grp: List[dict], pool: List[dict], cast: dict, bg: str) -> List[Scene]:
    """Đố vui trắc nghiệm A/B/C: câu hỏi Việt → đếm ngược tích tắc → công bố (tiếng 'đúng') + đọc đáp án."""
    import random
    rnd = random.Random(len(pool))
    out = []
    for qi, p in enumerate(grp):
        wrong = [x["foreign"] for x in pool if x["foreign"] != p["foreign"]]
        rnd.shuffle(wrong)
        opts = wrong[:2] + [p["foreign"]]
        rnd.shuffle(opts)
        ans = opts.index(p["foreign"])
        q = f"Câu {qi + 1}: “{p['meaning']}” là câu nào?"
        tag = f"Quiz {qi + 1}/{len(grp)}"
        speech = [_vi(q)]
        for _ in range(3):
            speech += [{"sfx": "tick"}, {"pause": 0.94}]
        base = dict(voice=ctx.voices["A"], character=cast["A"], character2=cast["B"], position="trai", background=bg)
        out.append(Scene(text=q, speech=speech, speaker=1, action="suy_nghi",
                         card={"lang": ctx.lang, "foreign": "?", "roman": "", "meaning": q, "mark": "quiz_q",
                               "tag": tag, "options": opts}, **base))
        out.append(Scene(text="", speech=[{"sfx": "dung"}, _nat(ctx.lang, p["foreign"], ctx.nat_voice("B")),
                                          {"pause": 0.6}],
                         speaker=2, action2="vui_mung", item=p.get("item", ""),
                         card=_card(ctx.lang, p, tag=tag, options=opts, answer=ans, picked=ans, reveal=True),
                         **{**base, "voice": ctx.voices["B"]}))
    return out


def _loop_to_target(phrases: List[dict], opts: LongOptions) -> List[dict]:
    """Luyện nghe: lặp vòng danh sách câu cho tới khi ước lượng đủ `target_minutes` phút."""
    if not opts.target_minutes or not phrases:
        return phrases
    per = 3.0 + max(1, opts.repeats) * (2.2 + opts.pause)        # giây ước lượng cho 1 câu
    need = int(opts.target_minutes * 60 / per) + 1
    out, rnd = [], 0
    while len(out) < need:
        rnd += 1
        out += [{**p, "round": rnd} for p in phrases]
    return out[:need]


# ---------------- lập kế hoạch chương ----------------
def plan(lessons: List[dict], fmt: str, title: str, opts: LongOptions) -> List[dict]:
    """Trả về danh sách chương: {"title", "project": Project, "phrases": [...]} (chương 0 = mở đầu)."""
    lang = lessons[0]["lang"]
    first_cast = {"A": "bo", "B": "mai", **lessons[0].get("cast", {})}
    ctx = _Ctx(lang, opts, first_cast)
    chapters = []
    L = LANGS[lang]

    def proj(t, scenes):
        return Project(title=t, language=lang, scenes=scenes, hashtags=L.hashtags)

    # ----- nội dung từng chương -----
    body = []
    if fmt == "hon_hop":
        pool = [p for les in lessons for p in extract_phrases(les)]
        for i, les in enumerate(lessons):
            ch_title = les.get("title", f"Phần {i + 1}")
            p = lessonmod.to_project(les, opts.voice_a, opts.voice_b, ctx.voices["N"], opts.native_engine,
                                     opts.one_voice, opts.vi_engine)
            phrases = extract_phrases(les)
            bg = les.get("background", "phong_khach")
            scenes = [_slide("chapter", [_vi(f"Phần {i + 1}. {ch_title}")], ctx.voices["N"], title=ch_title,
                             number=i + 1)] + p.scenes
            if phrases:
                scenes.append(_slide("chapter", [_vi("Đố vui! Chọn đáp án đúng trước khi hết giờ nhé.")],
                                     ctx.voices["N"], title="Đố vui A / B / C", number=i + 1))
                scenes += _quiz_abc(ctx, phrases[:3], pool, first_cast, bg)
                scenes.append(_slide("chapter", [_vi("Giờ nghe và nhắc lại theo nhé.")], ctx.voices["N"],
                                     title="Nghe – nhắc lại", number=i + 1))
                scenes += [_listen_scene(ctx, ph, "vu_tru") for ph in phrases[:3]]
                scenes.append(_recap(ctx, phrases))
            body.append({"title": ch_title, "project": proj(ch_title, scenes), "phrases": phrases})
    elif fmt in ("tron_chu_de", "phim_tinh_huong"):
        for i, les in enumerate(lessons):
            les = dict(les)
            if fmt == "phim_tinh_huong":   # giữ nguyên nhân vật chính xuyên suốt
                les["cast"] = {**les.get("cast", {}), "A": first_cast["A"]}
            ch_title = les.get("title", f"Phần {i + 1}")
            p = lessonmod.to_project(les, ctx.voices["A"] if fmt == "phim_tinh_huong" else opts.voice_a,
                                     opts.voice_b, ctx.voices["N"], opts.native_engine, opts.one_voice,
                                     opts.vi_engine)
            phrases = extract_phrases(les)
            intro = ("Tiếp theo, " if fmt == "phim_tinh_huong" and i else f"Phần {i + 1}. ") + ch_title
            scenes = [_slide("chapter", [_vi(intro)], ctx.voices["N"], title=ch_title, number=i + 1)] + p.scenes
            if phrases:
                scenes.append(_recap(ctx, phrases))
            body.append({"title": ch_title, "project": proj(ch_title, scenes), "phrases": phrases})
    else:
        phrases = [p for les in lessons for p in extract_phrases(les)]
        if fmt == "luyen_nghe":
            phrases = _loop_to_target(phrases, opts)
            n = max(1, opts.per_chapter)
            for ci in range(0, len(phrases), n):
                grp = phrases[ci:ci + n]
                t = f"Câu {ci + 1}–{ci + len(grp)}"
                scenes = [_slide("chapter", [_vi(f"Phần {ci // n + 1}. Nghe và nhắc lại theo nhé.")],
                                 ctx.voices["N"], title=t, number=ci // n + 1)]
                scenes += [_listen_scene(ctx, p, "vu_tru") for p in grp]
                body.append({"title": t, "project": proj(t, scenes), "phrases": grp})
        elif fmt == "on_tap":
            g = max(1, opts.group)
            for ci in range(0, len(phrases), g):
                grp = phrases[ci:ci + g]
                t = f"Nhóm {ci // g + 1}"
                scenes = [_slide("chapter", [_vi(f"Nhóm {ci // g + 1}. Học năm câu rồi làm quiz nhé!")],
                                 ctx.voices["N"], title=t, number=ci // g + 1)]
                for p in grp:     # học
                    scenes.append(Scene(text=p["meaning"], speech=[_nat(lang, p["foreign"], ctx.nat_voice("B")),
                                                                    {"pause": 0.3},
                                                                    _nat(lang, p["foreign"], ctx.nat_voice("B"), 0.75),
                                                                    _vi(p["meaning"])],
                                        voice=ctx.voices["B"], card=_card(lang, p), character=first_cast["A"],
                                        character2=first_cast["B"], speaker=2, action2="chi_tay", position="trai",
                                        background=lessons[0].get("background", "phong_khach"), item=p.get("item", "")))
                scenes += _quiz_abc(ctx, grp, phrases, first_cast, lessons[0].get("background", "phong_khach"))
                body.append({"title": t, "project": proj(t, scenes), "phrases": grp})
        else:  # flashcard
            n = max(1, opts.per_chapter)
            for ci in range(0, len(phrases), n):
                grp = phrases[ci:ci + n]
                t = f"Thẻ {ci + 1}–{ci + len(grp)}"
                scenes = [_slide("chapter", [_vi(f"Bộ thẻ {ci // n + 1}.")], ctx.voices["N"], title=t,
                                 number=ci // n + 1)]
                for j, p in enumerate(grp):
                    nv = ctx.nat_voice("A")
                    scenes.append(Scene(text=p["meaning"], speech=[_nat(lang, p["foreign"], nv), {"pause": 0.3},
                                                                    _vi(p["meaning"]), {"pause": 0.3},
                                                                    _nat(lang, p["foreign"], nv, 0.75),
                                                                    {"pause": opts.pause * 0.6}],
                                        voice=ctx.voices["A"], card=_card(lang, p, "tu", tag=f"{ci + j + 1}"),
                                        character=first_cast["A"], action="chi_tay", position="trai",
                                        background=lessons[0].get("background", "phong_khach"), item=p.get("item", "")))
                body.append({"title": t, "project": proj(t, scenes), "phrases": grp})

    # ----- mở đầu + kết -----
    toc = [c["title"] for c in body]
    hello = f"Chào mừng bạn! Trong video này, chúng ta cùng học {L.name_vi} chủ đề {title}."
    intro = [
        _slide("title", [_vi(hello)], ctx.voices["N"], title=title, subtitle=FORMATS[fmt].split(" (")[0],
               cast=[first_cast["A"], first_cast["B"]], lang=lang),
        _slide("toc", [_vi(f"Video gồm {len(toc)} phần. Bắt đầu thôi!")], ctx.voices["N"], title="Nội dung video",
               items=toc[:12]),
    ]
    outro = [_slide("outro", [_vi("Cảm ơn bạn đã xem! Lưu video để ôn lại, đăng ký kênh và bình luận chủ đề "
                                  "bạn muốn học tiếp nhé!")], ctx.voices["N"], title="Cảm ơn bạn đã xem!",
                    subtitle="Đăng ký kênh • Lưu video để ôn", cast=[first_cast["A"], first_cast["B"]], lang=lang)]
    chapters.append({"title": "Mở đầu", "project": proj("Mở đầu", intro), "phrases": []})
    chapters += body
    chapters.append({"title": "Kết thúc", "project": proj("Kết thúc", outro), "phrases": []})
    return chapters


# ---------------- dựng + ghép ----------------
def _ts(sec: float) -> str:
    sec = int(sec)
    return f"{sec // 3600}:{sec // 60 % 60:02d}:{sec % 60:02d}" if sec >= 3600 else f"{sec // 60:02d}:{sec % 60:02d}"


def _srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def build_long(lessons: List[dict], fmt: str, title: str, opts: Optional[LongOptions] = None,
               progress: Optional[Callable[[float, str], None]] = None, only_chapters: Optional[List[int]] = None) -> dict:
    opts = opts or LongOptions()
    prog = progress or (lambda p, m: print(f"[{p:4.0%}] {m}", flush=True))
    lang = lessons[0]["lang"]
    L = LANGS[lang]
    out_dir = PROJECTS / "_long" / f"{slug(title)}-{fmt}-{lang}"
    out_dir.mkdir(parents=True, exist_ok=True)
    chapters = plan(lessons, fmt, title, opts)
    ropts = RenderOptions(watermark=L.handle, quality=opts.quality, layout=opts.layout)
    if opts.music == "on" or (opts.music == "auto" and fmt == "luyen_nghe"):
        from .formats_extra import ambient_music
        ropts.music = str(ambient_music(out_dir / "nhac_nen.wav", 480))
        ropts.music_volume = 0.12
    videos, marks, srt, t0 = [], [], [], 0.0
    for ci, ch in enumerate(chapters):
        work = out_dir / f"ch{ci:02d}"
        done = work / "done.json"
        if only_chapters is None or ci in only_chapters or not done.exists():
            base = ci / len(chapters)
            res = build(ch["project"], ch["project"].scenes[0].voice or "vieneu:Hải Đăng", "card", ropts,
                        speed=opts.speed, export=False, work_dir=work,
                        progress=lambda p, m, ci=ci, base=base: prog(base + p / len(chapters),
                                                                    f"[Chương {ci}/{len(chapters) - 1}] {m}"))
            done.write_text(json.dumps({"video": res["video"], "duration": res["duration"]}), encoding="utf-8")
        info = json.loads(done.read_text(encoding="utf-8"))
        videos.append(info["video"])
        marks.append((t0, ch["title"]))
        # phụ đề từ mốc thời gian của từng đoạn giọng
        pj = json.loads((work / "project.json").read_text(encoding="utf-8"))
        st = t0
        for s in pj["scenes"]:
            for a, b, txt in (s.get("caption_span") or []):
                srt.append((st + a, st + b, txt))
            for a, b in (s.get("native_spans") or []):
                c = s.get("card") or {}
                srt.append((st + a, st + b, "\n".join(x for x in (c.get("foreign"), c.get("meaning")) if x)))
            st += s["duration"]
        t0 += info["duration"]

    # ghép chương (cùng thông số mã hoá → copy, không mã hoá lại)
    lst = out_dir / "concat.txt"
    lst.write_text("".join(f"file '{Path(v).resolve().as_posix()}'\n" for v in videos), encoding="utf-8")
    final = out_dir / f"{slug(title)}-{fmt}.mp4"
    subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", "-movflags", "+faststart", str(final)], check=True)

    chap_txt = "\n".join(f"{_ts(t)} {name}" for t, name in marks)
    (out_dir / "chuong_youtube.txt").write_text(chap_txt, encoding="utf-8")
    srt.sort()
    (out_dir / "phu_de.srt").write_text(
        "\n".join(f"{i + 1}\n{_srt_time(a)} --> {_srt_time(b)}\n{txt}\n" for i, (a, b, txt) in enumerate(srt)),
        encoding="utf-8")
    all_phrases = [(ch["title"], ch["phrases"]) for ch in chapters if ch["phrases"]]
    thumb = make_thumbnail(title, FORMATS[fmt].split(" (")[0], lang, lessons, out_dir / "thumbnail.jpg")
    pdf = make_pdf(title, lang, all_phrases, out_dir / "tom_tat.pdf")
    desc = (f"{title} — {FORMATS[fmt].split(' (')[0]}\n\n{chap_txt}\n\n"
            f"📄 Tải PDF tóm tắt các câu trong video (link ở bình luận ghim).\n{' '.join(L.hashtags)}")
    (out_dir / "mo_ta_youtube.txt").write_text(desc, encoding="utf-8")
    prog(1.0, "Xong video dài")
    return {"video": str(final), "duration": t0, "chapters": chap_txt, "srt": str(out_dir / "phu_de.srt"),
            "thumbnail": str(thumb), "pdf": str(pdf), "description": str(out_dir / "mo_ta_youtube.txt"),
            "folder": str(out_dir)}


# ---------------- thumbnail + PDF ----------------
def make_thumbnail(title: str, subtitle: str, lang: str, lessons: List[dict], out: Path) -> Path:
    from .character import load
    from .images import _wrap, font
    W, H = 1280, 720
    img = Image.new("RGB", (W, H), "#1B2A41")
    d = ImageDraw.Draw(img)
    d.polygon([(0, 0), (W * 0.62, 0), (W * 0.5, H), (0, H)], fill="#FFB400")
    flag = {"en": "TIẾNG ANH", "zh": "TIẾNG TRUNG", "ko": "TIẾNG HÀN"}[lang]
    d.rounded_rectangle([40, 36, 40 + d.textlength(flag, font=font(44)) + 50, 110], 20, fill="#E63946")
    d.text((65, 73), flag, font=font(44), fill="#FFFFFF", anchor="lm")
    ft = font(70)
    y = 170
    for ln in _wrap(d, title.upper(), ft, W * 0.44)[:4]:
        d.text((46, y), ln, font=ft, fill="#1B2A41", stroke_width=3, stroke_fill="#FFFFFF")
        y += 92
    d.text((48, H - 70), subtitle, font=font(36, "Bold"), fill="#1B2A41")
    cast = lessons[0].get("cast", {})
    for i, key in enumerate([cast.get("A", "bo"), cast.get("B", "mai")]):
        im = load(key).render("vui_mung" if i else "chi_tay", 0.3, expression="vui")
        im = im.crop(im.getbbox())
        th = int(H * 0.78)
        im = im.resize((int(im.width * th / im.height), th), Image.LANCZOS)
        if i:
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
        img.paste(im, (int(W * (0.68 + 0.18 * i)) - im.width // 2, H - th), im)
    ph = next((p for les in lessons for p in extract_phrases(les)), None)
    if ph:
        fc = cjk_font(lang, 58)
        w = d.textlength(ph["foreign"], font=fc) + 60
        d.rounded_rectangle([W - w - 30, 30, W - 30, 120], 24, fill="#FFFFFF", outline="#1B2A41", width=6)
        d.text((W - 30 - w / 2, 75), ph["foreign"], font=fc, fill="#1B2A41", anchor="mm")
    img.save(out, quality=92)
    return out


def make_pdf(title: str, lang: str, groups, out: Path) -> Path:
    """Bảng tóm tắt A4 (ngoại ngữ – phiên âm – nghĩa) theo chương — quà tặng / sản phẩm bán kèm."""
    from .images import font
    W, H, M = 1240, 1754, 90
    pages, page, y = [], None, 0

    def new_page():
        nonlocal page, y
        page = Image.new("RGB", (W, H), "#FFFFFF")
        pages.append(page)
        dd = ImageDraw.Draw(page)
        dd.rectangle([0, 0, W, 130], fill="#1B2A41")
        dd.text((M, 65), title, font=font(46), fill="#FFFFFF", anchor="lm")
        dd.text((W - M, 65), LANGS[lang].channel, font=font(26, "Bold"), fill="#FFB400", anchor="rm")
        dd.text((W // 2, H - 50), f"Trang {len(pages)}", font=font(24, "Bold"), fill="#888888", anchor="mm")
        y = 180
        return dd

    d = new_page()
    for name, phrases in groups:
        if y > H - 300:
            d = new_page()
        d.rounded_rectangle([M, y, W - M, y + 64], 14, fill="#FFB400")
        d.text((M + 24, y + 32), name, font=font(32), fill="#1B2A41", anchor="lm")
        y += 90
        for p in phrases:
            if y > H - 170:
                d = new_page()
            d.text((M + 10, y), p["foreign"], font=cjk_font(lang, 40), fill="#1B2A41")
            if p.get("roman"):
                d.text((M + 10, y + 52), p["roman"], font=roman_font(26), fill="#6C757D")
            d.text((W - M - 10, y + 12), p.get("meaning", ""), font=font(28, "Bold"), fill="#264653", anchor="ra")
            y += 100
            d.line([M, y - 12, W - M, y - 12], fill="#E9ECEF", width=2)
        y += 20
    pages[0].save(out, save_all=True, append_images=pages[1:], resolution=150)
    return out


# ---------------- LLM: lên dàn ý nhiều chương cùng chủ đề ----------------
def generate_long(topic: str, lang: str, n: int = 5, style: str = "giao_tiep", level: str = "người mới bắt đầu",
                  model: str = "qwen2.5:7b", host: str = "http://localhost:11434") -> List[dict]:
    import requests
    from .script import _extract_json
    prompt = (f"Lập dàn ý video dài dạy {LANGS[lang].name_vi} cho người Việt, chủ đề lớn: \"{topic}\", trình độ {level}. "
              f"Chia thành đúng {n} tình huống/chủ đề con nối tiếp nhau hợp lý (ví dụ du lịch: sân bay → taxi → "
              f"khách sạn → nhà hàng → mua sắm). Chỉ trả JSON: {{\"parts\": [\"chủ đề con 1\", ...]}}")
    r = requests.post(f"{host}/api/generate", json={"model": model, "prompt": prompt, "stream": False,
                                                    "format": "json"}, timeout=300)
    r.raise_for_status()
    parts = _extract_json(r.json()["response"]).get("parts", [])[:n]
    return [lessonmod.generate(f"{topic} — {p}", lang, level, model, host, style=style) for p in parts]
