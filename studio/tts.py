"""Giọng đọc (TTS) mã nguồn mở, chạy offline trên CPU. Chọn MODULE (engine) rồi chọn giọng.

- vieneu : https://github.com/pnnbao97/VieNeu-TTS (Apache-2.0) — TIẾNG VIỆT tự nhiên, 25 giọng mẫu
           Bắc/Trung/Nam, nhân bản giọng từ file mẫu. pip install vieneu "onnxruntime<1.23"
- qwen   : Qwen3-TTS (Alibaba, Apache-2.0) — giọng bản ngữ TRUNG/HÀN/ANH rất tự nhiên, chạy GPU (CUDA).
           Mặc định model 0.6B-CustomVoice (đổi bằng biến SHORTS_QWEN_MODEL, VD bản 1.7B). pip install qwen-tts
- omnivoice : G-OmniVoice (fine-tune tiếng Việt từ k2-fsa/OmniVoice, Apache-2.0) — MODULE DỰ PHÒNG tiếng Việt,
           nhân bản giọng từ file mẫu (25 giọng VieNeu có sẵn trong assets/voices hoặc giọng bạn tự thu).
           Chạy trong môi trường riêng (xem setup_omnivoice.bat) vì xung đột thư viện với qwen-tts.
- clone  : "1 NHÂN VẬT = 1 GIỌNG": nhân bản giọng tiếng Việt của nhân vật để nói Trung/Hàn/Anh
           (Qwen3-TTS Base; dự phòng OmniVoice).
- piper  : https://github.com/OHF-Voice/piper1-gpl — có giọng TIẾNG VIỆT, nhẹ, nhanh.
- kokoro : https://github.com/hexgrad/kokoro (Apache-2.0) — tiếng Anh rất tự nhiên (cần torch).
- silent : không có giọng, ước lượng thời lượng theo số chữ (để dựng thử bố cục).
"""
import subprocess
import wave
from pathlib import Path

import numpy as np
import requests

from .config import ASSETS, MODELS

HF = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
PIPER_VOICES = {
    "vi-vais1000 (Việt, nữ)": "vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium",
    "vi-25hours (Việt, nữ)": "vi/vi_VN/25hours_single/low/vi_VN-25hours_single-low",
    "vi-vivos (Việt, nhiều giọng)": "vi/vi_VN/vivos/x_low/vi_VN-vivos-x_low",
    "en-ryan (Anh, nam)": "en/en_US/ryan/high/en_US-ryan-high",
    "en-lessac (Anh, nữ)": "en/en_US/lessac/medium/en_US-lessac-medium",
    "zh-huayan (Trung, nữ)": "zh/zh_CN/huayan/medium/zh_CN-huayan-medium",
    "ko-kss (Hàn, nữ)": "ko/ko_KR/kss/medium/ko_KR-kss-medium",
}
KOKORO_VOICES = {"kokoro-am_michael (Anh, nam)": "am_michael", "kokoro-af_heart (Anh, nữ)": "af_heart",
                 "kokoro-bm_george (Anh-Anh, nam)": "bm_george"}
SR = 24000


VIENEU_FALLBACK = ["Trúc Ly", "Hải Đăng", "Adam bựa", "Thiện Minh", "Mai Anh", "Ngọc Huyền", "Thùy Dung",
                   "Quang Sơn", "Ngọc Trân", "Đoan Trang", "Quốc Tuấn", "Ngọc Linh", "Thục Đoan", "Mỹ Duyên"]
QWEN_VOICES = {   # giọng có sẵn của Qwen3-TTS CustomVoice (nói được đa ngôn ngữ)
    "vivian": "Vivian — nữ trẻ, Trung (Phổ thông)", "serena": "Serena — nữ dịu dàng, Trung",
    "dylan": "Dylan — nam Bắc Kinh", "uncle_fu": "Uncle Fu — nam trầm, Trung", "eric": "Eric — nam Tứ Xuyên",
    "sohee": "Sohee — nữ Hàn Quốc", "ryan": "Ryan — nam Anh (Mỹ)", "aiden": "Aiden — nam Anh (Mỹ)",
    "ono_anna": "Ono Anna — nữ Nhật",
}
QWEN_LANG = {"zh": "Chinese", "ko": "Korean", "en": "English", "ja": "Japanese"}
ENGINES = {
    "omnivoice": "OmniVoice tiếng Việt (dự phòng, nhân bản giọng)",
    "qwen": "Qwen3-TTS (giọng bản ngữ Trung/Hàn/Anh, GPU)",
    "vieneu": "VieNeu-TTS (tiếng Việt, khuyên dùng)",
    "piper": "Piper (Việt/Anh/Trung/Hàn, rất nhẹ)",
    "kokoro": "Kokoro (tiếng Anh)",
    "silent": "Không giọng (dựng thử bố cục)",
}


