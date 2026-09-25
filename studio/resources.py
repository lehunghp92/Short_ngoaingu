"""Nguồn MỞ dùng để bám đúng trình độ khi LLM viết kịch bản (tải 1 lần, lưu ở models/wordlists/).

- 🇨🇳 HSK 3.0 (cấp 1-9): github.com/drkameleon/complete-hsk-vocabulary — MIT
- 🇰🇷 NIKL 한국어 학습용 어휘 목록 (A/B/C) + TOPIK 초급/중급: github.com/julienshim/combined_korean_vocabulary_list — MIT
       (có cột 漢字 → dùng cho định dạng Mổ xẻ chữ / so sánh Hán-Việt)
- 🇬🇧 CEFR-J Wordlist A1-B2 + Octanove C1/C2: github.com/openlanguageprofiles/olp-en-cefrj — CC BY-SA 4.0
- 💬 Câu ví dụ thật: Tatoeba API (CC BY 2.0 FR) — kèm bản dịch Việt/Anh nếu có
Không có mạng → các hàm trả về rỗng, LLM vẫn viết theo khung trình độ (studio/curriculum.py).
"""
import csv
import io
import json
import random
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from .config import ROOT

CACHE = ROOT / "models" / "wordlists"
HSK_URL = "https://raw.githubusercontent.com/drkameleon/complete-hsk-vocabulary/main/wordlists/exclusive/new/{n}.json"
KO_URL = "https://raw.githubusercontent.com/julienshim/combined_korean_vocabulary_list/master/results.tsv"
EN_URLS = ["https://raw.githubusercontent.com/openlanguageprofiles/olp-en-cefrj/master/cefrj-vocabulary-profile-1.5.csv",
           "https://raw.githubusercontent.com/openlanguageprofiles/olp-en-cefrj/master/octanove-vocabulary-profile-c1c2-1.0.csv"]
TATOEBA = "https://api.tatoeba.org/unstable/sentences"
TATOEBA_LANG = {"en": "eng", "zh": "cmn", "ko": "kor"}


def _get(url: str, name: str) -> str:
    f = CACHE / name
    if f.exists():
        return f.read_text(encoding="utf-8")
    import requests
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(r.text, encoding="utf-8")
    return r.text


# ---------------- danh sách từ theo level 1-5 ----------------
def _zh() -> List[dict]:
    out = []
    for n in range(1, 8):          # 7 = cấp 7-9
        for w in json.loads(_get(HSK_URL.format(n=n), f"hsk_{n}.json")):
            f = (w.get("forms") or [{}])[0]
            out.append({"word": w["simplified"], "hsk": n, "roman": f.get("transcriptions", {}).get("pinyin", ""),
                        "meaning": "; ".join(f.get("meanings", [])[:2])})
    return out


def _ko() -> List[dict]:
    rows = list(csv.DictReader(io.StringIO(_get(KO_URL, "ko_nikl_topik.tsv")), delimiter="\t"))
    out = []
    for r in rows:
        word = re.sub(r"\d+$", "", r["word"]).strip("-")
        if not word:
            continue
        rank = int(r["rank"]) if r.get("rank", "").isdigit() else 99999
        nik, top = r.get("nikl_level", ""), r.get("topik_level", "")
        if nik == "A":
            lv = 1 if rank <= 1000 else 2
        elif nik == "B":
            lv = 3 if rank <= 3000 else 4
        elif nik == "C":
            lv = 5
        else:
            lv = 2 if top == "초급" else 4
        out.append({"word": word, "level": lv, "hanja": r.get("hanja", ""), "pos": r.get("part_of_speech", ""),
                    "meaning": r.get("explanation", "")})
    return out


def _en() -> List[dict]:
    lv = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 5}
    out = []
    for i, u in enumerate(EN_URLS):
        for r in csv.DictReader(io.StringIO(_get(u, f"en_cefr_{i}.csv"))):
            for hw in r["headword"].split("/"):
                if r.get("CEFR") in lv:
                    out.append({"word": hw.strip(), "level": lv[r["CEFR"]], "pos": r.get("pos", "")})
    return out


@lru_cache(maxsize=3)
def wordlist(lang: str) -> List[dict]:
    """Toàn bộ danh sách từ đã gắn level 1-5 (tiếng Trung: HSK 5-6 → level 5)."""
    try:
        if lang == "zh":
            return [{**w, "level": min(5, w["hsk"]) if w["hsk"] <= 6 else 6} for w in _zh()]
        return _ko() if lang == "ko" else _en()
    except Exception as e:  # noqa: BLE001 — không có mạng
        print(f"[resources] không tải được danh sách từ {lang}: {e}")
        return []


