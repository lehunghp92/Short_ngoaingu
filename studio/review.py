"""RÀ SOÁT kịch bản trước khi dựng/đăng.

1) check_rules(lesson)      — kiểm tra nhanh không cần mạng: thiếu nghĩa, sai chữ viết (VD câu Hàn lẫn chữ Hán),
                              câu quá dài so với level, đáp án quiz không có trong lựa chọn, thời lượng ngoài 40-50 s...
2) review_llm(lesson)       — LLM thứ hai (Ollama) soát câu ngoại ngữ: đúng ngữ pháp? tự nhiên? nghĩa Việt khớp?
3) export_sheet / import_sheet — bảng CSV (mở bằng Excel/Google Sheets) cho người bản xứ duyệt nhanh:
                              cột "ok" (x = đạt) và "sua_thanh" (câu sửa). Nhập lại → tự cập nhật file kịch bản.
4) estimate_seconds(lesson) — ước lượng thời lượng TRƯỚC khi dựng (không cần TTS).
"""
import csv
import json
import re
from pathlib import Path
from typing import List

from .langs import LANGS

VI_WPS = 3.3                                    # tiếng Việt: âm tiết/giây (giọng 1.0x)
NATIVE_RATE = {"en": ("word", 2.6), "zh": ("char", 4.0), "ko": ("char", 5.0)}
SCRIPT = {"zh": r"[一-鿿]", "ko": r"[가-힣ㄱ-ㅎㅏ-ㅣ]", "en": r"[A-Za-z]"}
FOREIGN_SCRIPT = {"ko": r"[一-鿿]", "zh": r"[가-힣]", "en": r"[一-鿿가-힣]"}


def _units(lang, text):
    kind, _ = NATIVE_RATE[lang]
    return len(re.findall(r"[A-Za-z']+", text)) if kind == "word" else len(re.findall(r"\w", text))


def _nat_sec(lang, text, speed=1.0):
    return 0.35 + _units(lang, text) / NATIVE_RATE[lang][1] / speed


def estimate_seconds(lesson: dict) -> float:
    """Ước lượng thời lượng short từ kịch bản (sai số ~±15%)."""
    from .lesson import level_num  # noqa: F401  (giữ import nhẹ)
    lang, t_all = lesson["lang"], 0.0
    style = lesson.get("style", "")
    for t in lesson.get("turns", []):
        t_all += 0.3 + float(t.get("gap", 0.3))
        if t.get("say"):
            t_all += len(t["say"].split()) / VI_WPS
        mark = t.get("mark", "dung" if t.get("native") else "")
        if t.get("native"):
            t_all += _nat_sec(lang, t["native"])
            slow = mark in ("dung", "tu") or (mark == "thoai" and style in ("giao_tiep", "nhap_vai"))
            if style == "chat":
                slow = False
            if t.get("repeat", slow):
                t_all += 0.3 + _nat_sec(lang, t["native"], 0.75)
            t_all += float(t.get("shadow", 0) or 0)
        if mark == "quiz_q":
            t_all += 3.0
        for c in t.get("compare", []):
            t_all += _nat_sec(c["lang"], c["text"]) + 0.5
        if t.get("anatomy", {}).get("word"):
            w = t["anatomy"]["word"]
            t_all += _nat_sec(lang, w) + 0.4 + _nat_sec(lang, w, 0.75)
        for it in t.get("pron", {}).get("items", []):
            t_all += _nat_sec(lang, it["text"], 0.85) + 0.8
        if t.get("breakdown"):
            s = t["breakdown"]["sentence"]
            t_all += _nat_sec(lang, s) + 0.5 + _nat_sec(lang, s, 0.75)
    return round(t_all, 1)


# ---------------- 1) kiểm tra theo quy tắc ----------------
def _foreign_texts(t, lang):
    out = []
    if t.get("native"):
        out.append(("native", lang, t["native"]))
    for c in t.get("compare", []):
        out.append(("compare", c["lang"], c["text"]))
    for key, fld in (("anatomy", "word"), ("breakdown", "sentence")):
        if t.get(key, {}).get(fld):
            out.append((key, lang, t[key][fld]))
    for it in t.get("pron", {}).get("items", []):
        out.append(("pron", lang, it["text"]))
    return out


