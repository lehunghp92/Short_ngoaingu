"""KHUNG NỘI DUNG: 10 định dạng × 5 level × 3 ngôn ngữ — "bản đề cương" để LLM viết kịch bản chi tiết.

Level chung 1-5 ↔ chuẩn quốc tế:
  🇬🇧 CEFR  A1 · A2 · B1 · B2 · C1      🇨🇳 HSK 1 · 2 · 3 · 4 · 5-6      🇰🇷 TOPIK 1 · 2 · 3 · 4 · 5-6
Mỗi ô (định dạng, ngôn ngữ, level) cho LLM biết:
  - Hồ sơ trình độ: ngữ pháp được dùng, độ dài câu, kiểu lời nói, chủ đề hợp level
  - Trọng tâm riêng của định dạng ở level đó (VD phát âm tiếng Hàn L4 = biến âm 비음화/경음화)
  - Series gợi ý (tên tập) để lên lịch đăng
  - Từ vựng ĐÚNG level lấy từ danh sách mở (studio/resources.py) + câu ví dụ thật từ Tatoeba
Sau khi LLM viết, check_level() đếm các từ vượt level để cảnh báo.
"""
from dataclasses import dataclass, field
from typing import Dict, List

from .langs import LANGS

LEVEL_NAMES = {
    "en": ["CEFR A1", "CEFR A2", "CEFR B1", "CEFR B2", "CEFR C1"],
    "zh": ["HSK 1", "HSK 2", "HSK 3", "HSK 4", "HSK 5-6"],
    "ko": ["TOPIK 1", "TOPIK 2", "TOPIK 3", "TOPIK 4", "TOPIK 5-6"],
}
LEVEL_VI = ["Level 1 · Mới bắt đầu", "Level 2 · Sơ cấp", "Level 3 · Trung cấp", "Level 4 · Trung cao cấp",
            "Level 5 · Cao cấp"]
MAX_LEN = {"en": (6, 9, 12, 16, 20), "zh": (8, 12, 16, 22, 28), "ko": (4, 6, 8, 10, 12)}
LEN_UNIT = {"en": "từ", "zh": "chữ Hán", "ko": "cụm từ (어절)"}