def vocab(lang: str, level: int, n: int = 40, only_new: bool = True, seed=None, hanja: bool = False) -> List[dict]:
    """Lấy ngẫu nhiên n từ ĐÚNG level (only_new) hoặc <= level. hanja=True: chỉ từ Hán-Hàn có 漢字."""
    pool = [w for w in wordlist(lang) if (w["level"] == level if only_new else w["level"] <= level)]
    if hanja:
        pool = [w for w in pool if w.get("hanja")]
    seen, uniq = set(), []
    for w in pool:
        if w["word"] not in seen:
            seen.add(w["word"])
            uniq.append(w)
    random.Random(seed).shuffle(uniq)
    return uniq[:n]


@lru_cache(maxsize=3)
def _known(lang: str) -> Dict[str, int]:
    d = {}
    for w in wordlist(lang):
        k = w["word"].lower()
        d[k] = min(d.get(k, 99), w["level"])        # từ đồng hình: lấy level thấp nhất
    return d


# ---------------- kiểm tra kịch bản có vượt trình độ không ----------------
_EN_SUFFIX = ("ing", "ed", "es", "s", "er", "est", "ly")
_KO_PARTICLES = sorted(["은", "는", "이", "가", "을", "를", "에", "에서", "에게", "한테", "도", "만", "의", "로", "으로", "와", "과",
                        "하고", "요", "까지", "부터", "처럼", "보다"], key=len, reverse=True)


def _level_of(lang: str, tok: str) -> int:
    k = _known(lang)
    t = tok.lower()
    if t in k:
        return k[t]
    if lang == "en":
        for suf in _EN_SUFFIX:
            if t.endswith(suf) and t[: -len(suf)] in k:
                return k[t[: -len(suf)]]
            if t.endswith(suf) and t[: -len(suf)] + "e" in k:
                return k[t[: -len(suf)] + "e"]
    if lang == "ko":
        for p in _KO_PARTICLES:
            if t.endswith(p) and t[: -len(p)] in k:
                return k[t[: -len(p)]]
        for i in range(len(t) - 1, 0, -1):         # gốc động/tính từ: 가요 → 가다
            if t[:i] + "다" in k:
                return k[t[:i] + "다"]
            if t[:i] in k:
                return k[t[:i]]
    return 0          # không có trong danh sách (tên riêng, số, từ lóng...)


def check_level(lesson: dict, level: int) -> dict:
    """Tỉ lệ từ vượt level trong các câu ngoại ngữ. Trả {"above": [...], "unknown": [...], "ratio": 0.xx}."""
    lang = lesson["lang"]
    if not wordlist(lang):
        return {"above": [], "unknown": [], "ratio": 0.0, "note": "chưa tải được danh sách từ"}
    texts = []
    for t in lesson.get("turns", []):
        texts += [t.get("native", "")] + [c.get("text", "") for c in t.get("compare", []) if c.get("lang") == lang]
        for key in ("anatomy", "breakdown"):
            if t.get(key):
                texts.append(t[key].get("word") or t[key].get("sentence", ""))
    above, unknown, total = [], [], 0
    for txt in texts:
        if lang == "zh":
            try:
                import jieba          # tách từ tốt hơn nếu có
                toks = [w for w in jieba.cut(txt) if re.match(r"[一-鿿]", w)]
            except ImportError:
                toks = re.findall(r"[一-鿿]", txt)
        elif lang == "ko":
            toks = re.findall(r"[가-힣]+", txt)
        else:
            toks = re.findall(r"[A-Za-z']+", txt)
        for tok in toks:
            total += 1
            lv = _level_of(lang, tok)
            if lang == "zh" and lv == 0 and len(tok) > 1:      # từ ghép lạ → xét từng chữ
                lv = max((_level_of(lang, ch) for ch in tok), default=0)
            if lv > level:
                above.append(f"{tok}(L{lv})")
            elif lv == 0:
                unknown.append(tok)
    return {"above": sorted(set(above)), "unknown": sorted(set(unknown)),
            "ratio": round(len(above) / total, 3) if total else 0.0}


# ---------------- câu ví dụ thật từ Tatoeba ----------------
def examples(lang: str, word: str, n: int = 3) -> List[dict]:
    """Câu thật chứa `word` (ưu tiên có bản dịch Việt, không có thì Anh). Lỗi mạng → []."""
    try:
        import requests
        out = []
        for tr in ("vie", "eng"):
            r = requests.get(TATOEBA, params={"lang": TATOEBA_LANG[lang], "q": word, "sort": "relevance",
                                              "limit": 10, "trans:lang": tr}, timeout=20)
            r.raise_for_status()
            for s in r.json().get("data", []):
                lim = 60 if lang == "en" else 25
                if word not in s["text"] or len(s["text"]) > lim or re.search(r"(?i)tatoeba|타토에바|塔托埃巴", s["text"]):
                    continue
                t = next((x["text"] for x in s.get("translations", []) if x["lang"] == tr), "")
                if t and all(o["text"] != s["text"] for o in out):
                    out.append({"text": s["text"], "trans": t, "trans_lang": tr, "src": f"tatoeba #{s['id']}"})
            if len(out) >= n:
                break
        return out[:n]
    except Exception:  # noqa: BLE001
        return []
