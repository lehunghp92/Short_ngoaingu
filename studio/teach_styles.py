"""Các PHONG CÁCH DẠY HỌC — chọn khi tạo kịch bản (thư viện hoặc LLM).

Mọi phong cách dùng chung 1 định dạng kịch bản "turns" (lượt nói), nên bộ dựng video chỉ có 1:
  who      : "A" | "B" (nhân vật trên màn hình) | "N" (người dẫn giọng đọc, không xuất hiện)
  say      : lời tiếng Việt
  native   : câu/từ ngoại ngữ (giọng bản ngữ đọc; nhân vật đang nói sẽ nhép miệng)
  meaning  : nghĩa tiếng Việt · mark: sai|dung|tu|quiz_q|thoai
  tag      : nhãn góc thẻ ("#1", "Câu 2/3", "Từ 3/5")
  shadow   : số giây im lặng để người xem NÓI THEO (hiện "Đến lượt bạn!")
  options/answer/picked: quiz trắc nghiệm A/B/C · sfx: dung|sai|pop|tick|whoosh
  compare / anatomy / pron / breakdown: màn đặc biệt (xem FORMATS10.md)
  repeat   : đọc lại chậm 0.75x · background / prop / action / expression / react: dàn dựng từng lượt
"""
from dataclasses import dataclass
from typing import Dict


@dataclass
class TeachStyle:
    key: str
    name: str
    hook_idea: str
    cast: tuple          # nhân vật A, B mặc định
    rules: str           # hướng dẫn riêng cho LLM
    when: str            # dùng khi nào


