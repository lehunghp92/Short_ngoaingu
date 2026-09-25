"""Cấu hình 3 kênh học ngoại ngữ: giọng bản ngữ, phiên âm tự động, font, hashtag."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List

import requests
from PIL import ImageFont

from .config import ASSETS


def _pinyin(text: str) -> str:
    from pypinyin import Style, pinyin
    return " ".join(x[0] for x in pinyin(text, style=Style.TONE) if x[0].strip())


def _romaja(text: str) -> str:
    from korean_romanizer.romanizer import Romanizer
    return Romanizer(text).romanize()


def _ipa(text: str) -> str:
    import eng_to_ipa
    out = eng_to_ipa.convert(text)
    return "/" + out.replace("*", "") + "/"


@dataclass
class Lang:
    code: str
    name_vi: str
    native_voice: str
    romanize: Callable[[str], str]
    native_voice_male: str = ""
    font_url: str = ""
    font_file: str = ""
    channel: str = ""
    handle: str = ""
    hashtags: List[str] = field(default_factory=list)


LANGS = {
    "en": Lang("en", "tiếng Anh", "en-lessac (Anh, nữ)", _ipa, native_voice_male="en-ryan (Anh, nam)", channel="Học Tiếng Anh cùng Bơ", handle="@HocTiengAnhCungBo",
               hashtags=["#hoctienganh", "#tienganhgiaotiep", "#english", "#learnenglish", "#tienganh"]),
    "zh": Lang("zh", "tiếng Trung", "zh-huayan (Trung, nữ)", _pinyin,
               font_url="https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf",
               font_file="NotoSansSC.ttf", channel="Học Tiếng Trung cùng Bơ", handle="@HocTiengTrungCungBo",
               hashtags=["#hoctiengtrung", "#tiengtrung", "#chinese", "#hsk", "#中文"]),
    "ko": Lang("ko", "tiếng Hàn", "ko-kss (Hàn, nữ)", _romaja,
               font_url="https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/notosanskr/NotoSansKR%5Bwght%5D.ttf",
               font_file="NotoSansKR.ttf", channel="Học Tiếng Hàn cùng Bơ", handle="@HocTiengHanCungBo",
               hashtags=["#hoctienghan", "#tienghan", "#korean", "#한국어", "#kdrama"]),
}

# Giọng bản ngữ theo module: (nữ, nam)
NATIVE_VOICES = {
    "piper": {"en": ("en-lessac (Anh, nữ)", "en-ryan (Anh, nam)"), "zh": ("zh-huayan (Trung, nữ)", ""),
              "ko": ("ko-kss (Hàn, nữ)", "")},
    "qwen": {"en": ("qwen:serena", "qwen:ryan"), "zh": ("qwen:vivian", "qwen:dylan"), "ko": ("qwen:sohee", "")},
}


def native_voice(lang: str, gender: str = "nu", engine: str = "auto") -> str:
    """Chọn giọng bản ngữ. engine=auto: Qwen3-TTS cho Trung/Hàn nếu đã cài, còn lại Piper."""
    from .tts import engine_available
    if engine == "auto":
        engine = "qwen" if lang in ("zh", "ko") and engine_available("qwen") else "piper"
    female, male = NATIVE_VOICES.get(engine, NATIVE_VOICES["piper"])[lang]
    return (male or female) if gender == "nam" else female


_fonts = {}
ROMAN_FONT_URL = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/notosans/NotoSans%5Bwdth,wght%5D.ttf"


def _load_var_font(url: str, file: str, size: int, weight: str = "Bold") -> ImageFont.FreeTypeFont:
    path = ASSETS / "fonts" / file
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        r = requests.get(url, timeout=300)
        r.raise_for_status()
        path.write_bytes(r.content)
    f = ImageFont.truetype(str(path), size)
    try:
        f.set_variation_by_name(weight)
    except Exception:  # noqa: BLE001
        pass
    return f


def roman_font(size: int) -> ImageFont.FreeTypeFont:
    """Noto Sans — có đủ ký hiệu IPA và dấu thanh pinyin."""
    key = ("roman", size)
    if key not in _fonts:
        _fonts[key] = _load_var_font(ROMAN_FONT_URL, "NotoSans.ttf", size, "SemiBold")
    return _fonts[key]


def cjk_font(lang: str, size: int) -> ImageFont.FreeTypeFont:
    """Font cho chữ ngoại ngữ (Noto Sans SC/KR — OFL). Tiếng Anh dùng font chung của app."""
    from .images import font
    L = LANGS.get(lang)
    if not L or not L.font_url:
        return font(size)
    key = (lang, size)
    if key not in _fonts:
        _fonts[key] = _load_var_font(L.font_url, L.font_file, size)
    return _fonts[key]
