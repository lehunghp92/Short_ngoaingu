"""Điều phối: kịch bản -> giọng đọc -> hình ảnh -> dựng video -> xuất đa nền tảng."""
import re
import subprocess
from pathlib import Path
from typing import Callable, Optional

from . import backgrounds, images, tts
from .config import PROJECTS, STYLES, RenderOptions
from .render import FFMPEG, render
from .script import Project
from .export import export_all


def slug(text: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", text.replace("đ", "d").replace("Đ", "D"))
    s = s.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()[:60] or "video"


def build(project: Project, voice: str, image_mode: str = "card", opts: Optional[RenderOptions] = None,
          speed: float = 1.1, sd_model: str = "stabilityai/sdxl-turbo",
          progress: Optional[Callable[[float, str], None]] = None, export: bool = True,
          work_dir: Optional[Path] = None) -> dict:
    opts = opts or RenderOptions()
    prog = progress or (lambda p, m: print(f"[{p:4.0%}] {m}"))
    work = work_dir or PROJECTS / slug(project.title)
    style = STYLES.get(opts.style, STYLES["infographic"])

    # 1) Giọng đọc từng cảnh (để biết chính xác thời lượng cảnh)
    wavs = []
    for i, s in enumerate(project.scenes):
        prog(0.05 + 0.25 * i / len(project.scenes), f"Giọng đọc cảnh {i + 1}/{len(project.scenes)}")
        wav = work / "audio" / f"{i:02d}.wav"
        if s.speech:
            s.text = " ".join(seg["text"] for seg in s.speech if seg.get("lang") == "vi") or s.text
            s.duration = _speak_segments(s, voice, wav, speed, work / "audio" / "seg")
        else:
            s.duration = tts.synthesize(s.text, voice, wav, speed)
        s.audio = str(wav)
        wavs.append(wav)
    voice_track = work / "audio" / "voice.wav"
    tts.concat(wavs, voice_track, FFMPEG)
    # chuẩn hoá âm lượng -14 LUFS (chuẩn YouTube/TikTok/Instagram)
    norm = work / "audio" / "voice_norm.wav"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(voice_track),
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", str(norm)], check=True)

    # 2) Hình ảnh
    for i, s in enumerate(project.scenes):
        if s.slide:
            continue
        if s.image and Path(s.image).exists() and "/images/" not in s.image.replace("\\", "/"):
            continue  # ảnh người dùng tự chọn
        prog(0.3 + 0.3 * i / len(project.scenes), f"Hình cảnh {i + 1}/{len(project.scenes)}")
        out = work / "images" / f"{i:02d}.png"
        if s.background in backgrounds.BACKGROUNDS:
            backgrounds.generate(s.background, out, seed=i)
        elif image_mode == "sd":
            prompt = s.visual or s.text
            if s.character:   # nhân vật do rig vẽ => SD chỉ vẽ PHÔNG NỀN
                prompt = f"background scene only, no people, {prompt}"
            images.generate_sd(prompt, style, out, model=sd_model, seed=i)
        elif s.character:
            images.generate_backdrop(style, out, i)
        else:
            images.generate_card(s.text, s.overlay or _keyword(s.text), style, out, i)
        s.image = str(out)
    project.save(work / "project.json")

    # 3) Dựng video (thẻ đồ hoạ đã chứa từ khoá => không lặp lại chữ lớn phía trên)
    opts.extra["hide_overlay"] = False
    video = work / f"{slug(project.title)}.mp4"
    render(project, video, opts, norm, progress=lambda p, m: prog(0.6 + 0.38 * p, m))
    # 4) Ảnh bìa (khung hình ở cảnh hook) + xuất đa nền tảng
    cover = work / "cover.jpg"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-ss", "0.6", "-i", str(video), "-frames:v", "1",
                    str(cover)], check=True)
    total = sum(s.duration for s in project.scenes)
    exports = export_all(project, video, work / "export", total) if export else {}
    prog(1.0, "Xong")
    return {"video": str(video), "cover": str(cover), "duration": total, "exports": exports, "folder": str(work)}


def _speak_segments(s, vi_voice: str, wav: Path, speed: float, tmp: Path) -> float:
    """Ghép nhiều đoạn giọng (Việt + bản ngữ + khoảng lặng) thành 1 file; ghi lại mốc thời gian."""
    from .langs import LANGS
    parts, t = [], 0.0
    s.native_spans, s.caption_span = [], []
    for j, seg in enumerate(s.speech):
        out = tmp / f"{wav.stem}_{j}.wav"
        if "pause" in seg:
            d = tts.silence(out, float(seg["pause"]))
        elif "sfx" in seg:     # hiệu ứng âm thanh: dung / sai / tick / pop / whoosh
            from .formats_extra import sfx
            d = sfx(seg["sfx"], out)
        else:
            lang = seg.get("lang", "vi")
            v = seg.get("voice") or ((s.voice or vi_voice) if lang == "vi" else LANGS[lang].native_voice)
            sp = speed if lang == "vi" else float(seg.get("speed", 1.0))
            d = tts.synthesize(seg["text"], v, out, sp, lang=lang)
            if lang == "vi":
                s.caption_span.append([t, t + d, seg["text"]])
            else:
                s.native_spans.append([t, t + d])
        parts.append(out)
        t += d
    tts.concat(parts, wav, FFMPEG)
    return tts.wav_duration(wav)


def _keyword(text: str) -> str:
    nums = re.findall(r"\d[\d.,]*\s*%?", text)
    if nums:
        return nums[0].strip()
    words = sorted(re.findall(r"\w+", text), key=len, reverse=True)
    return words[0] if words else ""