STYLES: Dict[str, TeachStyle] = {s.key: s for s in [
    TeachStyle("hoi_thoai", "💬 Hỏi – Giảng (Bơ hỏi, Mai giảng)", "Mai ơi, sao người Hàn nghe mình nói xong lại cười?",
               ("bo", "mai"),
               "A là người học tò mò hỏi bằng tiếng Việt; B là người giỏi ngoại ngữ, giải thích và đọc mẫu. "
               "Có 1 cặp sai-đúng, 1 quiz (B hỏi mark quiz_q, lượt sau trả lời bằng native).",
               "Mặc định, hợp mọi chủ đề giao tiếp"),
    TeachStyle("nhap_vai", "🎭 Nhập vai tình huống", "Đi chợ ở Hàn mà chỉ biết chỉ tay? Xem cảnh này!",
               ("du_khach", "co_tap_hoa"),
               "A và B ĐÓNG VAI trong tình huống thật (khách – người bán, bệnh nhân – bác sĩ...), "
               "lượt của A/B chủ yếu CHỈ có native + meaning (mark thoai), không có say. "
               "Xen giữa, người dẫn N (không xuất hiện) giải thích nhanh bằng tiếng Việt (say) 2-3 lần. "
               "Kết: N tóm tắt 1 câu quan trọng nhất (mark dung, repeat).",
               "Tình huống thực tế: mua sắm, nhà hàng, sân bay, bệnh viện"),
    TeachStyle("top_sai", "❌ Top 3 lỗi sai người Việt hay mắc", "3 câu người Việt hay nói sai nhất khi đi làm!",
               ("bo", "co_giao"),
               "Đếm ngược 3 lỗi: mỗi lỗi gồm lượt A nói câu SAI (native, mark sai, tag '#3', '#2', '#1'), "
               "lượt B sửa bằng câu ĐÚNG (native, mark dung, repeat) kèm say giải thích ngắn. #1 là lỗi bất ngờ nhất.",
               "Tăng tương tác, bình luận tranh luận"),
    TeachStyle("do_vui", "🏆 Game show đố vui", "Bạn trả lời được mấy câu? Cùng thử nhé!",
               ("mai", "bo"),
               "A là MC hỏi 3 câu (mark quiz_q, tag 'Câu 1/3'..., có \"options\": 3 lựa chọn ngoại ngữ và \"answer\": "
               "chỉ số đáp án đúng 0-2), B là thí sinh trả lời (native, mark dung). "
               "Có 1 câu B trả lời sai (mark sai) rồi A sửa. A khen/chọc vui giữa các câu. Kết: 'Bạn được mấy điểm? Bình luận nhé'.",
               "Ôn tập, tăng xem lại (rewatch)"),
    TeachStyle("tu_vung_nhanh", "⚡ 5 từ vựng tốc độ", "5 từ vựng ở phòng gym bạn phải biết!",
               ("ban_gym", "bo"),
               "A giới thiệu nhanh 5 từ/cụm từ theo chủ đề: mỗi từ 1 lượt có native, meaning, mark tu, tag 'Từ 1/5'..., "
               "prop hoặc background phù hợp nếu có. B phản ứng hài hước 1-2 lần. Kết: kêu gọi lưu lại.",
               "Từ vựng theo chủ đề, lượt lưu cao"),
    TeachStyle("noi_theo", "🎤 Luyện nói theo (shadowing)", "Nói theo 3 câu này mỗi ngày, bạn sẽ nói trôi chảy hơn!",
               ("co_giao", "bo"),
               "A đọc 3-4 câu mẫu (native, meaning, mark dung, repeat) và sau mỗi câu cho người xem nói theo "
               "(shadow: 2.5). B thỉnh thoảng nói theo và được A sửa phát âm (say). Kết: thử thách bình luận.",
               "Phát âm, phản xạ nói"),
    TeachStyle("ke_chuyen", "📖 Truyện chêm", "Chuyện Bơ lần đầu đi phỏng vấn bằng tiếng Anh...",
               ("bo", "ong_chu"),
               "Kể 1 câu chuyện ngắn hài hước bằng tiếng Việt (N kể, A/B diễn), chêm 3-4 từ/câu ngoại ngữ "
               "đúng lúc (native, meaning, mark tu). Có tình tiết bất ngờ ở cuối. Kết: hỏi người xem nhớ được mấy từ.",
               "Giải trí + nhớ từ theo ngữ cảnh"),
    TeachStyle("giao_tiep", "🛒 Giao tiếp hằng ngày (có cảnh & đồ vật)", "Đi tạp hoá ở Hàn, hỏi giá cái bánh này nói sao?",
               ("du_khach", "co_tap_hoa"),
               "Một tình huống đời thường TỪ ĐẦU ĐẾN CUỐI (mua đồ, gọi món, hỏi đường, check-in...). "
               "A và B nói bằng native (mark thoai) đúng như ngoài đời; N giải thích ngắn bằng tiếng Việt 2-3 lần. "
               "BẮT BUỘC: background khớp nơi chốn (tiem_tap_hoa, cho_trai_cay, nha_hang, san_bay, khach_san, "
               "benh_vien, shop_quan_ao, ben_xe_buyt, quan_ca_phe); khi câu nói nhắc tới một đồ vật thì thêm "
               "\"item\" (đồ vật hiện to giữa màn hình) và action \"chi_tay\"; khi hỏi/nói giá thêm \"price\" "
               "(VD '3.000원', '¥15', '$2.50'). Mỗi câu phải có hình ảnh/không gian tương ứng.",
               "Tình huống thực tế có hình minh hoạ: đi chợ, nhà hàng, sân bay, khách sạn, bệnh viện"),
    TeachStyle("chat", "📱 Tin nhắn (KakaoTalk / WeChat / iMessage)", "Crush người Hàn nhắn thế này, trả lời sao?",
               ("bo", "mai"),
               "Cuộc trò chuyện qua TIN NHẮN hiện trên màn hình điện thoại. A (bên phải, 'me') và B nhắn bằng native "
               "(mark thoai, meaning), mỗi lượt 1 tin ngắn đúng kiểu nhắn tin (viết tắt, ㅋㅋ, 哈哈, lol nếu hợp). "
               "Có thể thêm \"typing\":\"me\"|\"other\" để hiện 'đang soạn'. N (giọng dẫn) giải thích 2-3 lần bằng say. "
               "Kết: 'Bạn sẽ trả lời thế nào? Bình luận nhé'.",
               "Tiếng lóng, nhắn tin, hẹn hò, công việc — Gen Z rất thích"),
    TeachStyle("so_sanh_3", "🌏 1 câu – 3 ngôn ngữ (Anh/Trung/Hàn)", "Cùng một câu 'Cảm ơn', 3 thứ tiếng nói thế nào?",
               ("co_giao", "bo"),
               "4-5 lượt chính, mỗi lượt có \"compare\":[{\"lang\":\"en\",\"text\":\"...\"},{\"lang\":\"zh\","
               "\"text\":\"...\"},{\"lang\":\"ko\",\"text\":\"...\"}] và \"meaning\" (câu Việt). "
               "Xen say ngắn so sánh điểm giống/khác (VD Hán-Việt: 感谢 cảm tạ – 감사 kamsa). Kết: hỏi thích tiếng nào nhất.",
               "Đăng cả 3 kênh cùng lúc, kéo người xem chéo kênh"),
    TeachStyle("mo_xe_chu", "🔤 Mổ xẻ chữ (bộ thủ / Hán-Việt / gốc từ)", "Chữ 好 = Nữ + Tử. Vì sao lại là TỐT?",
               ("co_giao", "bo"),
               "3 từ, mỗi từ 1 lượt có \"anatomy\":{\"word\":\"...\",\"parts\":[{\"text\":\"女\",\"label\":\"nữ\"},...],"
               "\"meaning\":\"...\",\"han_viet\":\"(nếu có)\",\"tip\":\"mẹo nhớ hài hước\"} kèm say giải thích. "
               "Tiếng Trung: bộ thủ; tiếng Hàn: âm Hán-Hàn hoặc ghép Hangul (ㅎ+ㅏ+ㄴ); tiếng Anh: tiền tố/gốc/hậu tố.",
               "Người học yêu chữ viết, lượt lưu rất cao"),
    TeachStyle("phat_am", "🎤 Phát âm (thanh điệu / khẩu hình)", "Người Việt hay đọc sai 4 thanh này!",
               ("co_giao", "bo"),
               "2-3 lượt có \"pron\":{\"title\":\"...\",\"items\":[{\"text\":\"妈\",\"meaning\":\"mẹ\","
               "\"mouth\":\"open|round|spread|closed|neutral\",\"tip\":\"...\"}]} (2-4 mục/lượt: cặp dễ nhầm, 4 thanh, "
               "ㅓ/ㅗ, th/s...). Tiếng Trung tự vẽ đường thanh điệu. B đọc sai 1 lần rồi được sửa. Có shadow cho người xem.",
               "Phát âm chuẩn — câu hỏi người học tìm nhiều nhất"),
    TeachStyle("cau_thoai", "🎬 Học qua câu thoại phim / bài hát", "Câu này trong phim Hàn nghĩa thật là gì?",
               ("bo", "mai"),
               "2-3 câu thoại NỔI TIẾNG hoặc đúng kiểu phim/nhạc (KHÔNG chép nguyên lời bài hát có bản quyền; "
               "dùng câu ngắn thông dụng). Mỗi câu 1 lượt có \"breakdown\":{\"source\":\"Phim ... / Bài hát ...\","
               "\"sentence\":\"...\",\"meaning\":\"...\",\"words\":[{\"w\":\"từ\",\"m\":\"nghĩa\"}]}, "
               "sau đó A/B dùng lại câu đó trong đời thường (native, mark dung).",
               "Bám trend phim/nhạc, dễ viral"),
    TeachStyle("phim_bo", "🎭 Phim bộ nhiều tập (có 'Tập trước' / 'Còn tiếp')", "Bơ lạc ở Seoul — tập 2!",
               ("du_khach", "mai"),
               "Một tập của phim bộ: cùng nhân vật, cốt truyện nối tiếp. A/B nói native (mark thoai) trong tình huống, "
               "N giải thích 2-3 lần. Có \"previously\" (tóm tắt tập trước 1 câu Việt) và \"next\" "
               "(gợi mở tập sau, gây tò mò) ở cấp bài học. Kết tập bằng tình huống bỏ lửng.",
               "Giữ chân người xem theo series, tăng đăng ký"),
    TeachStyle("thu_thach", "📅 Thử thách 30 ngày", "Ngày 7/30: học 3 câu gọi món!",
               ("co_giao", "bo"),
               "Bài của 1 ngày trong thử thách 30 ngày (lesson có \"day\"). Lượt 1 nhắc 'Ngày N/30' + mục tiêu. "
               "Ôn 1 câu của hôm qua, học 3 câu mới (mark dung, repeat, shadow 2.5), 1 quiz trắc nghiệm có \"options\" "
               "(3 lựa chọn ngoại ngữ) và \"answer\" (chỉ số đúng). Kết: 'Hẹn mai ngày N+1, bình luận \"xong\" nhé'.",
               "Người xem quay lại mỗi ngày"),
    TeachStyle("giang", "🧑‍🏫 Giảng 1 người (sai/đúng + quiz)", "90% người Việt nói sai câu này!",
               ("bo", ""),
               "Chỉ A nói: hook, 1-2 cặp sai-đúng, 1 quiz, kết.", "Nhanh gọn, dễ sản xuất"),
]}