def check_rules(lesson: dict, level: int = 0) -> List[dict]:
    from .curriculum import MAX_LEN
    from .lesson import level_num
    lang = lesson["lang"]
    lv = level or level_num(lesson.get("level", 0) or 5)
    issues = []

    def add(i, sev, msg):
        issues.append({"turn": i + 1 if i >= 0 else "-", "muc": sev, "van_de": msg})

    turns = lesson.get("turns", [])
    if not turns:
        add(-1, "LỖI", "Kịch bản không có lượt nào")
    for i, t in enumerate(turns):
        if not any(t.get(k) for k in ("say", "native", "compare", "anatomy", "pron", "breakdown")):
            add(i, "LỖI", "Lượt trống (không có lời/câu nào)")
        if t.get("native") and not t.get("meaning") and t.get("mark") != "sai":
            add(i, "CẢNH BÁO", f"Thiếu nghĩa tiếng Việt cho: {t['native']}")
        for fld, lg, txt in _foreign_texts(t, lang):
            if not re.search(SCRIPT[lg], txt):
                add(i, "LỖI", f"[{fld}] '{txt}' không có chữ {LANGS[lg].name_vi}")
            if re.search(FOREIGN_SCRIPT[lg], txt):
                add(i, "LỖI", f"[{fld}] '{txt}' lẫn chữ viết của ngôn ngữ khác")
            lim = MAX_LEN[lg][lv - 1] if lv else 99
            n = len(txt.split()) if lg in ("en", "ko") else len(re.findall(r"[一-鿿]", txt))
            if fld in ("native", "breakdown") and n > lim:
                add(i, "CẢNH BÁO", f"Câu dài {n} (> {lim} cho level {lv}): {txt}")
        if t.get("options"):
            a = t.get("answer", 0)
            if not isinstance(a, int) or not 0 <= a < len(t["options"]):
                add(i, "LỖI", "Chỉ số đáp án (answer) nằm ngoài danh sách lựa chọn")
            nxt = turns[i + 1] if i + 1 < len(turns) else {}
            if nxt.get("native") and isinstance(a, int) and 0 <= a < len(t["options"]) and nxt.get("mark") != "sai":
                norm = lambda x: re.sub(r"[\W_]+", "", x.lower())  # noqa: E731
                if norm(t["options"][a]) not in norm(nxt["native"]) and norm(nxt["native"]) not in norm(t["options"][a]):
                    add(i, "CẢNH BÁO", f"Đáp án đúng '{t['options'][a]}' khác câu công bố '{nxt['native']}'")
        if t.get("say") and len(t["say"].split()) > 22:
            add(i, "CẢNH BÁO", "Lời Việt dài > 22 từ — nên tách hoặc rút gọn")
    if turns and turns[0].get("say") and len(turns[0]["say"].split()) > 12:
        add(0, "CẢNH BÁO", "Câu mở đầu dài > 12 từ — short nên vào thẳng nội dung")
    if turns and turns[-1].get("say") and len(turns[-1]["say"].split()) > 12:
        add(len(turns) - 1, "CẢNH BÁO", "Câu kết dài > 12 từ — nên ngắn gọn")
    sec = estimate_seconds(lesson)
    if sec < 38:
        add(-1, "CẢNH BÁO", f"Ước lượng ~{sec:.0f}s — ngắn hơn 40s, nên thêm 2-4 lượt dạy")
    elif sec > 55:
        add(-1, "CẢNH BÁO", f"Ước lượng ~{sec:.0f}s — dài hơn 50s, nên bớt lượt")
    return issues


# ---------------- 2) LLM soát lỗi ----------------
REVIEW_PROMPT = """Bạn là giáo viên {lang_vi} bản xứ, rà soát kịch bản dạy {lang_vi} cho người Việt.
Với MỖI câu dưới đây, kiểm tra: (1) đúng ngữ pháp/chính tả, (2) người bản xứ có nói tự nhiên như vậy không,
(3) nghĩa tiếng Việt có khớp không, (4) có hợp trình độ {level} không. Câu đánh dấu "SAI_CỐ_Ý" là câu sai để dạy — bỏ qua.
Chỉ trả JSON: {{"items":[{{"id":số,"ok":true/false,"loi":"mô tả ngắn (nếu có)","sua":"câu {lang_vi} đề xuất (nếu cần)",
"nghia_sua":"nghĩa Việt đề xuất (nếu cần)"}}]}}
Danh sách câu:
{rows}"""