def engine_available(engine: str) -> bool:
    try:
        if engine == "vieneu":
            import vieneu  # noqa: F401
        elif engine == "piper":
            import piper  # noqa: F401
        elif engine == "kokoro":
            import kokoro  # noqa: F401
        elif engine == "qwen":
            import qwen_tts  # noqa: F401
        elif engine == "omnivoice":
            return omni_python() is not None
        return True
    except ImportError:
        return False


def voices_for(engine: str) -> list:
    """Danh sách giọng (mã đầy đủ dạng 'engine:tên') cho một module TTS."""
    if engine == "vieneu":
        try:
            names = [vid for _, vid in _vieneu().list_preset_voices()]
        except Exception:  # noqa: BLE001 - chưa cài / chưa tải model
            names = VIENEU_FALLBACK
        return [f"vieneu:{n}" for n in names]
    if engine == "omnivoice":
        return [f"omnivoice:{n}" for n in reference_voices()]
    if engine == "piper":
        return list(PIPER_VOICES)
    if engine == "qwen":
        return [f"qwen:{k}" for k in QWEN_VOICES]
    if engine == "kokoro":
        return list(KOKORO_VOICES)
    return ["silent (không giọng, dựng thử)"]


def available_voices() -> list:
    return voices_for("vieneu") + list(PIPER_VOICES) + list(KOKORO_VOICES) + ["silent (không giọng, dựng thử)"]


# ================= Giọng mẫu (reference) — nền tảng của nhân bản giọng =================


VOICE_DIR = ASSETS / "voices"          # <tên>.wav + <tên>.txt (lời của đoạn mẫu) — thả giọng của bạn vào đây
REF_TEXT = "Xin chào các bạn, hôm nay chúng ta cùng học một câu giao tiếp thật hay và dễ nhớ nhé."


def reference_voices() -> list:
    """Tên các giọng mẫu có sẵn (file trong assets/voices)."""
    return sorted(p.stem for p in VOICE_DIR.glob("*.wav") if p.with_suffix(".txt").exists())


def voice_reference(voice: str):
    """(đường dẫn wav, lời thoại) của giọng — dùng làm mẫu để nhân bản sang engine/ngôn ngữ khác."""
    name = voice.split(":", 1)[1] if ":" in voice else voice
    if name.startswith("file:"):
        p = Path(name[5:])
        return str(p), p.with_suffix(".txt").read_text(encoding="utf-8").strip()
    p = VOICE_DIR / f"{name}.wav"
    if p.exists():
        return str(p), p.with_suffix(".txt").read_text(encoding="utf-8").strip()
    # giọng chưa có mẫu: tạo 1 lần bằng chính engine của nó rồi lưu lại
    cache = MODELS / "refs" / f"{name.replace(' ', '_')}.wav"
    if not cache.exists():
        synthesize(REF_TEXT, voice if ":" in voice else f"vieneu:{name}", cache, 1.0, lang="vi")
        cache.with_suffix(".txt").write_text(REF_TEXT, encoding="utf-8")
    return str(cache), REF_TEXT


def omni_python():
    """Python của môi trường OmniVoice riêng (biến SHORTS_OMNI_PYTHON hoặc thư mục venv-omnivoice)."""
    import os
    root = Path(__file__).resolve().parent.parent
    for c in (os.environ.get("SHORTS_OMNI_PYTHON"), root / "venv-omnivoice" / "Scripts" / "python.exe",
              root / "venv-omnivoice" / "bin" / "python"):
        if c and Path(c).exists():
            return str(c)
    return None