GRAMMAR = {
    "en": [
        ["to be", "present simple", "can / can't", "there is / there are", "this / that", "imperatives",
         "Wh-questions", "possessives my/your"],
        ["past simple", "present continuous", "be going to", "comparatives & superlatives", "would like",
         "some/any, how much/many", "should"],
        ["present perfect", "past continuous", "will vs going to", "first conditional", "used to",
         "gerund vs infinitive", "relative clauses who/which/that", "must / have to"],
        ["second & third conditional", "passive voice", "reported speech", "I wish", "common phrasal verbs",
         "modals of deduction (must have)", "although / however / despite"],
        ["inversion (Never have I…)", "mixed conditionals", "cleft sentences (What I need is…)", "idioms & collocations",
         "hedging & softening", "register: formal vs casual"],
    ],
    "zh": [
        ["是", "有", "吗 / 呢 câu hỏi", "的", "不 / 没", "很 + tính từ", "几 / 多少", "在 + nơi chốn", "想 / 要"],
        ["了 (đã xong)", "过 (từng)", "在…呢 (đang)", "比 so sánh", "要…了 (sắp)", "因为…所以", "得 bổ ngữ trình độ",
         "还是 / 或者"],
        ["把", "被", "越来越", "一…就", "虽然…但是", "bổ ngữ kết quả 完/好/到", "bổ ngữ xu hướng 上来/下去",
         "除了…以外", "如果…就"],
        ["连…都", "既…又", "不但…而且", "无论…都", "即使…也", "难道", "由于", "bổ ngữ khả năng 得了/不了"],
        ["thành ngữ 4 chữ (成语)", "何况", "与其…不如", "宁可", "未必", "văn viết 之/其/则", "固然", "以免"],
    ],
    "ko": [
        ["이에요/예요", "은/는 · 이/가", "을/를", "-아요/어요 (hiện tại)", "있어요/없어요", "안 phủ định",
         "-고 싶어요", "에 / 에서", "số Hán-Hàn & thuần Hàn"],
        ["-았/었어요 (quá khứ)", "-(으)ㄹ 거예요", "-(으)세요", "-아서/어서", "-지만", "-(으)ㄹ 수 있다/없다",
         "-고 있다", "-(으)면", "-아/어야 하다"],
        ["-는데", "-(으)니까", "-기 때문에", "định ngữ -(으)ㄴ/는/(으)ㄹ", "-게 되다", "-아/어 보다", "-(으)려고",
         "-는 것 같다", "반말 cơ bản"],
        ["-더라고요", "-(으)ㄹ 뻔했다", "-다고 하다 (gián tiếp)", "-도록", "-(으)ㄹ수록", "-는 바람에",
         "bị động / sai khiến", "-기는 하지만"],
        ["-(으)ㄹ 리가 없다", "-는 셈이다", "-기 마련이다", "-(으)ㄴ 탓에", "속담 & 관용어", "từ Hán-Hàn trang trọng",
         "văn tin tức 합니다체", "-거니와"],
    ],
}
SPEECH = {
    "en": ["câu ngắn, rõ, giọng thân thiện", "câu đơn + câu ghép and/but", "tự nhiên, có từ nối",
           "tự nhiên, có phrasal verbs, idiom thông dụng", "như người bản xứ, sắc thái, chơi chữ"],
    "zh": ["câu ngắn, tránh 把/被", "khẩu ngữ đơn giản", "khẩu ngữ tự nhiên, có từ đệm 啊/吧/嘛",
           "khẩu ngữ + văn viết nhẹ", "thành ngữ, văn viết, sắc thái"],
    "ko": ["chỉ dùng 해요체", "해요체", "해요체 + 반말 giữa bạn bè", "해요체/반말/합니다체 theo quan hệ",
           "đủ các kính ngữ, 합니다체 trang trọng, 사투리 nhẹ"],
}
TOPICS = [
    ["chào hỏi", "giới thiệu bản thân", "số & giá tiền", "gia đình", "đồ ăn uống", "màu sắc & quần áo", "giờ & ngày",
     "ở nhà", "lớp học", "cảm ơn & xin lỗi"],
    ["mua sắm", "gọi món", "hỏi đường", "phương tiện", "thời tiết", "sở thích", "hẹn gặp", "đi khám bệnh",
     "khách sạn", "cuối tuần"],
    ["sự cố khi du lịch", "đời văn phòng", "thuê nhà", "bạn bè & cảm xúc", "mạng xã hội", "sức khoẻ",
     "phàn nàn ở nhà hàng", "ngân hàng & bưu điện", "lễ hội & văn hoá", "học tập"],
    ["phỏng vấn xin việc", "họp & email", "mặc cả / đàm phán", "tin tức", "môi trường", "tranh luận quan điểm",
     "các mối quan hệ", "công nghệ", "chăm sóc khách hàng", "văn hoá công sở"],
    ["thuyết trình", "kinh tế & xã hội", "văn học & thành ngữ", "hài hước & chơi chữ", "nói giảm nói tránh",
     "phỏng vấn truyền thông", "triết lý sống", "phương ngữ & giọng vùng", "lịch sử", "khoa học phổ thông"],
]