def _rows(lesson):
    lang, rows = lesson["lang"], []
    for i, t in enumerate(lesson.get("turns", [])):
        for fld, lg, txt in _foreign_texts(t, lang):
            meaning = t.get("meaning", "") if fld in ("native", "compare") else \
                (t.get(fld, {}).get("meaning", "") if fld in ("anatomy", "breakdown") else "")
            rows.append({"id": len(rows) + 1, "turn": i + 1, "field": fld, "lang": lg, "text": txt,
                         "meaning": meaning, "intentional_error": t.get("mark") == "sai"})
    return rows


def review_llm(lesson: dict, model: str = "qwen2.5:7b", host: str = "http://localhost:11434") -> List[dict]:
    import requests
    from .curriculum import LEVEL_NAMES
    from .lesson import level_num
    from .script import _extract_json
    rows = _rows(lesson)
    if not rows:
        return []
    lv = level_num(lesson.get("level", 1))
    txt = "\n".join(f'{r["id"]}. [{r["lang"]}] {r["text"]} = "{r["meaning"]}"' + (" SAI_CỐ_Ý" if r["intentional_error"] else "")
                    for r in rows)
    prompt = REVIEW_PROMPT.format(lang_vi=LANGS[lesson["lang"]].name_vi, level=LEVEL_NAMES[lesson["lang"]][lv - 1],
                                  rows=txt)
    r = requests.post(f"{host}/api/generate", json={"model": model, "prompt": prompt, "stream": False,
                                                    "format": "json", "options": {"temperature": 0.1}}, timeout=600)
    r.raise_for_status()
    got = {int(x.get("id", 0)): x for x in _extract_json(r.json()["response"]).get("items", [])}
    out = []
    for row in rows:
        g = got.get(row["id"], {})
        if row["intentional_error"] or g.get("ok", True):
            continue
        out.append({"turn": row["turn"], "cau": row["text"], "nghia": row["meaning"], "loi": g.get("loi", ""),
                    "de_xuat": g.get("sua", ""), "nghia_de_xuat": g.get("nghia_sua", "")})
    return out


# ---------------- 3) bảng duyệt cho người bản xứ ----------------
SHEET_COLS = ["file", "turn", "field", "lang", "cau_goc", "nghia", "ok", "sua_thanh", "nghia_sua", "ghi_chu"]


def export_sheet(files: List[str], out: Path) -> Path:
    """CSV UTF-8 (có BOM để Excel đọc đúng tiếng Việt/Hàn/Trung)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SHEET_COLS)
        w.writeheader()
        for f in files:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
            d.setdefault("lang", Path(f).stem.rpartition("_")[2])
            for r in _rows(d):
                w.writerow({"file": str(f), "turn": r["turn"], "field": r["field"], "lang": r["lang"],
                            "cau_goc": r["text"], "nghia": r["meaning"], "ok": "", "sua_thanh": "", "nghia_sua": "",
                            "ghi_chu": "câu sai cố ý" if r["intentional_error"] else ""})
    return out


def import_sheet(path: Path) -> List[str]:
    """Áp dụng các ô 'sua_thanh' / 'nghia_sua' vào file kịch bản. Trả về danh sách thay đổi."""
    changes, cache = [], {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            new, new_m = (row.get("sua_thanh") or "").strip(), (row.get("nghia_sua") or "").strip()
            if not new and not new_m:
                continue
            f = row["file"]
            d = cache.setdefault(f, json.loads(Path(f).read_text(encoding="utf-8")))
            t = d["turns"][int(row["turn"]) - 1]
            old = row["cau_goc"]
            fld = row["field"]
            if fld == "native" and t.get("native") == old:
                t["native"] = new or old
                if new_m:
                    t["meaning"] = new_m
            elif fld == "compare":
                for c in t.get("compare", []):
                    if c["text"] == old:
                        c["text"] = new or old
                if new_m:
                    t["meaning"] = new_m
            elif fld in ("anatomy", "breakdown"):
                key = "word" if fld == "anatomy" else "sentence"
                if t[fld].get(key) == old:
                    t[fld][key] = new or old
                    if new_m:
                        t[fld]["meaning"] = new_m
            elif fld == "pron":
                for it in t["pron"].get("items", []):
                    if it["text"] == old:
                        it["text"] = new or old
                        if new_m:
                            it["meaning"] = new_m
            else:
                continue
            changes.append(f"{Path(f).name} lượt {row['turn']}: {old} → {new or old}" + (f" ({new_m})" if new_m else ""))
    for f, d in cache.items():
        Path(f).write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changes