TURN_SCHEMA = (
    '{"who":"A|B|N","say":"lời Việt (tuỳ chọn)","native":"câu ngoại ngữ (tuỳ chọn)","meaning":"nghĩa Việt",'
    '"mark":"sai|dung|tu|quiz_q|thoai","tag":"nhãn (tuỳ chọn)","shadow":0,"repeat":false,'
    '"action":"dung|chi_tay|vay_tay|suy_nghi|bat_ngo|vui_mung|buon|run_so|di_bo","expression":"vui|soc|buon|gian|nghi|",'
    '"background":"(tuỳ chọn)","prop":"(cầm trên tay, tuỳ chọn)","item":"(đồ vật hiện to giữa màn hình, tuỳ chọn)",'
    '"price":"(thẻ giá, tuỳ chọn)","options":["(trắc nghiệm, cho quiz_q)"],"answer":0,"picked":0,'
    '"sfx":"dung|sai|pop|whoosh|tick (tuỳ chọn)","compare":[],"anatomy":{},"pron":{},"breakdown":{},'
    '"typing":"me|other (tuỳ chọn)"}'
)

STYLE_PROMPT = """Bạn viết kịch bản video short 40-50 giây dạy {lang_vi} cho người Việt.
PHONG CÁCH: {style_name}. {rules}
Chủ đề: "{topic}". Trình độ: {level}. Nhân vật: A = {cast_a}, B = {cast_b}; N = người dẫn (chỉ có giọng).
Quy tắc chung:
- 10-14 lượt. VÀO THẲNG NỘI DUNG: lượt 1 là HOOK tiếng Việt <= 10 từ (ví dụ: "{hook_idea}"), KHÔNG chào hỏi,
  KHÔNG giới thiệu bản thân/kênh, KHÔNG "hôm nay chúng ta sẽ học". Lượt 2 đã phải dạy câu/từ đầu tiên.
- Lời Việt ngắn 5-16 từ, tự nhiên, vui. Câu {lang_vi} CHÍNH XÁC, tự nhiên, <= 10 từ. KHÔNG tự phiên âm.
- background chọn trong: {bgs}. prop chọn trong: {props}.
- Lượt cuối: 1 câu kêu gọi NGẮN <= 8 từ (VD "Bạn được mấy điểm? Bình luận nhé!"), không cảm ơn/tạm biệt dài dòng.
Mỗi lượt theo mẫu: {schema}
Chỉ trả JSON: {{"title":"tiêu đề tiếng Việt <= 60 ký tự","description":"...","background":"...",
"previously":"(chỉ phim bộ)","next":"(chỉ phim bộ)","turns":[...]}}"""

# 10 ĐỊNH DẠNG THU HÚT NHẤT (chọn chung cho short & video dài) → phong cách tương ứng
FORMATS10 = [
    ("giao_tiep", "1. 🛒 Tình huống đời thường có cảnh & đồ vật"),
    ("chat", "2. 📱 Tin nhắn KakaoTalk / WeChat / iMessage"),
    ("do_vui", "3. 🏆 Đố vui trắc nghiệm A/B/C (đếm ngược + tính điểm)"),
    ("top_sai", "4. ❌ Top lỗi sai – sửa đúng"),
    ("so_sanh_3", "5. 🌏 1 câu – 3 ngôn ngữ"),
    ("mo_xe_chu", "6. 🔤 Mổ xẻ chữ (bộ thủ / Hán-Việt / gốc từ)"),
    ("phat_am", "7. 🎤 Phát âm: thanh điệu & khẩu hình"),
    ("cau_thoai", "8. 🎬 Học qua câu thoại phim / bài hát"),
    ("phim_bo", "9. 🎭 Phim bộ nhiều tập"),
    ("thu_thach", "10. 📅 Thử thách 30 ngày"),
]