# ---------- trọng tâm từng định dạng theo level (chung cho 3 ngôn ngữ, trừ khi có bản riêng) ----------
FOCUS: Dict[str, List[str]] = {
    "giao_tiep": ["1 câu mẫu cho 1 tình huống, hỏi–đáp 2 lượt, chỉ tay vào đồ vật",
                  "hội thoại 4-6 lượt có số lượng, giá, lựa chọn",
                  "xử lý sự cố: đổi hàng, trễ chuyến, mất đồ",
                  "phàn nàn lịch sự, thương lượng, yêu cầu đặc biệt",
                  "tình huống tế nhị: từ chối khéo, nói giảm nói tránh, xin lỗi trang trọng"],
    "chat": ["chào / ok / cảm ơn / emoji, tin 1-3 từ", "hẹn giờ, hỏi đang làm gì, rủ đi chơi",
             "viết tắt & tiếng lóng nhắn tin phổ biến CỦA NGÔN NGỮ NÀY (VD Hàn ㅋㅋ ㅇㅇ, Trung 哈哈 666, Anh lol btw)",
             "nhắn công việc: lịch sự vs thân mật, xin nghỉ, báo trễ", "meme, chơi chữ, mỉa mai nhẹ, sắc thái cảm xúc"],
    "do_vui": ["chọn nghĩa đúng của từ (có hình đồ vật)", "chọn câu đúng cho tình huống",
               "chọn đúng cấu trúc ngữ pháp level 3", "chọn cách nói TỰ NHIÊN nhất (cả 3 đều đúng ngữ pháp)",
               "đoán nghĩa thành ngữ / sắc thái"],
    "top_sai": ["lỗi phát âm & trật tự từ cơ bản", "lỗi thì / lượng từ / trợ từ",
                "lỗi dịch word-by-word từ tiếng Việt", "lỗi kính ngữ, sai ngữ cảnh trang trọng",
                "lỗi kết hợp từ (collocation) & sắc thái"],
    "so_sanh_3": ["chào, cảm ơn, số đếm", "câu hỏi thường ngày", "từ gốc Hán giống tiếng Việt (zh/ko) vs tiếng Anh",
                  "thành ngữ tương đương 3 thứ tiếng", "khác biệt văn hoá trong cách nói"],
    "cau_thoai": ["câu cảm thán ngắn hay gặp trong phim", "câu thoại đời thường trong phim",
                  "câu thoại có ngữ pháp level 3", "trích ≤ 1 câu lời bài hát / thoại nói nhanh",
                  "chơi chữ, tiếng lóng, giọng địa phương trong phim"],
    "phim_bo": ["series 'Ngày đầu ở nước ngoài' (sân bay → nhà trọ → cửa hàng)",
                "series 'Du học / làm thêm' (lớp học, quán ăn, ký túc xá)",
                "series 'Đời văn phòng' (sếp, đồng nghiệp, deadline)",
                "series 'Khởi nghiệp & tình yêu' (gọi vốn, hẹn hò, hiểu lầm)",
                "series 'Drama gia đình / công ty' (tranh luận, thương lượng, đảo ngược)"],
    "thu_thach": ["30 ngày sinh tồn: 3 câu/ngày", "30 ngày nói trôi chảy chủ đề hằng ngày",
                  "30 ngày ngữ pháp trung cấp (1 cấu trúc/ngày)", "30 ngày tiếng công sở",
                  "30 ngày thành ngữ & diễn đạt như người bản xứ"],
    "phat_am": {
        "zh": ["4 thanh + thanh nhẹ, cặp mā/má/mǎ/mà", "biến điệu 不 / 一 và thanh 3 + thanh 3",
               "phụ âm dễ nhầm zh/z, ch/c, sh/s, j/q/x", "vận mẫu ü, -n/-ng, âm cuốn lưỡi 儿化",
               "ngữ điệu câu, nhịp thành ngữ, giọng Bắc vs Nam"],
        "ko": ["nguyên âm ㅓ/ㅗ, ㅡ/ㅜ, ㅐ/ㅔ", "phụ âm thường / bật hơi / căng (ㄱ ㅋ ㄲ)",
               "7 âm cuối batchim & nối âm 연음", "biến âm 비음화, 경음화, ㅎ탈락",
               "ngữ điệu, giọng Busan vs Seoul, nói nhanh tự nhiên"],
        "en": ["th /θ/ /ð/, âm cuối -s", "nguyên âm ngắn/dài (ship/sheep), đuôi -ed", "trọng âm từ & âm schwa",
               "nối âm, weak forms, flap t (water)", "ngữ điệu, nhấn câu, giọng Anh–Mỹ–Úc"],
    },
    "mo_xe_chu": {
        "zh": ["chữ tượng hình đơn (人 口 日 月 木 水)", "hội ý ghép 2 bộ (好 明 休 林)",
               "hình thanh: bộ nghĩa + phần âm (妈 吗 骂)", "từ ghép Hán-Việt 2 chữ (学生 = học sinh)",
               "thành ngữ 4 chữ: tách nghĩa từng chữ"],
        "ko": ["ghép Hangul phụ âm + nguyên âm (가 나 다)", "batchim tạo âm tiết (한 = ㅎ+ㅏ+ㄴ)",
               "từ Hán-Hàn ↔ Hán-Việt (학생 學生 = học sinh)", "tiền/hậu tố Hán-Hàn (-적, 무-, 불-, -성)",
               "사자성어 & từ ghép trang trọng"],
        "en": ["từ ghép (sunflower, toothbrush)", "hậu tố -er / -ful / -less", "tiền tố un- / re- / dis-",
               "gốc Latin/Hy Lạp (port, spect, dict)", "họ từ & nguồn gốc từ thú vị"],
    },
}
SERIES = {    # tên series gợi ý cho từng định dạng (thêm "#tập")
    "giao_tiep": "Tiếng {lang} đời thường", "chat": "Nhắn tin tiếng {lang}", "do_vui": "Đố vui tiếng {lang}",
    "top_sai": "Người Việt hay sai", "so_sanh_3": "1 câu 3 thứ tiếng", "mo_xe_chu": "Mổ xẻ chữ",
    "phat_am": "Phát âm chuẩn", "cau_thoai": "Học qua phim", "phim_bo": "Phim bộ", "thu_thach": "Thử thách 30 ngày",
}