class _OmniWorker:
    def __init__(self):
        import json
        self.json = json
        worker = Path(__file__).resolve().parent / "omni_worker.py"
        self.proc = subprocess.Popen([omni_python(), str(worker)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     text=True, encoding="utf-8", bufsize=1)
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("OmniVoice worker không khởi động được (xem setup_omnivoice.bat)")
            if line.startswith("{") and self.json.loads(line).get("ready"):
                break

    def say(self, text, ref_audio, ref_text, out):
        self.proc.stdin.write(self.json.dumps({"text": text, "ref_audio": ref_audio, "ref_text": ref_text,
                                               "out": str(out)}, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("OmniVoice worker dừng đột ngột")
            if line.startswith("{"):
                r = self.json.loads(line)
                if not r.get("ok"):
                    raise RuntimeError(r.get("error"))
                return


def _omni():
    if "omni" not in _cache:
        _cache["omni"] = _OmniWorker()
    return _cache["omni"]


def _qwen_base():
    """Qwen3-TTS Base: nhân bản giọng từ file mẫu sang Trung/Hàn/Anh."""
    if "qwen_base" not in _cache:
        import os
        import torch
        from qwen_tts import Qwen3TTSModel
        name = os.environ.get("SHORTS_QWEN_BASE", "Qwen/Qwen3-TTS-12Hz-0.6B-Base")
        cuda = torch.cuda.is_available() and not os.environ.get("SHORTS_NO_GPU")
        kw = {"device_map": "cuda:0", "dtype": torch.bfloat16} if cuda else {"device_map": "cpu", "dtype": torch.float32}
        _cache["qwen_base"] = Qwen3TTSModel.from_pretrained(name, **kw)
    return _cache["qwen_base"]


def _postprocess(tmp: Path, out: Path, speed: float) -> None:
    from .gpu import ffmpeg_exe
    subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(tmp), "-af", f"atempo={speed:.3f}",
                    "-ac", "1", "-ar", str(SR), str(out)], check=True)
    tmp.unlink(missing_ok=True)


def _qwen():
    """Nạp Qwen3-TTS 1 lần; GPU (bfloat16) nếu có CUDA, không thì CPU (chậm hơn nhiều)."""
    if "qwen" not in _cache:
        import os
        import torch
        from qwen_tts import Qwen3TTSModel
        name = os.environ.get("SHORTS_QWEN_MODEL", "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice")
        cuda = torch.cuda.is_available() and not os.environ.get("SHORTS_NO_GPU")
        kw = {"device_map": "cuda:0", "dtype": torch.bfloat16} if cuda else {"device_map": "cpu", "dtype": torch.float32}
        try:
            import flash_attn  # noqa: F401
            if cuda:
                kw["attn_implementation"] = "flash_attention_2"
        except ImportError:
            pass
        _cache["qwen"] = Qwen3TTSModel.from_pretrained(name, **kw)
    return _cache["qwen"]


def _vieneu():
    if "vieneu" not in _cache:
        from vieneu import Vieneu
        _cache["vieneu"] = Vieneu()
    return _cache["vieneu"]


def _download(url: str, dest: Path) -> Path:
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        r = requests.get(url, timeout=300)
        r.raise_for_status()
        dest.write_bytes(r.content)
    return dest


_cache = {}


def _piper(key: str):
    if key not in _cache:
        from piper import PiperVoice
        rel = PIPER_VOICES[key]
        onnx = _download(HF + rel + ".onnx", MODELS / "piper" / (Path(rel).name + ".onnx"))
        _download(HF + rel + ".onnx.json", MODELS / "piper" / (Path(rel).name + ".onnx.json"))
        _cache[key] = PiperVoice.load(str(onnx))
    return _cache[key]


def _kokoro(voice: str):
    if "kokoro" not in _cache:
        from kokoro import KPipeline  # pip install kokoro soundfile
        _cache["kokoro"] = {"a": KPipeline(lang_code="a"), "b": KPipeline(lang_code="b")}
    return _cache["kokoro"][voice[0]]


def _write_wav(path: Path, audio: np.ndarray, sr: int) -> None:
    pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / wf.getframerate()


HEAVY = ("clone:", "qwen:", "omnivoice:", "vieneu:")


def synthesize(text: str, voice: str, out: Path, speed: float = 1.1, lang: str = "") -> float:
    """Tạo file WAV cho một câu; trả về thời lượng (giây). speed > 1 = đọc nhanh hơn (nhịp short).
    Model nặng (clone/qwen/omnivoice/vieneu): kết quả được nhớ đệm theo (câu, giọng, ngôn ngữ) → đọc lại
    chậm 0.75x hoặc dựng lại video không phải chạy model lần nữa."""
    out.parent.mkdir(parents=True, exist_ok=True)
    if voice.startswith(HEAVY) and speed != 1.0:
        import hashlib
        key = hashlib.sha1(f"{voice}|{lang}|{text}".encode("utf-8")).hexdigest()[:20]
        base = MODELS / "tts_cache" / f"{key}.wav"
        if not base.exists():
            _synthesize(text, voice, base, 1.0, lang)
        from .gpu import ffmpeg_exe
        subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(base), "-af", f"atempo={speed:.3f}",
                        "-ac", "1", "-ar", str(SR), str(out)], check=True)
        return wav_duration(out)
    if voice.startswith(HEAVY):
        import hashlib
        import shutil
        key = hashlib.sha1(f"{voice}|{lang}|{text}".encode("utf-8")).hexdigest()[:20]
        base = MODELS / "tts_cache" / f"{key}.wav"
        if not base.exists():
            _synthesize(text, voice, base, 1.0, lang)
        shutil.copyfile(base, out)
        return wav_duration(out)
    return _synthesize(text, voice, out, speed, lang)