@dataclass
class Cell:
    fmt: str
    lang: str
    level: int
    level_name: str
    focus: str
    grammar: List[str]
    max_len: int
    speech: str
    topics: List[str]
    vocab: List[dict] = field(default_factory=list)
    examples: List[dict] = field(default_factory=list)


def focus(fmt: str, lang: str, level: int) -> str:
    f = FOCUS.get(fmt, FOCUS["giao_tiep"])
    return (f[lang] if isinstance(f, dict) else f)[level - 1]


def cell(fmt: str, lang: str, level: int, with_vocab: bool = True, n_vocab: int = 40, seed=None,
         with_examples: bool = False) -> Cell:
    level = max(1, min(5, int(level)))
    c = Cell(fmt, lang, level, LEVEL_NAMES[lang][level - 1], focus(fmt, lang, level),
             GRAMMAR[lang][level - 1], MAX_LEN[lang][level - 1], SPEECH[lang][level - 1], TOPICS[level - 1])
    if with_vocab:
        from .resources import examples, vocab
        c.vocab = vocab(lang, level, n_vocab, seed=seed, hanja=(fmt == "mo_xe_chu" and lang == "ko" and level >= 3))
        if with_examples:
            for w in c.vocab[:4]:
                c.examples += examples(lang, w["word"], 1)
    return c


def brief(fmt: str, lang: str, level: int, topic: str = "", with_vocab: bool = True,
          with_examples: bool = False) -> str:
    """Đoạn "đề cương" chèn vào prompt LLM (tiếng Việt)."""
    c = cell(fmt, lang, level, with_vocab, with_examples=with_examples)
    L = LANGS[lang]
    lines = [f"TRÌNH ĐỘ: {LEVEL_VI[level - 1]} ({c.level_name}).",
             f"- Trọng tâm của định dạng ở level này: {c.focus}.",
             f"- Ngữ pháp được dùng (không dùng cấu trúc cao hơn): {', '.join(c.grammar)}"
             + (" + mọi cấu trúc level thấp hơn." if level > 1 else "."),
             f"- Câu {L.name_vi} tối đa {c.max_len} {LEN_UNIT[lang]}. Kiểu lời nói: {c.speech}.",
             f"- Chủ đề hợp level: {', '.join(c.topics)}."]
    if topic:
        lines.append(f"- Chủ đề tập này: {topic}.")
    if c.vocab:
        ws = ", ".join(w["word"] + (f"({w['hanja']})" if w.get("hanja") else "") for w in c.vocab)
        lines.append(f"- Từ vựng ĐÚNG level (danh sách chuẩn {c.level_name}); chọn 5-8 từ HỢP CHỦ ĐỀ, "
                     f"bỏ qua từ không liên quan: {ws}.")
    if c.examples:
        ex = "; ".join(f"{e['text']} = {e['trans']}" for e in c.examples)
        lines.append(f"- Câu mẫu thật (Tatoeba, có thể dùng/biến tấu): {ex}.")
    return "\n".join(lines)


def episodes(fmt: str, lang: str, level: int, n: int = 10) -> List[dict]:
    """Danh sách tập gợi ý (không cần LLM): mỗi tập = 1 chủ đề của level, gắn trọng tâm định dạng."""
    c = cell(fmt, lang, level, with_vocab=False)
    series = SERIES[fmt].format(lang=LANGS[lang].name_vi.replace("tiếng ", "").replace("Tiếng ", ""))
    out = []
    for i in range(n):
        t = c.topics[i % len(c.topics)]
        out.append({"episode": i + 1, "series": f"{series} · L{level}", "topic": t, "focus": c.focus,
                    "style": fmt, "level": level})
    return out


def matrix() -> List[dict]:
    """Toàn bộ khung 10 × 3 × 5 (không kèm từ vựng) — để xem trên app / xuất tài liệu."""
    from .teach_styles import FORMATS10
    return [{"format": name, "style": key, "lang": lang, "level": lv, "level_name": LEVEL_NAMES[lang][lv - 1],
             "focus": focus(key, lang, lv), "grammar": ", ".join(GRAMMAR[lang][lv - 1][:4]) + "…",
             "max_len": f"{MAX_LEN[lang][lv - 1]} {LEN_UNIT[lang]}"}
            for key, name in FORMATS10 for lang in ("en", "zh", "ko") for lv in range(1, 6)]


def write_doc(path) -> None:
    """Xuất CURRICULUM.md từ chính dữ liệu trong code (luôn đồng bộ)."""
    from .teach_styles import FORMATS10
    out = ["# Khung nội dung: 10 định dạng × 5 level × 3 ngôn ngữ", "",
           "> Tệp này được sinh tự động từ `studio/curriculum.py`. Chạy `python curriculum_cli.py doc` để cập nhật.",
           "", "## Thang level", "", "| Level | 🇬🇧 Anh | 🇨🇳 Trung | 🇰🇷 Hàn | Độ dài câu (Anh / Trung / Hàn) |",
           "|---|---|---|---|---|"]
    for i in range(5):
        out.append(f"| {LEVEL_VI[i]} | {LEVEL_NAMES['en'][i]} | {LEVEL_NAMES['zh'][i]} | {LEVEL_NAMES['ko'][i]} | "
                   f"{MAX_LEN['en'][i]} từ / {MAX_LEN['zh'][i]} chữ / {MAX_LEN['ko'][i]} 어절 |")
    out += ["", "## Ngữ pháp theo level", ""]
    for lang, flag in (("en", "🇬🇧"), ("zh", "🇨🇳"), ("ko", "🇰🇷")):
        out += [f"### {flag} {LANGS[lang].name_vi}", ""]
        for i in range(5):
            out.append(f"- **L{i + 1} ({LEVEL_NAMES[lang][i]})**: {', '.join(GRAMMAR[lang][i])}. *Lời nói:* {SPEECH[lang][i]}")
        out.append("")
    out += ["## Chủ đề theo level", ""] + [f"- **L{i + 1}**: {', '.join(t)}" for i, t in enumerate(TOPICS)]
    out += ["", "## Trọng tâm từng định dạng theo level", ""]
    for key, name in FORMATS10:
        out += [f"### {name}", ""]
        f = FOCUS[key]
        if isinstance(f, dict):
            out += ["| Level | 🇬🇧 Anh | 🇨🇳 Trung | 🇰🇷 Hàn |", "|---|---|---|---|"]
            out += [f"| L{i + 1} | {f['en'][i]} | {f['zh'][i]} | {f['ko'][i]} |" for i in range(5)]
        else:
            out += [f"- **L{i + 1}**: {x}" for i, x in enumerate(f)]
        out.append("")
    out += ["## Nguồn mở dùng để bám level", "",
            "- HSK 3.0: github.com/drkameleon/complete-hsk-vocabulary (MIT)",
            "- NIKL + TOPIK: github.com/julienshim/combined_korean_vocabulary_list (MIT), có cột 漢字 cho Hán-Việt",
            "- CEFR-J + Octanove: github.com/openlanguageprofiles/olp-en-cefrj (CC BY-SA 4.0)",
            "- Câu ví dụ thật: Tatoeba (CC BY 2.0 FR). Ghi nguồn khi dùng nguyên câu.", ""]
    from pathlib import Path
    Path(path).write_text("\n".join(out), encoding="utf-8")