def _synthesize(text: str, voice: str, out: Path, speed: float = 1.1, lang: str = "") -> float:
    out.parent.mkdir(parents=True, exist_ok=True)
    if voice.startswith("clone:"):
        # 1 nhân vật = 1 giọng: nói ngoại ngữ bằng chính giọng tiếng Việt của nhân vật
        ref_audio, ref_text = voice_reference(voice.split(":", 1)[1])
        tmp = out.with_suffix(".raw.wav")
        if engine_available("qwen") and lang in QWEN_LANG:
            wavs, sr = _qwen_base().generate_voice_clone(text=text, language=QWEN_LANG[lang], ref_audio=ref_audio,
                                                         ref_text=ref_text)
            _write_wav(tmp, np.asarray(wavs[0], dtype=np.float32), sr)
        elif engine_available("omnivoice"):
            _omni().say(text, ref_audio, ref_text, tmp)
        else:
            raise RuntimeError("Cần Qwen3-TTS (pip install qwen-tts) hoặc OmniVoice để giữ 1 giọng cho nhân vật")
        _postprocess(tmp, out, speed)
    elif voice.startswith("omnivoice:"):
        ref_audio, ref_text = voice_reference(voice)
        tmp = out.with_suffix(".raw.wav")
        _omni().say(text, ref_audio, ref_text, tmp)
        _postprocess(tmp, out, speed)
    elif voice.startswith("qwen:"):
        wavs, sr = _qwen().generate_custom_voice(text=text, language=QWEN_LANG.get(lang, "Auto"),
                                                speaker=voice.split(":", 1)[1])
        tmp = out.with_suffix(".raw.wav")
        _write_wav(tmp, np.asarray(wavs[0], dtype=np.float32), sr)
        from .gpu import ffmpeg_exe
        subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(tmp), "-af", f"atempo={speed:.3f}",
                        "-ac", "1", "-ar", str(SR), str(out)], check=True)
        tmp.unlink(missing_ok=True)
    elif voice.startswith("vieneu:") and not engine_available("vieneu") and engine_available("omnivoice"):
        # dự phòng: VieNeu chưa cài/lỗi → OmniVoice nhân bản đúng giọng VieNeu từ file mẫu có sẵn
        return synthesize(text, "omnivoice:" + voice.split(":", 1)[1], out, speed, lang)
    elif voice.startswith("vieneu:"):
        v = _vieneu()
        audio = v.infer(text, voice=voice.split(":", 1)[1])
        tmp = out.with_suffix(".raw.wav")
        v.save(audio, str(tmp))
        # đổi tốc độ nói (không đổi cao độ) + đưa về mono 24 kHz như các engine khác
        from .gpu import ffmpeg_exe
        subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(tmp),
                        "-af", f"atempo={speed:.3f}", "-ac", "1", "-ar", str(SR), str(out)], check=True)
        tmp.unlink(missing_ok=True)
    elif voice in PIPER_VOICES:
        from piper import SynthesisConfig
        v = _piper(voice)
        with wave.open(str(out), "wb") as wf:
            v.synthesize_wav(text, wf, syn_config=SynthesisConfig(length_scale=1 / speed))
    elif voice in KOKORO_VOICES:
        vid = KOKORO_VOICES[voice]
        chunks = [a.numpy() if hasattr(a, "numpy") else np.asarray(a)
                  for _, _, a in _kokoro(vid)(text, voice=vid, speed=speed)]
        _write_wav(out, np.concatenate(chunks), SR)
    else:
        secs = max(1.2, len(text.split()) / (2.9 * speed))
        _write_wav(out, np.zeros(int(secs * SR), dtype=np.float32), SR)
    _pad(out, 0.12)
    return wav_duration(out)


def silence(out: Path, secs: float) -> float:
    out.parent.mkdir(parents=True, exist_ok=True)
    _write_wav(out, np.zeros(int(secs * SR), dtype=np.float32), SR)
    return secs


def _pad(path: Path, secs: float) -> None:
    """Thêm khoảng lặng ngắn cuối câu cho nhịp tự nhiên."""
    with wave.open(str(path), "rb") as wf:
        params, frames = wf.getparams(), wf.readframes(wf.getnframes())
    pad = b"\x00" * int(params.framerate * secs) * params.sampwidth * params.nchannels
    with wave.open(str(path), "wb") as wf:
        wf.setparams(params)
        wf.writeframes(frames + pad)


def concat(wavs: list, out: Path, ffmpeg: str) -> None:
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{Path(w).resolve().as_posix()}'\n" for w in wavs), encoding="utf-8")
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-ar", str(SR), "-ac", "1", str(out)], check=True)
