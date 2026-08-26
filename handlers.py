# -*- coding: utf-8 -*-
"""
معالجة الرسائل: الأوامر (عربي و/)، الأزرار التفاعلية، الصور، والأعضاء الجدد.
"""
import time
import re
import random
import datetime
import threading

import db
import persona
import time_utils
import model_registry
import youtube_service
import pdf_export
import image_search_client
import backup_export
import tournament
import bracket_image
import hunter_system
import hunter_card
import handlers_hunter
import anime_draft
import draft_card_image
from config import (
    MASTER_ADMIN_ID, MASTER_ADMIN_IDS, AI_COOLDOWN_SECONDS,
    VOICE_GEN_COOLDOWN_SECONDS, TAGALL_COOLDOWN_SECONDS,
    REQUIRE_OWNER_PRESENCE, OWNER_PRESENCE_CACHE_MINUTES,
    GROUP_RULES_TEXT, MAX_WARNINGS_BEFORE_KICK, BACKUP_INTERVAL_DAYS, PERSONA_NAME,
    YT_SERVICE_URL,
)
from telegram_client import (
    send_message, send_photo, send_video, send_poll, send_document, edit_message_text,
    delete_message, send_chat_action, answer_callback_query, get_file_path, download_file_bytes,
    get_chat_member_status, restrict_chat_member, ban_chat_member, unban_chat_member,
    pin_chat_message, unpin_chat_message, set_chat_title, set_chat_lock, set_chat_photo,
    delete_messages_batch, send_document_bytes, send_dice, send_photo_bytes, send_audio_bytes,
    leave_chat, get_chat, get_chat_member_count, promote_chat_member, create_chat_invite_link,
    get_me,
)

# ----------------------------------------------------------------
# لعبة "خمن مين قالها" — شخصية أنمي + مقولة مختصرة معروفة عنها (بصياغتنا الخاصة).
# لو المالك حافظ صورة بالمكتبة المحفوظة بنفس اسم الشخصية بالضبط (احفظ باسم <الاسم>)،
# راح تنعرض قبل السؤال تلقائياً.
# ----------------------------------------------------------------
QUOTE_GAME_DATA = [
    {"character": "ايتاشي أوتشيها", "anime": "ناروتو",
     "quote": "الإنسان يصير قوي فعلاً بس لما يكون عنده شيء يحميه"},
    {"character": "اوبيتو أوتشيها", "anime": "ناروتو",
     "quote": "اللي يخالف القوانين يعتبر نذل، بس اللي يتخلى عن رفاقه أسوأ من نذل"},
    {"character": "مادارا أوتشيها", "anime": "ناروتو",
     "quote": "الحلم يضل حلم إلى أن تسوي منه حقيقة بإيدك"},
    {"character": "ناروتو أوزوماكي", "anime": "ناروتو",
     "quote": "أنا ما أرجع بكلامي أبداً، هذا هو طريقي بالنينجا"},
    {"character": "كاكاشي هاتاكي", "anime": "ناروتو",
     "quote": "اللي ما يقدّر رفاقه بالفريق أحقر من القمامة"},
    {"character": "جيرايا", "anime": "ناروتو",
     "quote": "طالما فيه ناس تتذكرك، انت أبداً ما تنموت بصورة كاملة"},
    {"character": "جارا", "anime": "ناروتو",
     "quote": "الحب الحقيقي هو اللي يخليك تحمي غيرك حتى على حساب نفسك"},
    {"character": "مونكي دي لوفي", "anime": "ون بيس",
     "quote": "لو ما جازفت بحياتك، ما تقدر تغيّر أي شي بهالعالم"},
    {"character": "رورونوا زورو", "anime": "ون بيس",
     "quote": "لو انهزمت وانا حامي رفاقي، هذا مو فشل، هذا شرف"},
    {"character": "بورتغاس دي ايس", "anime": "ون بيس",
     "quote": "ما ندمت ولا لحظة إني وُلدت بهالعالم"},
    {"character": "شانكس", "anime": "ون بيس",
     "quote": "لو تبي تعيش حياتك بلا ندم، عيشها بأقصى ما تقدر"},
    {"character": "ايرين ييغر", "anime": "هجوم العمالقة",
     "quote": "لو ما تقاتل، ما تقدر تنتصر"},
    {"character": "ليفاي أكرمان", "anime": "هجوم العمالقة",
     "quote": "الاختيار الصح دايماً يجيب معاه ندم على الاختيار الثاني"},
    {"character": "ال (لولايت)", "anime": "دفتر الموت",
     "quote": "أنا العدالة، وبعيد الكتابة بهالدفتر أطهّر هالعالم من الأشرار"},
    {"character": "ريوك", "anime": "دفتر الموت",
     "quote": "البشر مخلوقات مسلّية جداً، أضمن لك المتعة"},
    {"character": "ايزوكو ميدوريا", "anime": "أكاديمية الأبطال",
     "quote": "حتى لو مو معي قوة خارقة، بضل أتحرك للأمام"},
    {"character": "الأول أول مايت", "anime": "أكاديمية الأبطال",
     "quote": "تقدر تصير بطل! جملة بسيطة بس تغيّر مصير ناس"},
    {"character": "تانجيرو كامادو", "anime": "قاتل الشياطين",
     "quote": "مهما صار، ما بترك أختي وبضل أحاول أنقذها"},
    {"character": "زينيتسو اغاتسوما", "anime": "قاتل الشياطين",
     "quote": "لما أخاف كثير، جسمي يتحرك بقوة أكبر من العادي"},
    {"character": "سون غوكو", "anime": "دراغون بول",
     "quote": "كل معركة أخسرها تخليني أقوى من قبل"},
    {"character": "فيجيتا", "anime": "دراغون بول",
     "quote": "أنا أمير السايان، وما أقبل بأقل من القمة"},
    {"character": "ايدوارد إلريك", "anime": "الخيميائي المعدني الكامل",
     "quote": "عشان تحصل على شي، لازم تضحي بشي يعادله بالقيمة"},
    {"character": "ايتشيغو كوروساكي", "anime": "بليتش",
     "quote": "القوة الحقيقية هي اللي تخليك تحمي اللي تحبهم"},
    {"character": "غون فريكس", "anime": "هنتر × هنتر",
     "quote": "بلاقي أبوي مهما كلفني الأمر، هذا وعدي لنفسي"},
]


def _get_quote_pool():
    """يرجع كل الاقتباسات: الثابتة بالكود + اللي أضافها المالك الأصلي من قاعدة البيانات."""
    added = [{"character": r["character"], "anime": r["anime"], "quote": r["quote"]}
             for r in db.list_quote_entries()]
    return QUOTE_GAME_DATA + added


def _pick_quote_question():
    pool = _get_quote_pool()
    correct = random.choice(pool)
    others = [q for q in pool if q["character"] != correct["character"]]
    decoys = random.sample(others, min(2, len(others)))
    options = [correct["quote"]] + [d["quote"] for d in decoys]
    random.shuffle(options)
    correct_index = options.index(correct["quote"])
    return correct, options, correct_index

# ----------------------------------------------------------------
# نظام تفعيل/تعطيل الميزات — المالك (MASTER_ADMIN_IDS) فقط يقدر يتحكم فيه
# ----------------------------------------------------------------
FEATURE_LABELS = {
    "trivia": "🎮 الألعاب (مسابقة معلومات / تخمين الرقم / صراحة وتحدي)",
    "story": "📖 نظام القصة (فصول/تصدير/ملخص...)",
    "suggestions": "💡 الاقتراحات والتصويت",
    "characters": "🧑 الشخصيات",
    "stats": "🏆 الترتيب والإحصائيات",
    "persona_chat": "💬 محادثة سيزار (رد + وصف صور + صوت)",
    "moderation": "🛡️ أوامر الإدارة (كتم/طرد/حظر/تثبيت...)",
    "settings": "⚙️ إعدادات المجموعة (الأصوات/نسيان المحادثة)",
    "admin_mgmt": "👑 إدارة صلاحيات الأدمن",
    "broadcast": "📢 الإذاعة",
    "diagnostics": "🔍 أدوات التشخيص",
    "media_library": "🎞️ مكتبة الصور والفيديوهات المحفوظة",
    "tag_all": "📣 مناداة الكل (طاق)",
    "quote_game": "🎭 لعبة خمن مين قالها (اقتباسات الأنمي)",
    "character_photo_game": "🖼️ لعبة خمن الشخصية من الصورة",
    "tictactoe_game": "❌⭕ لعبة إكس-أو",
    "connect4_game": "🔴🟡 لعبة أربعة متتالية",
    "othello_game": "⚫⚪ لعبة أوثيلو (ريفيرسي)",
    "memory_game": "🧠 لعبة الذاكرة (Memory Match)",
    "wheel_game": "🎡 عجلة الأسماء",
    "duel_vote_game": "⚔️ منافسة التصويت (مين الأحسن)",
    "tournament_game": "🏆 نظام البطولات",
    "activity_stats": "📊 الأكثر تفاعلاً",
    "nickname": "🏷️ الكنية",
    "image_search": "🖼️ جلب صورة حقيقية بالإنترنت",
}

# يربط كل أمر بميزة قابلة للتعطيل. أي أمر غير موجود هنا (مثل /start أو /features
# نفسها) يبقى شغّالاً دائماً عشان المالك ما يقفل نفسه بالخطأ.
CMD_FEATURE_MAP = {
    "/story": "story", "/lastchapter": "story", "/newarc": "story", "/export": "story",
    "/exportpdf": "story", "/search": "story", "/summary": "story", "/ideas": "story",
    "/rate": "story", "/challenge": "story", "/addchapterdirect": "story", "/editchapter": "story",
    "/deletechapter": "story", "/undolastchapter": "story",
    "/suggest": "suggestions", "/suggestions": "suggestions", "/pollvote": "suggestions",
    "/approvesuggestion": "suggestions", "/rejectsuggestion": "suggestions",
    "/editsuggestion": "suggestions", "/cancel": "suggestions", "/improve": "suggestions",
    "/addcharacter": "characters", "/editcharacter": "characters", "/deletecharacter": "characters",
    "/mycharacter": "characters", "/characters": "characters",
    "/leaderboard": "stats", "/mystats": "stats",
    "/trivia": "trivia", "/trivialeaderboard": "trivia", "/games": "trivia",
    "/guessnumber": "trivia", "/truthdare": "trivia", "/endgame": "trivia",
    "/tictactoe": "tictactoe_game",
    "/connect4": "connect4_game",
    "/othello": "othello_game",
    "/memory": "memory_game",
    "/wheel": "wheel_game",
    "/duel": "duel_vote_game",
    "/tournament": "tournament_game", "/canceltournament": "tournament_game",
    "/mute": "moderation", "/unmute": "moderation", "/kick": "moderation", "/ban": "moderation",
    "/unban": "moderation", "/pin": "moderation", "/unpin": "moderation", "/delmsg": "moderation",
    "/clearall": "moderation", "/setgrouptitle": "moderation", "/setgroupphoto": "moderation",
    "/lockchat": "moderation", "/unlockchat": "moderation", "/tag": "moderation",
    "/warn": "moderation", "/unwarn": "moderation",
    "/resetwarnings": "moderation", "/warnings": "moderation", "/warninglist": "moderation",
    "/tagall": "tag_all",
    "/quotegame": "quote_game", "/quotecharacters": "quote_game",
    "/addquote": "quote_game", "/deletequote": "quote_game",
    "/guesscharacterphoto": "character_photo_game", "/characterphotolist": "character_photo_game",
    "/deletecharacterphoto": "character_photo_game", "/renamecharacterphoto": "character_photo_game",
    "/addcharacterphoto": "character_photo_game",
    "/setautovotes": "settings", "/forgetchat": "settings",
    "/makeadmin": "admin_mgmt", "/addadmin": "admin_mgmt", "/removeadmin": "admin_mgmt",
    "/requestremoveadmin": "admin_mgmt",
    "/myrank": "admin_mgmt", "/adminlist": "admin_mgmt", "/rankpermissions": "admin_mgmt",
    "/broadcast": "broadcast",
    "/aitest": "diagnostics", "/checkenv": "diagnostics",
    "/medialist": "media_library", "/deletemedia": "media_library",
    "/active": "activity_stats",
    "/nickname": "nickname", "/removenickname": "nickname",
    "/genimage": "image_search",
}


def _feature_blocked_message(chat_id, feature_key):
    label = FEATURE_LABELS.get(feature_key, feature_key)
    send_message(chat_id, f"🚫 ميزة «{label}» معطّلة حالياً من قبل مالك البوت.")

# تبريد بسيط داخل الذاكرة لكل مستخدم لطلبات الذكاء الاصطناعي (يمنع الإغراق المتكرر)
_last_ai_request = {}


def _cooldown_ok(user_id):
    now = time.time()
    last = _last_ai_request.get(user_id, 0)
    if now - last < AI_COOLDOWN_SECONDS:
        return False
    _last_ai_request[user_id] = now
    return True


_last_voice_request = {}


def _voice_cooldown_ok(user_id):
    now = time.time()
    last = _last_voice_request.get(user_id, 0)
    if now - last < VOICE_GEN_COOLDOWN_SECONDS:
        return False
    _last_voice_request[user_id] = now
    return True


_last_tagall_request = {}


def _tagall_cooldown_ok(chat_id):
    now = time.time()
    last = _last_tagall_request.get(chat_id, 0)
    if now - last < TAGALL_COOLDOWN_SECONDS:
        return False
    _last_tagall_request[chat_id] = now
    return True


# ----------------------------------------------------------------
# تتبع رسائل الألعاب (لحذفها دفعة وحدة بأمر "انهاء اللعب")
# ----------------------------------------------------------------
GAME_MSG_IDS = {}  # chat_id -> [message_id, ...]


def _track_game_msg(chat_id, message_id):
    if message_id:
        GAME_MSG_IDS.setdefault(chat_id, []).append(message_id)


def end_active_games(chat_id):
    """ينهي أي لعبة نشطة بالمجموعة (تخمين رقم / صراحة وتحدي / خمن الشخصية / إكس-أو / أربعة متتالية /
    أوثيلو / الذاكرة / عجلة الأسماء / منافسة تصويت / بطولة) ويمسح رسائلها. يرجع عدد الرسائل المحذوفة."""
    had_game = (chat_id in GUESS_GAMES or chat_id in TRUTHDARE_PENDING or chat_id in CHAR_GUESS_GAMES
                or chat_id in TICTACTOE_GAMES or chat_id in CONNECT4_GAMES or chat_id in OTHELLO_GAMES
                or chat_id in MEMORY_GAMES or chat_id in DRAFT_GAMES
                or chat_id in WHEEL_GAMES or chat_id in DUEL_VOTES or chat_id in TOURNAMENTS)
    GUESS_GAMES.pop(chat_id, None)
    TRUTHDARE_PENDING.pop(chat_id, None)
    CHAR_GUESS_GAMES.pop(chat_id, None)
    TICTACTOE_GAMES.pop(chat_id, None)
    CONNECT4_GAMES.pop(chat_id, None)
    OTHELLO_GAMES.pop(chat_id, None)
    MEMORY_GAMES.pop(chat_id, None)
    DRAFT_GAMES.pop(chat_id, None)
    WHEEL_GAMES.pop(chat_id, None)
    DUEL_VOTES.pop(chat_id, None)
    TOURNAMENTS.pop(chat_id, None)
    ids = GAME_MSG_IDS.pop(chat_id, [])
    if ids:
        delete_messages_batch(chat_id, ids)
    return len(ids), had_game or bool(ids)


# ----------------------------------------------------------------
# 🏆 نظام البطولات — تسجيل مفتوح لكل الأعضاء بزر "انضم"، شجرة إقصاء تلقائية
# (bracket) تدعم أي عدد مشاركين، اختيار الأدمن للعبة (إكس-أو / أربعة متتالية /
# مبارزة حظ) أو "عشوائي" لكل مباراة، ونقاط تُضاف للترتيب العام لكل فوز + مكافأة
# للبطل. المنطق الخالص (الشجرة والمباريات) بملف tournament.py.
# ----------------------------------------------------------------
TOURNAMENTS = {}  # chat_id -> {"stage", "max_players", "game_mode", "players": [(id,name)],
                   #             "created_by", "reg_message_id", "bracket", "active_match"}


def _tournament_size_keyboard():
    row = [(f"👥 {n}", f"trnsize_{n}") for n in tournament.TOURNAMENT_SIZE_OPTIONS]
    return inline_keyboard([row, [("❌ إلغاء", "trncancel")]])


def _tournament_game_keyboard():
    return inline_keyboard([
        [("❌⭕ إكس-أو", "trngame_xo")],
        [("🔴🟡 أربعة متتالية", "trngame_c4")],
        [("🎲 مبارزة حظ (سريعة)", "trngame_dice")],
        [("🎰 عشوائي كل مباراة", "trngame_random")],
        [("❌ إلغاء", "trncancel")],
    ])


def _tournament_reg_text(t):
    label = tournament.MATCH_GAME_LABELS.get(t["game_mode"], "🎰 عشوائي كل مباراة")
    lines = [f"🏆 بطولة جديدة — {label}",
             f"الحد الأقصى: {t['max_players']} لاعب",
             f"\nالمسجلين ({len(t['players'])}/{t['max_players']}):"]
    if t["players"]:
        lines.extend(f"  {i}. {name}" for i, (_, name) in enumerate(t["players"], 1))
    else:
        lines.append("  (لسا محد انضم)")
    lines.append("\n🙋 اضغط «انضم» للمشاركة. الأدمن يقدر يبدأ بأي وقت بعد أول عضوين.")
    return "\n".join(lines)


def _tournament_reg_keyboard():
    return inline_keyboard([
        [("🙋 انضم", "trnjoin")],
        [("▶️ ابدأ الآن", "trnstart"), ("❌ إلغاء البطولة", "trncancel")],
    ])


def _tournament_bracket_title(t):
    mode = t.get("game_mode")
    if mode == "random":
        return "بطولة (لعبة عشوائية كل مباراة)"
    return f"بطولة {tournament.MATCH_GAME_TITLES.get(mode, '')}".strip()


def _tournament_send_bracket_photo(chat_id, subtitle=None, caption="🏆 شجرة البطولة الحيّة"):
    """يرسل صورة احترافية محدَّثة لشجرة البطولة (تحذف صورة الشجرة السابقة قبلها
    عشان ما تتكدس رسائل بالمجموعة). لو توليد الصورة تعذّر (Pillow أو خط Amiri
    غير مثبّتين على الاستضافة)، يرجع تلقائياً لعرض نصي بسيط بدون ما يتعطل،
    وينبّه الأدمن بالسبب مرة وحدة بس بكل بطولة."""
    t = TOURNAMENTS.get(chat_id)
    if not t:
        return
    ok, result = bracket_image.render_bracket_image(t["bracket"], title=_tournament_bracket_title(t),
                                                      subtitle=subtitle)
    old_id = t.get("bracket_photo_msg_id")
    if ok:
        if old_id:
            delete_message(chat_id, old_id)
        mid = send_photo_bytes(chat_id, result, "bracket.png", caption=caption)
        if mid:
            t["bracket_photo_msg_id"] = mid
            _track_game_msg(chat_id, mid)
        return

    if not t.get("_img_warned"):
        t["_img_warned"] = True
        send_message(chat_id, f"⚠️ ملاحظة للأدمن: تعذّر توليد صورة شجرة البطولة، فبنعرضها كنص مؤقتاً.\n{result}")
    mid = send_message(chat_id, f"{caption}\n" + tournament.render_bracket(t["bracket"]))
    _track_game_msg(chat_id, mid)


def _tournament_start_setup(chat_id, user_id):
    TOURNAMENTS[chat_id] = {"stage": "size", "created_by": user_id}
    mid = send_message(chat_id, "🏆 بطولة جديدة!\nكم أقصى عدد مشاركين؟", reply_markup=_tournament_size_keyboard())
    _track_game_msg(chat_id, mid)


def _tournament_match_text(t):
    p1_name = t["_active_p1_name"]
    p2_name = t["_active_p2_name"]
    game_key = t["active_match"]["game"]
    return f"🏆 {tournament.MATCH_GAME_LABELS[game_key]}\n{p1_name} 🆚 {p2_name}"


def _tournament_announce_next_match(chat_id):
    t = TOURNAMENTS.get(chat_id)
    if not t:
        return
    found = tournament.find_next_pending_match(t["bracket"])
    if not found:
        champ = tournament.champion(t["bracket"])
        if champ:
            _tournament_finish(chat_id)
            return
        if tournament.build_next_round(t["bracket"]):
            champ2 = tournament.settle_byes(t["bracket"])
            if champ2:
                _tournament_finish(chat_id)
                return
            _tournament_announce_next_match(chat_id)
        return

    ri, mi, match = found
    game_key = tournament.pick_match_game(t["game_mode"])
    match["game"] = game_key
    t["active_match"] = {"round": ri, "index": mi, "game": game_key}
    t["_active_p1_name"] = match["p1"][1]
    t["_active_p2_name"] = match["p2"][1]

    if game_key == "dice":
        t["active_match"]["state"] = {"p1_roll": None, "p2_roll": None}
        kb = inline_keyboard([[(f"🎲 رمي {match['p1'][1]}", "trndice_p1"),
                                (f"🎲 رمي {match['p2'][1]}", "trndice_p2")]])
        mid = send_message(chat_id, _tournament_match_text(t) + "\n\nكل لاعب يضغط زر رميته الخاص 👇",
                            reply_markup=kb)
    elif game_key == "xo":
        t["active_match"]["state"] = tournament.new_xo_state()
        kb = inline_keyboard(tournament.xo_keyboard_rows(t["active_match"]["state"]["board"], "trnxo_"))
        mid = send_message(chat_id, _tournament_match_text(t) + f"\n\nدور: {match['p1'][1]} ❌", reply_markup=kb)
    else:  # c4
        t["active_match"]["state"] = tournament.new_c4_state()
        board = t["active_match"]["state"]["board"]
        kb = inline_keyboard(tournament.c4_keyboard_row("trnc4_"))
        mid = send_message(chat_id, _tournament_match_text(t) + f"\n\n{tournament.c4_render_text(board)}\n\n"
                            f"دور: {match['p1'][1]} 🔴", reply_markup=kb)

    t["active_match"]["message_id"] = mid
    _track_game_msg(chat_id, mid)


def _tournament_match_won(chat_id, winner):
    t = TOURNAMENTS.get(chat_id)
    if not t:
        return
    ri, mi = t["active_match"]["round"], t["active_match"]["index"]
    t["bracket"][ri][mi]["winner"] = winner
    db.add_trivia_score(chat_id, winner[0], winner[1], 5)
    t["active_match"] = None
    _tournament_send_bracket_photo(chat_id, subtitle=f"فاز {winner[1]} بالجولة الأخيرة",
                                    caption=f"🏆 فاز {winner[1]}! (+5 نقاط) — شجرة البطولة محدَّثة")
    _tournament_announce_next_match(chat_id)


def _tournament_finish(chat_id):
    t = TOURNAMENTS.pop(chat_id, None)
    if not t:
        return
    champ = tournament.champion(t["bracket"])
    caption = "🏆🎉 انتهت البطولة!"
    if champ:
        db.add_trivia_score(chat_id, champ[0], champ[1], 25)
        caption += f"\n👑 مبروك للبطل: {champ[1]}! (+25 نقطة إضافية بالترتيب العام)"

    ok, result = bracket_image.render_bracket_image(t["bracket"], title=_tournament_bracket_title(t),
                                                      subtitle="النتيجة النهائية")
    old_id = t.get("bracket_photo_msg_id")
    if ok:
        if old_id:
            delete_message(chat_id, old_id)
        mid = send_photo_bytes(chat_id, result, "bracket_final.png", caption=caption)
    else:
        mid = send_message(chat_id, caption + "\n\n" + tournament.render_bracket(t["bracket"]))
    _track_game_msg(chat_id, mid)


def _tournament_launch(chat_id):
    t = TOURNAMENTS.get(chat_id)
    if not t or len(t["players"]) < 2:
        return
    t["stage"] = "running"
    t["bracket"] = tournament.build_bracket(t["players"])
    champ = tournament.settle_byes(t["bracket"])
    _tournament_send_bracket_photo(chat_id, subtitle="بدأت البطولة!", caption="▶️ بدأت البطولة! شجرة الإقصاء الكاملة:")
    if champ:
        _tournament_finish(chat_id)
    else:
        _tournament_announce_next_match(chat_id)


def _handle_tournament_callback(data, chat_id, user_id, user_name, cq):
    """يعالج كل أزرار نظام البطولة (بادئة trn): الإعداد، التسجيل، وكل أنواع المباريات."""
    cq_id = cq["id"]
    message_id = cq["message"]["message_id"]
    t = TOURNAMENTS.get(chat_id)

    if data.startswith("trnsize_"):
        if not t or t.get("stage") != "size":
            answer_callback_query(cq_id, "🚫 ما فيه إعداد بطولة نشط.", show_alert=True)
            return
        if user_id != t["created_by"]:
            answer_callback_query(cq_id, "بس اللي بدأ إعداد البطولة يكمّل إعدادها.", show_alert=True)
            return
        t["max_players"] = int(data[len("trnsize_"):])
        t["stage"] = "game"
        answer_callback_query(cq_id)
        edit_message_text(chat_id, message_id, "🏆 اختر نوع اللعبة للبطولة:", reply_markup=_tournament_game_keyboard())
        return

    if data.startswith("trngame_"):
        if not t or t.get("stage") != "game":
            answer_callback_query(cq_id, "🚫 ما فيه إعداد بطولة نشط.", show_alert=True)
            return
        if user_id != t["created_by"]:
            answer_callback_query(cq_id, "بس اللي بدأ إعداد البطولة يكمّل إعدادها.", show_alert=True)
            return
        t["game_mode"] = data[len("trngame_"):]
        t["stage"] = "registration"
        t["players"] = []
        t["reg_message_id"] = message_id
        answer_callback_query(cq_id)
        edit_message_text(chat_id, message_id, _tournament_reg_text(t), reply_markup=_tournament_reg_keyboard())
        return

    if data == "trnjoin":
        if not t or t.get("stage") != "registration":
            answer_callback_query(cq_id, "🚫 ما فيه بطولة تسجّل حالياً.", show_alert=True)
            return
        if any(pid == user_id for pid, _ in t["players"]):
            answer_callback_query(cq_id, "✅ انت مسجّل بالفعل!")
            return
        if len(t["players"]) >= t["max_players"]:
            answer_callback_query(cq_id, "🚫 اكتمل عدد المشاركين.", show_alert=True)
            return
        t["players"].append((user_id, user_name))
        full = len(t["players"]) >= t["max_players"]
        answer_callback_query(cq_id, "🙋 تم تسجيلك بالبطولة!")
        edit_message_text(chat_id, message_id, _tournament_reg_text(t), reply_markup=_tournament_reg_keyboard())
        if full:
            _tournament_launch(chat_id)
        return

    if data == "trnstart":
        if not t or t.get("stage") != "registration":
            answer_callback_query(cq_id, "🚫 ما فيه بطولة تسجّل حالياً.", show_alert=True)
            return
        if user_id != t["created_by"] and not is_admin(chat_id, user_id):
            answer_callback_query(cq_id, "بدء البطولة للأدمن فقط.", show_alert=True)
            return
        if len(t["players"]) < 2:
            answer_callback_query(cq_id, "🚫 لازم عضوين على الأقل قبل البدء.", show_alert=True)
            return
        answer_callback_query(cq_id)
        _tournament_launch(chat_id)
        return

    if data == "trncancel":
        if not t:
            answer_callback_query(cq_id)
            return
        if user_id != t["created_by"] and not is_admin(chat_id, user_id):
            answer_callback_query(cq_id, "إلغاء البطولة للأدمن فقط.", show_alert=True)
            return
        TOURNAMENTS.pop(chat_id, None)
        answer_callback_query(cq_id, "❌ تم إلغاء البطولة.")
        edit_message_text(chat_id, message_id, "❌ أُلغيت البطولة.")
        return

    # ---- من هنا: أزرار مباراة نشطة فعلياً (نرد / إكس-أو / أربعة متتالية) ----
    if not t or t.get("stage") != "running" or not t.get("active_match"):
        answer_callback_query(cq_id, "🚫 ما فيه مباراة بطولة نشطة حالياً.", show_alert=True)
        return

    active = t["active_match"]
    match = t["bracket"][active["round"]][active["index"]]
    p1_id, p1_name = match["p1"]
    p2_id, p2_name = match["p2"]

    if user_id not in (p1_id, p2_id):
        answer_callback_query(cq_id, "🚫 هذي المباراة بين لاعبين محددين بالبطولة، مو لك.", show_alert=True)
        return
    side = "p1" if user_id == p1_id else "p2"

    if data.startswith("trndice_"):
        if data[len("trndice_"):] != side:
            answer_callback_query(cq_id, "🚫 هذا زر رمي الطرف الثاني، اضغط زرك انت.", show_alert=True)
            return
        state = active["state"]
        key = f"{side}_roll"
        if state[key] is not None:
            answer_callback_query(cq_id, "🚫 رميت بالفعل، بانتظار الطرف الثاني.", show_alert=True)
            return
        answer_callback_query(cq_id, "🎲 رميت النرد!")
        state[key] = send_dice(chat_id) or random.randint(1, 6)
        dice_kb = inline_keyboard([[(f"🎲 رمي {p1_name}", "trndice_p1"), (f"🎲 رمي {p2_name}", "trndice_p2")]])
        if state["p1_roll"] is None or state["p2_roll"] is None:
            waiting = p2_name if side == "p1" else p1_name
            edit_message_text(chat_id, active["message_id"],
                               _tournament_match_text(t) + f"\n\nبانتظار رمي {waiting}...", reply_markup=dice_kb)
        elif state["p1_roll"] == state["p2_roll"]:
            state["p1_roll"] = state["p2_roll"] = None
            edit_message_text(chat_id, active["message_id"],
                               _tournament_match_text(t) + "\n\n🎲 تعادل بالنرد! أعيدوا الرمي.",
                               reply_markup=dice_kb)
        else:
            winner = match["p1"] if state["p1_roll"] > state["p2_roll"] else match["p2"]
            edit_message_text(chat_id, active["message_id"],
                               _tournament_match_text(t) +
                               f"\n\n🎲 {p1_name}: {state['p1_roll']} — {p2_name}: {state['p2_roll']}\n"
                               f"🎉 فاز {winner[1]}! +5 نقاط")
            _tournament_match_won(chat_id, winner)
        return

    if data.startswith("trnxo_"):
        cell = int(data[len("trnxo_"):])
        state = active["state"]
        if state["turn"] != side:
            answer_callback_query(cq_id, "⏳ مو دورك.", show_alert=True)
            return
        if state["board"][cell]:
            answer_callback_query(cq_id, "🚫 هذا المربع مشغول.", show_alert=True)
            return
        state["board"][cell] = side
        answer_callback_query(cq_id)
        result = tournament.xo_winner(state["board"])
        if result == "draw":
            active["state"] = tournament.new_xo_state()
            kb = inline_keyboard(tournament.xo_keyboard_rows(active["state"]["board"], "trnxo_"))
            edit_message_text(chat_id, active["message_id"],
                               _tournament_match_text(t) + f"\n\n🤝 تعادل، إعادة! دور: {p1_name} ❌",
                               reply_markup=kb)
        elif result in ("p1", "p2"):
            winner = match[result]
            kb = inline_keyboard(tournament.xo_keyboard_rows(state["board"], "trnxo_"))
            edit_message_text(chat_id, active["message_id"],
                               _tournament_match_text(t) +
                               f"\n\n🎉 فاز {winner[1]} ({tournament.xo_symbol(result)})! +5 نقاط", reply_markup=kb)
            _tournament_match_won(chat_id, winner)
        else:
            state["turn"] = "p2" if side == "p1" else "p1"
            next_name = p2_name if state["turn"] == "p2" else p1_name
            kb = inline_keyboard(tournament.xo_keyboard_rows(state["board"], "trnxo_"))
            edit_message_text(chat_id, active["message_id"],
                               _tournament_match_text(t) +
                               f"\n\nدور: {next_name} {tournament.xo_symbol(state['turn'])}", reply_markup=kb)
        return

    if data.startswith("trnc4_"):
        col = int(data[len("trnc4_"):])
        state = active["state"]
        if state["turn"] != side:
            answer_callback_query(cq_id, "⏳ مو دورك.", show_alert=True)
            return
        row = tournament.c4_drop(state["board"], col, side)
        if row is None:
            answer_callback_query(cq_id, "🚫 هذا العمود ممتلئ.", show_alert=True)
            return
        answer_callback_query(cq_id)
        result = tournament.c4_winner(state["board"], row, col)
        kb = inline_keyboard(tournament.c4_keyboard_row("trnc4_"))
        if result == "draw":
            active["state"] = tournament.new_c4_state()
            edit_message_text(chat_id, active["message_id"],
                               _tournament_match_text(t) +
                               f"\n\n{tournament.c4_render_text(active['state']['board'])}\n\n"
                               f"🤝 تعادل، إعادة! دور: {p1_name} 🔴", reply_markup=kb)
        elif result in ("p1", "p2"):
            winner = match[result]
            edit_message_text(chat_id, active["message_id"],
                               _tournament_match_text(t) + f"\n\n{tournament.c4_render_text(state['board'])}\n\n"
                               f"🎉 فاز {winner[1]}! +5 نقاط", reply_markup=kb)
            _tournament_match_won(chat_id, winner)
        else:
            state["turn"] = "p2" if side == "p1" else "p1"
            next_name = p2_name if state["turn"] == "p2" else p1_name
            edit_message_text(chat_id, active["message_id"],
                               _tournament_match_text(t) + f"\n\n{tournament.c4_render_text(state['board'])}\n\n"
                               f"دور: {next_name} {tournament.c4_symbol(state['turn'])}", reply_markup=kb)
        return

    answer_callback_query(cq_id)


# ----------------------------------------------------------------
# لعبة "تخمين الرقم" — أزرار بدل الكتابة (يختار العضو رقم من 1-20 مباشرة،
# وبيرد له خاص "أكبر/أصغر" برسالة منبثقة بدون ما يزعج المحادثة العامة)
# ----------------------------------------------------------------
GUESS_GAMES = {}  # chat_id -> {"number": int, "attempts": int, "message_id": int}
GUESS_RANGE = 20


def _guess_keypad():
    numbers = list(range(1, GUESS_RANGE + 1))
    rows = []
    for i in range(0, len(numbers), 5):
        rows.append([(str(n), f"gsn_{n}") for n in numbers[i:i + 5]])
    return inline_keyboard(rows)


def start_guess_game(chat_id):
    number = random.randint(1, GUESS_RANGE)
    message_id = send_message(
        chat_id,
        f"🔢 اخترت رقم سري من 1 إلى {GUESS_RANGE}!\nاضغطوا على رقمكم بالأسفل 👇",
        reply_markup=_guess_keypad(),
    )
    GUESS_GAMES[chat_id] = {"number": number, "attempts": 0, "message_id": message_id}
    _track_game_msg(chat_id, message_id)


def is_guess_game_active(chat_id):
    return chat_id in GUESS_GAMES


def handle_guess_button(chat_id, cq_id, user_id, user_name, guess, message_id):
    game = GUESS_GAMES.get(chat_id)
    if not game:
        answer_callback_query(cq_id, text="🚫 ما فيه لعبة تخمين نشطة حالياً. اكتب «خمن الرقم» لبدء واحدة.",
                               show_alert=True)
        return

    game["attempts"] += 1
    if guess == game["number"]:
        del GUESS_GAMES[chat_id]
        answer_callback_query(cq_id, text="🎉 صح! أنت الفايز")
        edit_message_text(chat_id, message_id,
                           f"🎉 {user_name} خمّن الرقم الصحيح ({guess}) بعد {game['attempts']} محاولة جماعية 👏")
    elif guess < game["number"]:
        answer_callback_query(cq_id, text="⬆️ أكبر من كذا")
    else:
        answer_callback_query(cq_id, text="⬇️ أصغر من كذا")


# ----------------------------------------------------------------
# لعبة "صراحة أو تحدي" — قوائم ثابتة (خفيفة، بدون استدعاء ذكاء اصطناعي)
# ----------------------------------------------------------------
TRUTH_QUESTIONS = [
    "شنو أكثر شي تندم عليه بحياتك؟",
    "شنو أغرب حلم شفته؟",
    "لو تقدر تغيّر شي بشخصيتك، شنو بيكون؟",
    "شنو أكثر كذبة قلتها وما انكشفت؟",
    "مين أكثر شخص أثّر بحياتك؟",
    "شنو أكثر خوف تسويه بصمت؟",
    "لو تربح مبلغ كبير فجأة، أول شي تسويه؟",
    "شنو أكثر موقف محرج صار لك؟",
    "شنو الشي اللي تتمناه بس ما جربته؟",
    "مين أكثر شخص بالمجموعة تحس إنك تفهمه زين؟",
]

DARE_TASKS = [
    "اكتب جملة معقدة بدون ما تستخدم حرف الألف 😄",
    "أرسل أغرب إيموجي عندك بدون تفسير",
    "اكتب مدح لأول شخص يرد عليك بالمجموعة",
    "غيّر اسمك بالمجموعة لمدة 5 دقايق لشي مضحك",
    "اكتب فصل القصة القادم بجملة واحدة بس",
    "قلّد أسلوب شخصية من القصة برسالة",
    "اكتب أغنية بكلمتين بس تعبّر عن مزاجك الحين",
    "أرسل نصيحة غريبة لكن مفيدة",
    "اكتب لغز بسيط وشوف مين يحله أول",
    "صف نفسك بثلاث كلمات بس",
]

# رد سريع لما حد يجاوب (يرد) على سؤال صراحة/تحدي — عشان الرد ما يضل معلّق بدون تفاعل
TRUTHDARE_REACTIONS = [
    "😄 إجابة حلوة يا {name}!",
    "🔥 يا سلام يا {name}، صراحة ما توقعتها!",
    "👏 تسلم يا {name}، إجابة عفوية!",
    "😂 {name} فضحنا نفسه بنفسه 😅",
    "✅ استلمنا إجابتك يا {name}، تسلم!",
]

TRUTHDARE_PENDING = {}  # chat_id -> {"message_id": int, "type": "truth"/"dare"}


def send_truth_or_dare(chat_id, kind):
    """kind: 'truth' أو 'dare'. يرسل السؤال/التحدي ويسجّله كمعلّق بانتظار رد."""
    if kind == "truth":
        text = f"🗣️ صراحة:\n{random.choice(TRUTH_QUESTIONS)}\n\n(ردّوا على هذي الرسالة بجوابكم 👇)"
    else:
        text = f"🎭 تحدي:\n{random.choice(DARE_TASKS)}\n\n(ردّوا على هذي الرسالة لما تسوّونه 👇)"
    message_id = send_message(chat_id, text)
    TRUTHDARE_PENDING[chat_id] = {"message_id": message_id, "type": kind}
    _track_game_msg(chat_id, message_id)


def react_to_truthdare_reply(chat_id, user_name, reply_to_message_id):
    """لو الرد كان على رسالة صراحة/تحدي المعلّقة، يرجع True ويرسل تفاعل قصير من سيزار."""
    pending = TRUTHDARE_PENDING.get(chat_id)
    if not pending or pending["message_id"] != reply_to_message_id:
        return False
    reaction = random.choice(TRUTHDARE_REACTIONS).format(name=user_name)
    message_id = send_message(chat_id, reaction)
    _track_game_msg(chat_id, message_id)
    return True


# ----------------------------------------------------------------
# لعبة "خمن الشخصية" — البوت يرسل صورة، الأعضاء يكتبون الاسم مباشرة
# (بدون خيارات جاهزة)، أول إجابة صحيحة تاخذ النقاط وتنهي الجولة،
# والإجابات الخاطئة يتم تجاهلها بصمت.
# ----------------------------------------------------------------
CHAR_GUESS_GAMES = {}  # chat_id -> {"name": str, "photo_id": int}


def _normalize_ar(text):
    text = (text or "").strip()
    text = re.sub(r"[\u064B-\u065F\u0670]", "", text)  # إزالة التشكيل
    text = re.sub(r"[إأآا]", "ا", text)
    text = text.replace("ى", "ي").replace("ة", "ه")
    text = re.sub(r"[،.!؟:]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()


def _is_correct_character_guess(guess_text, correct_name):
    g = _normalize_ar(guess_text)
    n = _normalize_ar(correct_name)
    if not g:
        return False
    if g == n:
        return True
    n_parts = n.split()
    if g in n_parts:
        return True
    if len(g) >= 3 and (g in n or n in g):
        return True
    return False


def is_character_guess_active(chat_id):
    return chat_id in CHAR_GUESS_GAMES


def _char_guess_skip_keyboard():
    return {"inline_keyboard": [[{"text": "⏭️ تخطي / التالي", "callback_data": "charskip"}]]}


def start_character_guess_game(chat_id, entry):
    photo_msg_id = send_photo(chat_id, entry["file_id"], caption="🖼️ وش اسم الشخصية؟ (اكتبوا الاسم مباشرة)",
                               reply_markup=_char_guess_skip_keyboard())
    _track_game_msg(chat_id, photo_msg_id)
    CHAR_GUESS_GAMES[chat_id] = {"name": entry["name"], "photo_id": entry["id"]}


def check_character_guess_answer(chat_id, user_id, user_name, text):
    """يتحقق هل الرسالة إجابة على جولة «خمن الشخصية» النشطة. يرجع True لو تعامل مع الرسالة."""
    game = CHAR_GUESS_GAMES.get(chat_id)
    if not game:
        return False
    if not _is_correct_character_guess(text, game["name"]):
        return False  # إجابة خاطئة — تجاهل بصمت
    del CHAR_GUESS_GAMES[chat_id]
    db.add_trivia_score(chat_id, user_id, user_name, 10)
    message_id = send_message(chat_id, f"✅ {user_name} جاوب صح! الشخصية كانت «{game['name']}» — +10 نقاط 🎉")
    _track_game_msg(chat_id, message_id)
    return True


# ----------------------------------------------------------------
# لعبة "إكس-أو" (Tic Tac Toe) — أول من يضغط لبدء اللعبة يصير X،
# وأول عضو مختلف يضغط أي مربع يصير O وتبدأ الجولة. تبادل أدوار حقيقي،
# فحص فوز/تعادل تلقائي، ولوحة تُحدَّث بنفس الرسالة (بدون رسائل جديدة).
# ----------------------------------------------------------------
TICTACTOE_GAMES = {}  # chat_id -> {"board": [None]*9, "players": {"X": (id,name), "O": (id,name)},
                       #             "turn": "X"/"O", "message_id": int}

TTT_WIN_LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),
    (0, 3, 6), (1, 4, 7), (2, 5, 8),
    (0, 4, 8), (2, 4, 6),
]


def _ttt_symbol(v):
    return {"X": "❌", "O": "⭕"}.get(v, " ")


def _ttt_keyboard(board):
    rows = []
    for r in range(3):
        row = []
        for c in range(3):
            i = r * 3 + c
            label = _ttt_symbol(board[i]) if board[i] else "‏"
            row.append((label, f"ttt_{i}"))
        rows.append(row)
    return inline_keyboard(rows)


def _ttt_winner(board):
    for a, b, c in TTT_WIN_LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    if all(board):
        return "draw"
    return None


def is_tictactoe_active(chat_id):
    return chat_id in TICTACTOE_GAMES


def start_tictactoe_game(chat_id, user_id, user_name):
    board = [None] * 9
    message_id = send_message(
        chat_id,
        f"❌⭕ إكس-أو بدأت!\n{user_name} يلعب ❌ (أول ضغطة).\nبانتظار عضو ثاني يضغط أي مربع ليصير ⭕...",
        reply_markup=_ttt_keyboard(board),
    )
    TICTACTOE_GAMES[chat_id] = {
        "board": board,
        "players": {"X": (user_id, user_name)},
        "turn": "X",
        "message_id": message_id,
    }
    _track_game_msg(chat_id, message_id)


def handle_tictactoe_button(chat_id, cq_id, user_id, user_name, cell, message_id):
    game = TICTACTOE_GAMES.get(chat_id)
    if not game:
        answer_callback_query(cq_id, text="🚫 ما فيه لعبة إكس-أو نشطة حالياً. اكتب «اكس او» لبدء واحدة.",
                               show_alert=True)
        return

    players = game["players"]

    # عضو ثاني ينضم كـ O أول ما يضغط (لازم يكون مختلف عن اللاعب الأول)
    if "O" not in players:
        if user_id == players["X"][0]:
            answer_callback_query(cq_id, text="🚫 لازم عضو ثاني غيرك يلعب ⭕ أول.", show_alert=True)
            return
        players["O"] = (user_id, user_name)

    symbol = "X" if players["X"][0] == user_id else ("O" if players.get("O", (None,))[0] == user_id else None)
    if symbol is None:
        answer_callback_query(cq_id, text="🚫 هذي الجولة بين لاعبين محددين، انتظر جولة جديدة.", show_alert=True)
        return

    if game["turn"] != symbol:
        answer_callback_query(cq_id, text="⏳ مو دورك، انتظر دور الطرف الثاني.", show_alert=True)
        return

    if game["board"][cell]:
        answer_callback_query(cq_id, text="🚫 هذا المربع مشغول.", show_alert=True)
        return

    game["board"][cell] = symbol
    answer_callback_query(cq_id)

    result = _ttt_winner(game["board"])
    x_name = players["X"][1]
    o_name = players.get("O", (None, "؟"))[1]

    if result == "draw":
        del TICTACTOE_GAMES[chat_id]
        edit_message_text(chat_id, message_id,
                           f"❌⭕ {x_name} ضد {o_name}\n\nالنتيجة: تعادل! 🤝",
                           reply_markup=_ttt_keyboard(game["board"]))
    elif result in ("X", "O"):
        winner_name = x_name if result == "X" else o_name
        del TICTACTOE_GAMES[chat_id]
        db.add_trivia_score(chat_id, players[result][0], winner_name, 5)
        edit_message_text(chat_id, message_id,
                           f"❌⭕ {x_name} ضد {o_name}\n\n🎉 فاز {winner_name} ({_ttt_symbol(result)}) — +5 نقاط!",
                           reply_markup=_ttt_keyboard(game["board"]))
    else:
        game["turn"] = "O" if symbol == "X" else "X"
        next_name = o_name if game["turn"] == "O" else x_name
        edit_message_text(chat_id, message_id,
                           f"❌ {x_name}  ضد  ⭕ {o_name}\n\nدور: {next_name} {_ttt_symbol(game['turn'])}",
                           reply_markup=_ttt_keyboard(game["board"]))


# ----------------------------------------------------------------
# لعبة "أربعة متتالية" (Connect 4) — تحدي بين لاعبين، شبكة 7 أعمدة × 6 صفوف،
# كل لاعب يختار عمود فتسقط قطعته لأسفل مكان فاضي بنفس العمود (جاذبية حقيقية،
# مو اختيار مربع عشوائي)، أول من يكوّن 4 متتالية (أفقي/عمودي/قطري) يفوز.
# ----------------------------------------------------------------
CONNECT4_GAMES = {}  # chat_id -> {"board": [[None]*7 for _ in range(6)], "players": {"R":(id,name),"Y":(id,name)},
                      #             "turn": "R"/"Y", "message_id": int}
C4_COLS = 7
C4_ROWS = 6


def _c4_symbol(v):
    return {"R": "🔴", "Y": "🟡"}.get(v, "⚪")


def _c4_keyboard(board, opened_cols=None):
    # صف أزرار الإسقاط بالأعلى (رقم كل عمود)، وتحته شبكة اللوحة الحالية (للعرض فقط)
    top_row = [(str(c + 1), f"c4_{c}") for c in range(C4_COLS)]
    rows = [top_row]
    for r in range(C4_ROWS):
        rows.append([(_c4_symbol(board[r][c]), f"c4_{c}") for c in range(C4_COLS)])
    return inline_keyboard(rows)


def _c4_drop(board, col, symbol):
    """يسقط القطعة بأسفل مكان فاضي بنفس العمود. يرجع رقم الصف اللي وقفت فيه، أو None لو العمود ممتلئ."""
    for r in range(C4_ROWS - 1, -1, -1):
        if board[r][col] is None:
            board[r][col] = symbol
            return r
    return None


def _c4_winner(board, last_row, last_col):
    symbol = board[last_row][last_col]
    if not symbol:
        return None
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
    for dr, dc in directions:
        count = 1
        r, c = last_row + dr, last_col + dc
        while 0 <= r < C4_ROWS and 0 <= c < C4_COLS and board[r][c] == symbol:
            count += 1
            r += dr
            c += dc
        r, c = last_row - dr, last_col - dc
        while 0 <= r < C4_ROWS and 0 <= c < C4_COLS and board[r][c] == symbol:
            count += 1
            r -= dr
            c -= dc
        if count >= 4:
            return symbol
    if all(board[0][c] is not None for c in range(C4_COLS)):
        return "draw"
    return None


def is_connect4_active(chat_id):
    return chat_id in CONNECT4_GAMES


def start_connect4_game(chat_id, user_id, user_name):
    board = [[None] * C4_COLS for _ in range(C4_ROWS)]
    message_id = send_message(
        chat_id,
        f"🔴🟡 أربعة متتالية بدأت!\n{user_name} يلعب 🔴 (أول ضغطة).\n"
        f"بانتظار عضو ثاني يضغط أي عمود ليصير 🟡...\nاضغطوا رقم العمود لإسقاط قطعتكم فيه 👇",
        reply_markup=_c4_keyboard(board),
    )
    CONNECT4_GAMES[chat_id] = {
        "board": board,
        "players": {"R": (user_id, user_name)},
        "turn": "R",
        "message_id": message_id,
    }
    _track_game_msg(chat_id, message_id)


def handle_connect4_button(chat_id, cq_id, user_id, user_name, col, message_id):
    game = CONNECT4_GAMES.get(chat_id)
    if not game:
        answer_callback_query(cq_id, text="🚫 ما فيه لعبة أربعة متتالية نشطة حالياً. اكتب «أربعة متتالية» لبدء واحدة.",
                               show_alert=True)
        return

    players = game["players"]

    # عضو ثاني ينضم كـ Y أول ما يضغط (لازم يكون مختلف عن اللاعب الأول)
    if "Y" not in players:
        if user_id == players["R"][0]:
            answer_callback_query(cq_id, text="🚫 لازم عضو ثاني غيرك يلعب 🟡 أول.", show_alert=True)
            return
        players["Y"] = (user_id, user_name)

    symbol = "R" if players["R"][0] == user_id else ("Y" if players.get("Y", (None,))[0] == user_id else None)
    if symbol is None:
        answer_callback_query(cq_id, text="🚫 هذي الجولة بين لاعبين محددين، انتظر جولة جديدة.", show_alert=True)
        return

    if game["turn"] != symbol:
        answer_callback_query(cq_id, text="⏳ مو دورك، انتظر دور الطرف الثاني.", show_alert=True)
        return

    row = _c4_drop(game["board"], col, symbol)
    if row is None:
        answer_callback_query(cq_id, text="🚫 هذا العمود ممتلئ، اختر عمود ثاني.", show_alert=True)
        return

    answer_callback_query(cq_id)

    result = _c4_winner(game["board"], row, col)
    r_name = players["R"][1]
    y_name = players.get("Y", (None, "؟"))[1]

    if result == "draw":
        del CONNECT4_GAMES[chat_id]
        edit_message_text(chat_id, message_id,
                           f"🔴🟡 {r_name} ضد {y_name}\n\nالنتيجة: تعادل! 🤝 (اللوحة امتلأت)",
                           reply_markup=_c4_keyboard(game["board"]))
    elif result in ("R", "Y"):
        winner_name = r_name if result == "R" else y_name
        del CONNECT4_GAMES[chat_id]
        db.add_trivia_score(chat_id, players[result][0], winner_name, 5)
        edit_message_text(chat_id, message_id,
                           f"🔴🟡 {r_name} ضد {y_name}\n\n🎉 فاز {winner_name} ({_c4_symbol(result)}) بأربعة متتالية! +5 نقاط",
                           reply_markup=_c4_keyboard(game["board"]))
    else:
        game["turn"] = "Y" if symbol == "R" else "R"
        next_name = y_name if game["turn"] == "Y" else r_name
        edit_message_text(chat_id, message_id,
                           f"🔴 {r_name}  ضد  🟡 {y_name}\n\nدور: {next_name} {_c4_symbol(game['turn'])}",
                           reply_markup=_c4_keyboard(game["board"]))


# ----------------------------------------------------------------
# لعبة "أوثيلو / ريفيرسي" (Othello / Reversi) — شبكة 8×8، لاعبان بأقراص
# سوداء وبيضاء، كل لاعب يضع قرصه ليحاصر أقراص المنافس بين قرصه الجديد
# وقرص آخر له بنفس الخط (أفقي/عمودي/قطري) فتنقلب كل الأقراص المحاصرة
# للونه تلقائياً. تنتهي اللعبة لما يمتلئ اللوح أو ما يعد فيه نقلة ممكنة
# لأي طرف، ويفوز صاحب العدد الأكبر من الأقراص.
# ----------------------------------------------------------------
OTHELLO_GAMES = {}  # chat_id -> {"board": [[None]*8 for _ in range(8)],
                     #             "players": {"B": (id,name), "W": (id,name)},
                     #             "turn": "B"/"W", "message_id": int}
OTHELLO_SIZE = 8
OTHELLO_DIRECTIONS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _othello_symbol(v):
    return {"B": "⚫", "W": "⚪"}.get(v, "🟩")


def _othello_new_board():
    board = [[None] * OTHELLO_SIZE for _ in range(OTHELLO_SIZE)]
    board[3][3] = "W"
    board[3][4] = "B"
    board[4][3] = "B"
    board[4][4] = "W"
    return board


def _othello_flips(board, row, col, symbol):
    """يرجع كل الأقراص اللي بتنقلب لو حط اللاعب قرصه بهالخانة (فاضية قائمة = نقلة غير صالحة)."""
    if board[row][col] is not None:
        return []
    opponent = "W" if symbol == "B" else "B"
    all_flips = []
    for dr, dc in OTHELLO_DIRECTIONS:
        line = []
        r, c = row + dr, col + dc
        while 0 <= r < OTHELLO_SIZE and 0 <= c < OTHELLO_SIZE and board[r][c] == opponent:
            line.append((r, c))
            r += dr
            c += dc
        if line and 0 <= r < OTHELLO_SIZE and 0 <= c < OTHELLO_SIZE and board[r][c] == symbol:
            all_flips.extend(line)
    return all_flips


def _othello_valid_moves(board, symbol):
    moves = {}
    for r in range(OTHELLO_SIZE):
        for c in range(OTHELLO_SIZE):
            flips = _othello_flips(board, r, c, symbol)
            if flips:
                moves[(r, c)] = flips
    return moves


def _othello_score(board):
    black = sum(row.count("B") for row in board)
    white = sum(row.count("W") for row in board)
    return black, white


def _othello_keyboard(board, valid_moves=None):
    valid_moves = valid_moves or {}
    rows = []
    for r in range(OTHELLO_SIZE):
        row = []
        for c in range(OTHELLO_SIZE):
            if board[r][c]:
                label = _othello_symbol(board[r][c])
            elif (r, c) in valid_moves:
                label = "✳️"
            else:
                label = "🟩"
            row.append((label, f"otl_{r}_{c}"))
        rows.append(row)
    return inline_keyboard(rows)


def is_othello_active(chat_id):
    return chat_id in OTHELLO_GAMES


def start_othello_game(chat_id, user_id, user_name):
    board = _othello_new_board()
    valid_moves = _othello_valid_moves(board, "B")
    message_id = send_message(
        chat_id,
        f"⚫⚪ أوثيلو (ريفيرسي) بدأت!\n{user_name} يلعب ⚫ (أول ضغطة).\n"
        f"بانتظار عضو ثاني يضغط أي خانة ليصير ⚪...\n"
        f"اضغطوا خانة (✳️) لمحاصرة أقراص الخصم وقلبها للونكم 👇",
        reply_markup=_othello_keyboard(board, valid_moves),
    )
    OTHELLO_GAMES[chat_id] = {
        "board": board,
        "players": {"B": (user_id, user_name)},
        "turn": "B",
        "message_id": message_id,
    }
    _track_game_msg(chat_id, message_id)


def handle_othello_button(chat_id, cq_id, user_id, user_name, row, col, message_id):
    game = OTHELLO_GAMES.get(chat_id)
    if not game:
        answer_callback_query(cq_id, text="🚫 ما فيه لعبة أوثيلو نشطة حالياً. اكتب «أوثيلو» لبدء واحدة.",
                               show_alert=True)
        return

    players = game["players"]

    # عضو ثاني ينضم كـ W أول ما يضغط (لازم يكون مختلف عن اللاعب الأول)
    if "W" not in players:
        if user_id == players["B"][0]:
            answer_callback_query(cq_id, text="🚫 لازم عضو ثاني غيرك يلعب ⚪ أول.", show_alert=True)
            return
        players["W"] = (user_id, user_name)

    symbol = "B" if players["B"][0] == user_id else ("W" if players.get("W", (None,))[0] == user_id else None)
    if symbol is None:
        answer_callback_query(cq_id, text="🚫 هذي الجولة بين لاعبين محددين، انتظر جولة جديدة.", show_alert=True)
        return

    if game["turn"] != symbol:
        answer_callback_query(cq_id, text="⏳ مو دورك، انتظر دور الطرف الثاني.", show_alert=True)
        return

    flips = _othello_flips(game["board"], row, col, symbol)
    if not flips:
        answer_callback_query(cq_id, text="🚫 نقلة غير صالحة هنا (لازم تحاصر قرص أو أكثر للخصم).", show_alert=True)
        return

    game["board"][row][col] = symbol
    for fr, fc in flips:
        game["board"][fr][fc] = symbol
    answer_callback_query(cq_id)

    b_name = players["B"][1]
    w_name = players.get("W", (None, "؟"))[1]
    opponent = "W" if symbol == "B" else "B"

    def _finish(reason):
        black, white = _othello_score(game["board"])
        del OTHELLO_GAMES[chat_id]
        if black == white:
            edit_message_text(chat_id, message_id,
                               f"⚫⚪ {b_name} ضد {w_name}\n\n{reason}\nالنتيجة: تعادل! 🤝 (⚫{black} - ⚪{white})",
                               reply_markup=_othello_keyboard(game["board"]))
        else:
            winner_symbol = "B" if black > white else "W"
            winner_name = b_name if winner_symbol == "B" else w_name
            winner_id = players[winner_symbol][0]
            db.add_trivia_score(chat_id, winner_id, winner_name, 5)
            edit_message_text(chat_id, message_id,
                               f"⚫⚪ {b_name} ضد {w_name}\n\n{reason}\n"
                               f"🎉 فاز {winner_name} ({_othello_symbol(winner_symbol)}) بالنقاط "
                               f"(⚫{black} - ⚪{white})! +5 نقاط",
                               reply_markup=_othello_keyboard(game["board"]))

    # لو ما فيه نقلات ممكنة للطرف الثاني، يضل الدور لنفس اللاعب؛ ولو ما فيه نقلات لأي
    # طرف أو امتلأ اللوح تنتهي اللعبة فوراً.
    opponent_moves = _othello_valid_moves(game["board"], opponent)
    if not opponent_moves:
        my_moves_again = _othello_valid_moves(game["board"], symbol)
        if not my_moves_again:
            _finish("انتهت اللعبة (ما فيه نقلات ممكنة لأي طرف).")
            return
        game["turn"] = symbol
        my_name = b_name if symbol == "B" else w_name
        edit_message_text(chat_id, message_id,
                           f"⚫ {b_name}  ضد  ⚪ {w_name}\n\n"
                           f"⚠️ ما فيه نقلة ممكنة للطرف الثاني، دور {my_name} {_othello_symbol(symbol)} مرة ثانية",
                           reply_markup=_othello_keyboard(game["board"], my_moves_again))
        return

    game["turn"] = opponent
    next_name = w_name if opponent == "W" else b_name
    edit_message_text(chat_id, message_id,
                       f"⚫ {b_name}  ضد  ⚪ {w_name}\n\nدور: {next_name} {_othello_symbol(opponent)}",
                       reply_markup=_othello_keyboard(game["board"], opponent_moves))


# ----------------------------------------------------------------
# لعبة "الذاكرة" (Memory Match) — شبكة 4×4 (16 بطاقة / 8 أزواج)، تحدي بين
# لاعبين يتبادلون الأدوار. كل دور: افتح بطاقتين. لو تطابقتا تُحسب نقطة
# للاعب وتبقى مكشوفة له ويلعب دور ثاني متتالي (نفس قاعدة لعبة الذاكرة
# التقليدية). لو ما تطابقتا تُقلبان تلقائياً (تُخفيان) أول ما يبدأ الطرف
# الثاني دوره، وينتقل الدور. تنتهي اللعبة لما تنكشف كل الأزواج، والفوز
# لصاحب أكبر عدد أزواج.
# ----------------------------------------------------------------
MEMORY_GAMES = {}  # chat_id -> {"board": [emoji]*16, "matched": set(), "pending_reveal": [idx?],
                    #             "mismatch_pair": (i,j)?, "players": {"1":(id,name),"2":(id,name)},
                    #             "turn": "1"/"2", "scores": {"1":0,"2":0}, "message_id": int}
MEMORY_SIZE = 16
MEMORY_COLS = 4
MEMORY_HIDDEN = "❓"
MEMORY_EMOJI_POOL = ["🍕", "🍔", "🍟", "🌭", "🍩", "🍦", "🍇", "🍓"]


def _memory_new_board():
    pairs = MEMORY_EMOJI_POOL * 2
    random.shuffle(pairs)
    return pairs


def _memory_visible_indices(game):
    visible = set(game["matched"]) | set(game["pending_reveal"])
    if game["mismatch_pair"]:
        visible |= set(game["mismatch_pair"])
    return visible


def _memory_keyboard(game):
    visible = _memory_visible_indices(game)
    rows = []
    for r in range(MEMORY_SIZE // MEMORY_COLS):
        row = []
        for c in range(MEMORY_COLS):
            i = r * MEMORY_COLS + c
            label = game["board"][i] if i in visible else MEMORY_HIDDEN
            row.append((label, f"mm_{i}"))
        rows.append(row)
    return inline_keyboard(rows)


def is_memory_active(chat_id):
    return chat_id in MEMORY_GAMES


def start_memory_game(chat_id, user_id, user_name):
    game = {
        "board": _memory_new_board(),
        "matched": set(),
        "pending_reveal": [],
        "mismatch_pair": None,
        "players": {"1": (user_id, user_name)},
        "turn": "1",
        "scores": {"1": 0, "2": 0},
        "message_id": None,
    }
    message_id = send_message(
        chat_id,
        f"🧠 لعبة الذاكرة (Memory Match) بدأت!\n{user_name} يلعب أول (اللاعب 1).\n"
        f"بانتظار عضو ثاني يضغط أي بطاقة ليصير اللاعب 2...\n"
        f"افتحوا بطاقتين بدوركم وطابقوا الصور المتشابهة لجمع أكبر عدد نقاط 👇",
        reply_markup=_memory_keyboard(game),
    )
    game["message_id"] = message_id
    MEMORY_GAMES[chat_id] = game
    _track_game_msg(chat_id, message_id)


def _memory_status_line(game):
    p1_name = game["players"]["1"][1]
    p2_name = game["players"].get("2", (None, "؟"))[1]
    return (f"🧠 {p1_name} 🆚 {p2_name}\n"
            f"🏆 {p1_name}: {game['scores']['1']}  |  🏆 {p2_name}: {game['scores']['2']}")


def handle_memory_button(chat_id, cq_id, user_id, user_name, cell, message_id):
    game = MEMORY_GAMES.get(chat_id)
    if not game:
        answer_callback_query(cq_id, text="🚫 ما فيه لعبة ذاكرة نشطة حالياً. اكتب «لعبة الذاكرة» لبدء واحدة.",
                               show_alert=True)
        return

    players = game["players"]

    # عضو ثاني ينضم كلاعب 2 أول ما يضغط (لازم يكون مختلف عن اللاعب الأول)
    if "2" not in players:
        if user_id == players["1"][0]:
            answer_callback_query(cq_id, text="🚫 لازم عضو ثاني غيرك يلعب كلاعب 2 أول.", show_alert=True)
            return
        players["2"] = (user_id, user_name)

    symbol = "1" if players["1"][0] == user_id else ("2" if players.get("2", (None,))[0] == user_id else None)
    if symbol is None:
        answer_callback_query(cq_id, text="🚫 هذي الجولة بين لاعبين محددين، انتظر جولة جديدة.", show_alert=True)
        return

    if game["turn"] != symbol:
        answer_callback_query(cq_id, text="⏳ مو دورك، انتظر دور الطرف الثاني.", show_alert=True)
        return

    # لو فيه زوج مكشوف من محاولة فاشلة سابقة، يُخفى أول ما يبدأ صاحب الدور الجديد
    # (ما يستهلك ضغطته الحالية، بس ينظف الظهور القديم قبل معالجة اختياره).
    if game["mismatch_pair"]:
        game["mismatch_pair"] = None

    if cell in game["matched"] or cell in game["pending_reveal"]:
        answer_callback_query(cq_id, text="🚫 هذي البطاقة مكشوفة أصلاً، اختر بطاقة ثانية.", show_alert=True)
        return

    game["pending_reveal"].append(cell)
    answer_callback_query(cq_id)

    if len(game["pending_reveal"]) == 1:
        my_name = players[symbol][1]
        edit_message_text(chat_id, message_id,
                           f"{_memory_status_line(game)}\n\nدور: {my_name} — اختر بطاقة ثانية 🃏",
                           reply_markup=_memory_keyboard(game))
        return

    i, j = game["pending_reveal"]
    game["pending_reveal"] = []
    my_name = players[symbol][1]

    if game["board"][i] == game["board"][j]:
        game["matched"].add(i)
        game["matched"].add(j)
        game["scores"][symbol] += 1

        if len(game["matched"]) == MEMORY_SIZE:
            p1_name = players["1"][1]
            p2_name = players.get("2", (None, "؟"))[1]
            score1, score2 = game["scores"]["1"], game["scores"]["2"]
            del MEMORY_GAMES[chat_id]
            if score1 == score2:
                edit_message_text(chat_id, message_id,
                                   f"🧠 {p1_name} 🆚 {p2_name}\n\n"
                                   f"انتهت اللعبة! تعادل 🤝 ({score1} - {score2})",
                                   reply_markup=_memory_keyboard(game))
            else:
                winner_symbol = "1" if score1 > score2 else "2"
                winner_name = players[winner_symbol][1]
                db.add_trivia_score(chat_id, players[winner_symbol][0], winner_name, 5)
                edit_message_text(chat_id, message_id,
                                   f"🧠 {p1_name} 🆚 {p2_name}\n\n"
                                   f"🎉 انتهت اللعبة! فاز {winner_name} ({score1} - {score2}) — +5 نقاط",
                                   reply_markup=_memory_keyboard(game))
            return

        edit_message_text(chat_id, message_id,
                           f"{_memory_status_line(game)}\n\n"
                           f"✅ تطابق! دور {my_name} يستمر — اختر بطاقة 🃏",
                           reply_markup=_memory_keyboard(game))
        return

    # ما فيه تطابق: تنقلب البطاقتان تلقائياً بأول ضغطة من الطرف الثاني، وينتقل الدور له الآن
    game["mismatch_pair"] = (i, j)
    next_symbol = "2" if symbol == "1" else "1"
    game["turn"] = next_symbol
    next_name = players[next_symbol][1]
    edit_message_text(chat_id, message_id,
                       f"{_memory_status_line(game)}\n\n"
                       f"❌ بدون تطابق! دور: {next_name} 🃏",
                       reply_markup=_memory_keyboard(game))


# ----------------------------------------------------------------
# 🎴 لعبة "درافت الأنمي" — لاعبان يتناوبون على بناء فريق 4 شخصيات من أنمي
# واحد بس (جوجيتسو كايسن / قاتل الشياطين / سولو لفلينج)، بميكانيكية
# "ظاهر/مخفي": كل دور بطاقة معروفة، واللاعب يوخذها أو يجازف بسحب مخفي
# عشوائي (والبطاقة الظاهرة المرفوضة تروح مجاناً للطرف الثاني). بعد اكتمال
# الفريقين، Gemini يحكم أي فريق أقوى بدقة بناءً على قوى الشخصيات الحقيقية.
# المنطق الخالص بملف anime_draft.py.
# ----------------------------------------------------------------
DRAFT_GAMES = {}  # chat_id -> {"phase", "starter_id", "starter_name", "state": anime_draft state}
DRAFT_WIN_POINTS = 20
DRAFT_AI_ID = -1  # ثابت سالب: لا يتعارض أبداً مع أي user_id حقيقي بتيليجرام (دائماً موجب)
DRAFT_AI_NAME = "🤖 الذكاء الاصطناعي"
DRAFT_AI_VISIBLE_CHANCE = 0.65  # احتمال أخذ AI البطاقة الظاهرة بدل المجازفة بالمجهول


def _draft_category_keyboard():
    return inline_keyboard([[(label, f"draftcat_{key}")] for key, label in anime_draft.list_categories()])


def start_draft_game(chat_id, user_id, user_name):
    if chat_id in DRAFT_GAMES:
        send_message(chat_id, "🎴 فيه درافت نشط بالمجموعة الحين. أنهوه أول أو اكتب «إنهاء اللعب».")
        return
    DRAFT_GAMES[chat_id] = {"phase": "choosing_category", "starter_id": user_id, "starter_name": user_name,
                             "state": None}
    message_id = send_message(chat_id,
                               f"🎴 درافت الأنمي!\n{user_name} يختار الفئة أول:",
                               reply_markup=_draft_category_keyboard())
    _track_game_msg(chat_id, message_id)


def _draft_visible_keyboard(visible_name):
    # اسم الشخصية على الزر نفسه بدل نص عام — يوضح فوراً وش تاخذ لو ضغطت
    take_label = f"✅ {visible_name}"
    if len(take_label) > 40:  # حد معقول لعرض الزر بتطبيق تليجرام
        take_label = take_label[:39] + "…"
    return inline_keyboard([[("🔒 مجهولة", "draftpick_hidden"), (take_label, "draftpick_visible")]])


def _draft_pick_progress(state):
    done = sum(len(team) for team in state["teams"].values())
    total = anime_draft.TEAM_SIZE * 2
    return done + 1, total  # +1 لأن الاختيار الحالي لسا ما انحسب


PLAYER_ICONS = ["🔵", "🟠"]  # ثابتة حسب ترتيب اللاعبين بالدرافت — لتمييز الفريقين بصرياً بكل مكان


def _draft_team_lines(state):
    """سطرين يلخّصان فريق كل لاعب لحد الآن — تُستخدم كابتشن دائم تحت كل بطاقة دور جديدة."""
    lines = []
    for i, pid in enumerate(state["player_order"]):
        icon = PLAYER_ICONS[i] if i < len(PLAYER_ICONS) else "⚪"
        team_names = [c["name"] for c in state["teams"][pid]]
        filled = "، ".join(team_names) if team_names else "— لسا فاضي —"
        lines.append(f"{icon} فريق {state['names'][pid]} ({len(team_names)}/{anime_draft.TEAM_SIZE}): {filled}")
    return lines


def _draft_team_rows_for_image(state):
    """يبني نفس معلومات _draft_team_lines لكن كصور مصغّرة (لصف الفرق الدائم
    داخل بطاقة الدور نفسها بدل نص فقط) — يحمّل صورة كل شخصية مأخوذة لحد الآن
    من مكتبة character_photos (أو None لو ما لها صورة، تُرسم بحرف بديل)."""
    rows = []
    for i, pid in enumerate(state["player_order"]):
        icon = PLAYER_ICONS[i] if i < len(PLAYER_ICONS) else "⚪"
        team = state["teams"][pid]
        label = f"{icon} فريق {state['names'][pid]} ({len(team)}/{anime_draft.TEAM_SIZE})"
        picks = [(c["name"], _draft_photo_bytes_for(c["name"])) for c in team]
        rows.append({"label": label, "picks": picks})
    return rows


def _draft_photo_bytes_for(name):
    """يجيب بايتات صورة الشخصية من مكتبة character_photos المشتركة (لو مضافة
    من المالك عبر: اضافة صورة شخصية الاسم) — نفس الصورة تظهر بكل المجموعات.
    يرجع None بهدوء لو ما فيه صورة أو صار خطأ بالتحميل."""
    row = db.get_character_photo_by_name(name)
    if not row:
        return None
    file_path = get_file_path(row["file_id"])
    if not file_path:
        return None
    return download_file_bytes(file_path)


def _send_draft_turn(chat_id, game):
    """يكشف بطاقة ظاهرة جديدة ويرسل بطاقة الدور (ظاهرة+مخفية جنب بعض) مع أزرار
    القرار، وتحتها دائماً صف مصغّر لكل فريق (صور صغيرة للشخصيات المأخوذة لحد
    الآن + خانات فاضية للباقي). لو توليد الصورة غير متوفر يرجع تلقائياً لعرض
    نصي بنفس المعلومات (بدون الصور المصغّرة، بس بنفس ملخص الفرق)."""
    state = game["state"]
    visible = anime_draft.reveal_visible(state)
    if visible is None:
        _finish_draft(chat_id, game)
        return

    turn_name = state["names"][state["turn"]]
    pick_number, total_picks = _draft_pick_progress(state)
    keyboard = _draft_visible_keyboard(visible["name"])

    ready, _err = draft_card_image.image_ready()
    message_id = None
    if ready:
        photo_bytes = _draft_photo_bytes_for(visible["name"])
        team_rows = _draft_team_rows_for_image(state)
        try:
            card_png = draft_card_image.build_turn_card(turn_name, pick_number, total_picks,
                                                          visible["name"], photo_bytes,
                                                          pool_remaining=len(state["pool"]),
                                                          teams=team_rows, team_size=anime_draft.TEAM_SIZE)
            message_id = send_photo_bytes(chat_id, card_png, "draft_turn.png", reply_markup=keyboard)
        except Exception:
            message_id = None

    if not message_id:
        team_lines = "\n".join(_draft_team_lines(state))
        caption = (f"🎴 دور: {turn_name}   —   الاختيار {pick_number} من {total_picks}\n\n"
                   f"البطاقة الظاهرة: {visible['name']}\nتاخذها؟ أو تجازف بسحب مخفي؟\n\n"
                   f"{team_lines}")
        message_id = send_message(chat_id, caption, reply_markup=keyboard)
    _track_game_msg(chat_id, message_id)


def handle_draft_category_button(chat_id, cq_id, user_id, choice_key):
    game = DRAFT_GAMES.get(chat_id)
    if not game or game["phase"] != "choosing_category":
        answer_callback_query(cq_id, text="🚫 ما فيه درافت بانتظار اختيار فئة.", show_alert=True)
        return
    if user_id != game["starter_id"]:
        answer_callback_query(cq_id, text="🚫 اللي بدأ الدرافت هو من يختار الفئة.", show_alert=True)
        return
    if choice_key not in dict(anime_draft.list_categories()):
        answer_callback_query(cq_id)
        return

    answer_callback_query(cq_id)
    game["phase"] = "waiting_player2"
    game["category_key"] = choice_key
    label = anime_draft.category_label(choice_key)
    message_id = send_message(
        chat_id,
        f"🎴 الفئة: {label}\n{game['starter_name']} بانتظار خصم! اضغط «🙋 انضم» لتبدأ المبارزة،\n"
        f"أو العب فوراً ضد الذكاء الاصطناعي لو ما لقيت فريق.",
        reply_markup=inline_keyboard([[("🙋 انضم", "draftjoin")], [("🤖 العب ضد AI", "draftai")]]))
    _track_game_msg(chat_id, message_id)


def handle_draft_join_button(chat_id, cq_id, user_id, user_name):
    game = DRAFT_GAMES.get(chat_id)
    if not game or game["phase"] != "waiting_player2":
        answer_callback_query(cq_id, text="🚫 ما فيه درافت بانتظار لاعب ثاني.", show_alert=True)
        return
    if user_id == game["starter_id"]:
        answer_callback_query(cq_id, text="🚫 لازم عضو ثاني غيرك.", show_alert=True)
        return

    answer_callback_query(cq_id)
    game["phase"] = "drafting"
    game["state"] = anime_draft.new_draft_state(game["category_key"], game["starter_id"], game["starter_name"],
                                                 user_id, user_name)
    send_message(chat_id, f"⚔️ {game['starter_name']} ضد {user_name}! يبدأ الدرافت — دور {game['starter_name']} أول.")
    _send_draft_turn(chat_id, game)


def handle_draft_ai_button(chat_id, cq_id, user_id):
    """يبدأ الدرافت فوراً ضد بوت AI بسيط لو ما فيه عضو ثاني متوفر — يسمح
    للاعب واحد يلعب ويستمتع باللعبة بدل ما ينتظر خصم ما يجي."""
    game = DRAFT_GAMES.get(chat_id)
    if not game or game["phase"] != "waiting_player2":
        answer_callback_query(cq_id, text="🚫 ما فيه درافت بانتظار لاعب ثاني.", show_alert=True)
        return
    if user_id != game["starter_id"]:
        answer_callback_query(cq_id, text="🚫 اللي بدأ الدرافت هو من يقرر يلعب مع AI أو لا.", show_alert=True)
        return

    answer_callback_query(cq_id)
    game["phase"] = "drafting"
    game["vs_ai"] = True
    game["state"] = anime_draft.new_draft_state(game["category_key"], game["starter_id"], game["starter_name"],
                                                 DRAFT_AI_ID, DRAFT_AI_NAME)
    send_message(chat_id, f"⚔️ {game['starter_name']} ضد {DRAFT_AI_NAME}! يبدأ الدرافت — دور {game['starter_name']} أول.")
    _send_draft_turn(chat_id, game)


def _send_hidden_reveal(chat_id, taker_name, character_name):
    """يرسل بطاقة كشف فورية بعد ما لاعب يجازف بزر «مجهولة» — عشان يشوف صورة
    الشخصية اللي طلعت له فوراً (لحظة مفاجأة حقيقية) بدل ما يبقى بس اسم نصي.
    يرجع تلقائياً لرسالة نصية لو توليد الصورة غير متوفر أو صار خطأ."""
    caption = f"🎲 {taker_name} جازف بالمجهول... وطلعت له:"
    ready, _err = draft_card_image.image_ready()
    message_id = None
    if ready:
        photo_bytes = _draft_photo_bytes_for(character_name)
        try:
            card_png = draft_card_image.build_reveal_card(character_name, photo_bytes)
            message_id = send_photo_bytes(chat_id, card_png, "draft_reveal.png", caption=caption)
        except Exception:
            message_id = None
    if not message_id:
        message_id = send_message(chat_id, f"{caption} {character_name}!")
    _track_game_msg(chat_id, message_id)


def handle_delete_character_photo_button(chat_id, cq_id, user_id, entry_id_str):
    """يعالج زر «🗑️ حذف هذي الصورة» اللي يظهر مباشرة تحت رسالة تأكيد الإضافة —
    تراجع فوري بضغطة وحدة لو المالك أخطأ باسم أو صورة، بدون ما يحتاج يكتب أمر
    حذف يدوي بالاسم. محصور بالمالك الأصلي فقط (نفس صلاحية إضافة/حذف الصور)."""
    if user_id != MASTER_ADMIN_ID:
        answer_callback_query(cq_id, text="🚫 هذي الميزة للمالك الأصلي للبوت فقط.", show_alert=True)
        return
    if not entry_id_str.isdigit():
        answer_callback_query(cq_id)
        return
    entry_id = int(entry_id_str)
    row = db.get_character_photo_by_id(entry_id)
    if not row:
        answer_callback_query(cq_id, text="✅ محذوفة أصلاً (ما فيه شي يتراجع عنه).", show_alert=True)
        return
    db.delete_character_photo_by_id(entry_id)
    answer_callback_query(cq_id, text=f"🗑️ تم حذف صورة «{row['name']}».", show_alert=True)
    send_message(chat_id, f"🗑️ تراجعت عن صورة «{row['name']}» (#{entry_id}) وانحذفت.")


def handle_delete_monster_photo_button(chat_id, cq_id, user_id, entry_id_str):
    """نفس فكرة handle_delete_character_photo_button بالضبط، بس لصور الوحوش."""
    if user_id != MASTER_ADMIN_ID:
        answer_callback_query(cq_id, text="🚫 هذي الميزة للمالك الأصلي للبوت فقط.", show_alert=True)
        return
    if not entry_id_str.isdigit():
        answer_callback_query(cq_id)
        return
    entry_id = int(entry_id_str)
    row = db.get_monster_photo_by_id(entry_id)
    if not row:
        answer_callback_query(cq_id, text="✅ محذوفة أصلاً (ما فيه شي يتراجع عنه).", show_alert=True)
        return
    db.delete_monster_photo_by_id(entry_id)
    answer_callback_query(cq_id, text=f"🗑️ تم حذف صورة «{row['name']}».", show_alert=True)
    send_message(chat_id, f"🗑️ تراجعت عن صورة وحش «{row['name']}» (#{entry_id}) وانحذفت.")


def handle_draft_pick_button(chat_id, cq_id, user_id, choice):
    game = DRAFT_GAMES.get(chat_id)
    if not game or game["phase"] != "drafting":
        answer_callback_query(cq_id, text="🚫 ما فيه درافت نشط حالياً.", show_alert=True)
        return
    state = game["state"]
    if user_id != state["turn"]:
        answer_callback_query(cq_id, text="⏳ مو دورك، انتظر دور الطرف الثاني.", show_alert=True)
        return
    if state["current_visible"] is None:
        answer_callback_query(cq_id, text="🚫 ما فيه بطاقة ظاهرة الحين.", show_alert=True)
        return

    answer_callback_query(cq_id)
    result = anime_draft.resolve_pick(state, choice)
    taker_name = state["names"][result["taken_by"]]

    if choice == "hidden":
        _send_hidden_reveal(chat_id, taker_name, result["taken_char"]["name"])
    else:
        send_message(chat_id, f"✅ {taker_name} أخذ: {result['taken_char']['name']}")

    if result["gifted_to"]:
        send_message(chat_id, f"🎁 والبطاقة الظاهرة «{result['gifted_char']['name']}» ذهبت مجاناً لـ"
                               f"{state['names'][result['gifted_to']]}!")

    if anime_draft.is_draft_complete(state):
        _finish_draft(chat_id, game)
        return

    if game.get("vs_ai") and state["turn"] == DRAFT_AI_ID:
        if _run_draft_ai_turn(chat_id, game):
            return  # اكتملت اللعبة أثناء دور الـAI

    _send_draft_turn(chat_id, game)


def _run_draft_ai_turn(chat_id, game):
    """يشغّل دور الذكاء الاصطناعي تلقائياً بدون أزرار: يقرر بمنطق بسيط (يميل
    لأخذ الظاهرة غالباً، ويجازف بالمجهول أحياناً لواقعية أكثر)، يرسل نفس رسائل
    الكشف/الإهداء اللي يشوفها اللاعب البشري، ثم يرجع True لو اكتمل الدرافت
    بعدها (عشان المتصل يوقف ويعرض النتيجة النهائية بدل ما يبدأ دور جديد)."""
    state = game["state"]
    visible = anime_draft.reveal_visible(state)
    if visible is None:
        _finish_draft(chat_id, game)
        return True

    choice = "visible" if random.random() < DRAFT_AI_VISIBLE_CHANCE else "hidden"
    result = anime_draft.resolve_pick(state, choice)

    if choice == "hidden":
        _send_hidden_reveal(chat_id, DRAFT_AI_NAME, result["taken_char"]["name"])
    else:
        send_message(chat_id, f"🤖 {DRAFT_AI_NAME} أخذ: {result['taken_char']['name']}")

    if result["gifted_to"]:
        send_message(chat_id, f"🎁 والبطاقة الظاهرة «{result['gifted_char']['name']}» ذهبت مجاناً لـ"
                               f"{state['names'][result['gifted_to']]}!")

    if anime_draft.is_draft_complete(state):
        _finish_draft(chat_id, game)
        return True
    return False


def _finish_draft(chat_id, game):
    state = game["state"]
    p1_id, p2_id = state["player_order"]
    p1_name, p2_name = state["names"][p1_id], state["names"][p2_id]
    team1 = [c["name"] for c in state["teams"][p1_id]]
    team2 = [c["name"] for c in state["teams"][p2_id]]
    category_label = anime_draft.category_label(state["category"])

    prompt = anime_draft.build_judge_prompt(category_label, p1_name, team1, p2_name, team2)
    from gemini_client import call_gemini
    ai_result = call_gemini(prompt_text=prompt, max_tokens=280)
    winner_num = anime_draft.parse_judge_result(ai_result)

    if winner_num is None:
        # لو Gemini غير متاح أو ما قدر يحدد: نحسم عشوائياً بدل ما تتعطل اللعبة
        winner_num = random.choice([1, 2])
        reasoning = "تعذّر تقييم الذكاء الاصطناعي هالمرة، فتم الحسم عشوائياً."
    else:
        reasoning = anime_draft.strip_judge_markers(ai_result)

    winner_id, winner_name = (p1_id, p1_name) if winner_num == 1 else (p2_id, p2_name)
    if winner_id != DRAFT_AI_ID:  # ما نسجّل نقاط لصدارة الألعاب باسم الـAI
        db.add_trivia_score(chat_id, winner_id, winner_name, DRAFT_WIN_POINTS)
        points_line = f"🏆 الفائز: {winner_name}! +{DRAFT_WIN_POINTS} نقطة"
    else:
        points_line = f"🏆 الفائز: {winner_name}!"

    del DRAFT_GAMES[chat_id]

    text = (f"🎴 اكتمل الدرافت! ({category_label})\n\n"
            f"فريق {p1_name}: {'، '.join(team1)}\n"
            f"فريق {p2_name}: {'، '.join(team2)}\n\n"
            f"⚖️ حكم الذكاء الاصطناعي:\n{reasoning}\n\n"
            f"{points_line}")
    send_message(chat_id, text)


def _draft_photo_status_text():
    """يبني تقرير: أي شخصيات درافت الأنمي عندها صورة مضافة بمكتبة character_photos
    وأيهم ناقصة — عشان المالك يعرف شنو يكمل رفعه بالخاص (اضافة صورة شخصية الاسم)."""
    lines = ["🖼️ حالة صور درافت الأنمي (المكتبة مشتركة لكل المجموعات):"]
    for key, label in anime_draft.list_categories():
        names = [n for n, _q in anime_draft.ANIME_CATEGORIES[key]["characters"]]
        have = [n for n in names if db.get_character_photo_by_name(n)]
        missing = [n for n in names if n not in have]
        lines.append(f"\n🔹 {label}: {len(have)}/{len(names)} مكتملة")
        if missing:
            lines.append("  ناقصة: " + "، ".join(missing))
    lines.append("\nلإضافة صورة: أرسليها بالخاص بكابشن «اضافة صورة شخصية الاسم» (نفس الاسم بالضبط).")
    return "\n".join(lines)


# ----------------------------------------------------------------
# لعبة "عجلة الأسماء" — يكتب أي عضو قائمة أسماء (مفصولة بمسافة أو فاصلة)،
# البوت يعرضها برسالة وزر "🎡 دوران"، وكل ضغطة تختار اسم عشوائي وتعرض النتيجة
# (تدعم أي استخدام: توزيع أدوار، قرعة، اختيار عشوائي... إلخ).
# ----------------------------------------------------------------
WHEEL_GAMES = {}  # chat_id -> {"names": [...], "message_id": int}
WHEEL_MAX_NAMES = 20


def _parse_wheel_names(arg):
    raw = re.split(r"[,،\n]|\s{1}", arg.strip()) if "," in arg or "،" in arg else arg.strip().split()
    names = [n.strip() for n in raw if n.strip()]
    # إزالة التكرار مع الحفاظ على الترتيب
    seen = set()
    unique_names = []
    for n in names:
        if n not in seen:
            seen.add(n)
            unique_names.append(n)
    return unique_names[:WHEEL_MAX_NAMES]


def _wheel_keyboard():
    return inline_keyboard([[("🎡 دوران", "wheel_spin")]])


def start_wheel_game(chat_id, arg):
    names = _parse_wheel_names(arg)
    if len(names) < 2:
        send_message(chat_id, "استخدم: عجلة اسم1 اسم2 اسم3 ... (أو مفصولين بفاصلة) — لازم اسمين على الأقل.")
        return
    names_text = "، ".join(names)
    message_id = send_message(
        chat_id,
        f"🎡 عجلة الأسماء جاهزة!\nالأسماء: {names_text}\n\nاضغط «دوران» واختار وحد عشوائياً 👇",
        reply_markup=_wheel_keyboard(),
    )
    WHEEL_GAMES[chat_id] = {"names": names, "message_id": message_id}
    _track_game_msg(chat_id, message_id)


def is_wheel_active(chat_id):
    return chat_id in WHEEL_GAMES


def _wheel_frame(names, pointer_index, spinning=True):
    """يبني إطار واحد من العجلة: الأسماء بترتيب دائري والمؤشر ▶ يشير للاسم الحالي أثناء الدوران."""
    lines = []
    for i, n in enumerate(names):
        marker = "▶️ " if i == pointer_index else "    "
        lines.append(f"{marker}{n}")
    header = "🎡 العجلة تدور...\n" if spinning else "🎡 عجلة الأسماء\n"
    return header + "\n".join(lines)


def handle_wheel_spin(chat_id, cq_id, user_name, message_id):
    game = WHEEL_GAMES.get(chat_id)
    if not game:
        answer_callback_query(cq_id, text="🚫 ما فيه عجلة نشطة حالياً. اكتب «عجلة اسم1 اسم2 ...» لبدء واحدة.",
                               show_alert=True)
        return
    names = game["names"]
    n = len(names)
    winner_index = random.randrange(n)
    answer_callback_query(cq_id, text="🎡 بتدور...")

    # محاكاة دوران فعلي: عدد إطارات ثابت (بغض النظر عن عدد الأسماء) عشان ما نغرق
    # تيليجرام بتعديلات كثيرة، مع تباطؤ تدريجي بالتأخير زي عجلة حقيقية تفقد سرعتها،
    # وتُحسب نقطة البداية رياضياً عشان آخر إطار يطابق بالضبط الاسم الفائز.
    frames = min(max(n * 2, 8), 14)
    start = (winner_index - (frames - 1)) % n
    for step in range(frames):
        pointer = (start + step) % n
        progress = step / max(frames - 1, 1)
        delay = 0.08 + (progress ** 2) * 0.35  # تسارع بطء تدريجي قرب النهاية
        try:
            edit_message_text(chat_id, message_id, _wheel_frame(names, pointer, spinning=True),
                               reply_markup=_wheel_keyboard())
        except Exception:
            pass
        time.sleep(delay)

    winner = names[winner_index]
    names_text = "، ".join(names)
    edit_message_text(chat_id, message_id,
                       f"🎡 عجلة الأسماء\nالأسماء: {names_text}\n\n"
                       f"🎯 استقرت على ({user_name}): {winner} 🎉\n\nاضغط «دوران» لمحاولة جديدة 👇",
                       reply_markup=_wheel_keyboard())


# ----------------------------------------------------------------
# لعبة "منافسة" (تصويت بزر بين خيارين) — مختلفة عن نظام تصويت الاقتراحات
# (اللي يعتمد الفصل التالي بالقصة). هنا: يكتب أي عضو شيئين للمقارنة، يظهران
# كزرين، وكل عضو يصوّت لواحد منهم بضغطة (صوت واحد لكل شخص، ممكن يغيّره)،
# والعداد يتحدث لحظياً بنفس الرسالة.
# ----------------------------------------------------------------
DUEL_VOTES = {}  # chat_id -> {"a": str, "b": str, "votes": {user_id: "a"/"b"}, "message_id": int}


def _duel_keyboard(game):
    a_count = sum(1 for v in game["votes"].values() if v == "a")
    b_count = sum(1 for v in game["votes"].values() if v == "b")
    return inline_keyboard([[
        (f"🅰️ {game['a']} ({a_count})", "duel_a"),
        (f"🅱️ {game['b']} ({b_count})", "duel_b"),
    ]])


def _duel_text(game):
    a_count = sum(1 for v in game["votes"].values() if v == "a")
    b_count = sum(1 for v in game["votes"].values() if v == "b")
    total = a_count + b_count
    return (f"⚔️ منافسة: مين الأحسن؟\n\n🅰️ {game['a']}   ضد   🅱️ {game['b']}\n\n"
            f"عدد الأصوات: {total} — صوّتوا بالأسفل 👇")


def start_duel_vote(chat_id, arg):
    parts = re.split(r"\s+مقابل\s+|\s+ضد\s+|\s+vs\s+", arg.strip(), maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        send_message(chat_id, "استخدم: منافسة الشي_الاول مقابل الشي_الثاني\nمثال: منافسة القهوة مقابل الشاي")
        return
    game = {"a": parts[0].strip(), "b": parts[1].strip(), "votes": {}, "message_id": None}
    message_id = send_message(chat_id, _duel_text(game), reply_markup=_duel_keyboard(game))
    game["message_id"] = message_id
    DUEL_VOTES[chat_id] = game
    _track_game_msg(chat_id, message_id)


def is_duel_active(chat_id):
    return chat_id in DUEL_VOTES


def handle_duel_vote(chat_id, cq_id, user_id, choice, message_id):
    game = DUEL_VOTES.get(chat_id)
    if not game:
        answer_callback_query(cq_id, text="🚫 ما فيه منافسة نشطة حالياً. اكتب «منافسة شي1 مقابل شي2» لبدء وحدة.",
                               show_alert=True)
        return
    previous = game["votes"].get(user_id)
    if previous == choice:
        answer_callback_query(cq_id, text="✅ صوتك مسجّل لهذا الخيار من قبل.")
        return
    game["votes"][user_id] = choice
    label = game["a"] if choice == "a" else game["b"]
    answer_callback_query(cq_id, text=f"✅ صوّتّ لـ «{label}»")
    edit_message_text(chat_id, message_id, _duel_text(game), reply_markup=_duel_keyboard(game))


def is_admin(chat_id, user_id):
    return db.is_admin(chat_id, user_id, MASTER_ADMIN_IDS)


# ----------------------------------------------------------------
# 🎖️ نظام رتب الإشراف الثلاث داخل كل مجموعة (فوق نظام is_admin الثنائي القديم):
#   1 🥉 مشرف مبتدئ  — كتم/فك الكتم، إنذار/سحب إنذار، تثبيت/إلغاء تثبيت، حذف رسالة، مناداة الكل
#   2 🥈 مشرف متقدم  — كل صلاحيات المبتدئ + تغيير/حذف الكنية، طرد، مسح كل الإنذارات
#   3 🥇 مشرف عام    — كل صلاحيات المتقدم + حظر/فك الحظر، قفل/فتح المحادثة، مسح الكل، تعيين/إزالة مشرفين
# المالك (MASTER_ADMIN_IDS) دائماً برتبة 3 تلقائياً بكل مجموعة.
# ----------------------------------------------------------------
RANK_NAMES = {
    0: "🙂 عضو عادي (بدون إشراف)",
    1: "🥉 مشرف مبتدئ",
    2: "🥈 مشرف متقدم",
    3: "🥇 مشرف عام",
}

RANK_PERMISSIONS_TEXT = (
    "🥉 <b>مشرف مبتدئ (رتبة 1)</b>\n"
    "كتم / فك الكتم | انذار / سحب انذار | ثبت / الغاء التثبيت | احذف (رسالة) | نادي / طاق\n\n"
    "🥈 <b>مشرف متقدم (رتبة 2)</b>\n"
    "كل صلاحيات المبتدئ +\n"
    "كنية / الغ كنية | طرد | مسح كل الإنذارات | قائمة الإنذارات\n\n"
    "🥇 <b>مشرف عام (رتبة 3)</b>\n"
    "كل صلاحيات المتقدم +\n"
    "حظر / فك الحظر | قفل المحادثة / فتح المحادثة | امسح الكل\n\n"
    "🔒 <b>ملاحظة</b>\n"
    "منح/نزع رتب الإشراف (ضيف ادمن / احذف ادمن) لمالك البوت فقط — أي مشرف (أي رتبة) يقدر "
    "بس يقدّم طلب نزع لمشرف ثاني، وينتظر موافقة المالك: اطلب نزع (رد على المشرف)"
)


def _get_rank(chat_id, user_id):
    return db.get_admin_rank(chat_id, user_id, MASTER_ADMIN_IDS)


def _require_rank(chat_id, user_id, min_rank):
    """يتحقق إن رتبة المستخدم كافية لتنفيذ أمر معيّن. يرجع True لو مسموح، وإلا يرسل رفض ويرجع False."""
    rank = _get_rank(chat_id, user_id)
    if rank >= min_rank:
        return True
    send_message(chat_id, f"🚫 هذا الأمر يحتاج {RANK_NAMES.get(min_rank, f'رتبة {min_rank}')} على الأقل.\n"
                            f"رتبتك الحالية: {RANK_NAMES.get(rank, '🙂 عضو عادي')}")
    return False


# ----------------------------------------------------------------
# ⚡ تشغيل غير متزامن (Threading) — أهم شي لسرعة سيزار بمجموعة كبيرة نشيطة:
# استدعاء Gemini قد ياخذ عدة ثواني، ولو نفّذناه مباشرة داخل معالج الـ webhook
# (خصوصاً على استضافة بعامل وحد زي PythonAnywhere المجانية) يوقف استقبال أي
# رسالة ثانية لحد ما يخلص. تشغيله بخيط منفصل يخلي الرد على تليجرام (200 OK)
# فوري دايماً، وردود الذكاء الاصطناعي توصل بالتوازي بدون ما تعطّل بعضها.
# ----------------------------------------------------------------
def run_async(fn, *args, **kwargs):
    def _wrapped():
        try:
            fn(*args, **kwargs)
        except Exception:
            pass  # أي خطأ غير متوقع بخيط الخلفية ما لازم يوقف باقي البوت
    threading.Thread(target=_wrapped, daemon=True).start()


def _build_models_hud_text():
    """يبني نص بطاقة حالة (HUD) بأسلوب شبه «نظام» لكل نموذج Gemini متاح —
    السرعة، الجودة، الحصة، الإيجابيات والسلبيات، وعدد طلبات اليوم فعلياً."""
    active = model_registry.get_active_model()
    lines = ["🧠 <b>━━ نظام نماذج Gemini ━━</b>\n"]
    for model_id, info in model_registry.all_models().items():
        ok_count, fail_count = db.get_gemini_usage_today(model_id)
        marker = "🟢 [مفعّل الآن]" if model_id == active else "⚪"
        lines.append(
            f"{marker} <b>{info['label']}</b>\n"
            f"  ⚡ السرعة: {info['speed']}\n"
            f"  🎯 الجودة: {info['quality']}\n"
            f"  📊 الحصة المجانية: {info['free_quota']}\n"
            f"  ➕ {' | '.join(info['pros'])}\n"
            f"  ➖ {' | '.join(info['cons'])}\n"
            f"  📈 استهلاك اليوم: {ok_count} ناجح / {fail_count} فاشل\n"
        )
    lines.append("اختر نموذج من الأزرار تحت للتبديل الفوري:")
    return "\n".join(lines)


def _build_models_hud_buttons():
    active = model_registry.get_active_model()
    buttons = []
    for model_id, info in model_registry.all_models().items():
        prefix = "✅ " if model_id == active else ""
        buttons.append([(f"{prefix}{info['label']}", f"own_setmodel:{model_id}")])
    buttons.append([("🔄 تحديث", "own_models")])
    buttons.append([("🔙 رجوع", "own_menu")])
    return buttons


def _build_ytsvc_status_text(testing=False):
    """يبني نص حالة خدمة تحميل الأغاني (Railway) — هل مضبوطة، وهل تستجيب فعلياً."""
    if not youtube_service.service_configured():
        return (
            "🎵 <b>خدمة الأغاني (يوتيوب)</b>\n\n"
            "⚪ غير مضبوطة حالياً.\n\n"
            "لتفعيلها: افتحي إعدادات متغيرات البيئة بـ PythonAnywhere وأضيفي:\n"
            "• <code>YT_SERVICE_URL</code> = رابط خدمة Railway (مثال: "
            "https://your-service.up.railway.app)\n"
            "• <code>YT_SERVICE_API_KEY</code> = نفس المفتاح السري المضبوط "
            "بـ SERVICE_API_KEY على Railway\n\n"
            "بعدها Reload للبوت من PythonAnywhere، وارجعي لهذي الشاشة."
        )

    url_display = YT_SERVICE_URL if len(YT_SERVICE_URL) < 60 else YT_SERVICE_URL[:57] + "..."
    lines = [
        "🎵 <b>خدمة الأغاني (يوتيوب)</b>\n",
        f"🟢 مضبوطة — الرابط: <code>{url_display}</code>\n",
    ]

    if testing:
        ok, detail = youtube_service.check_health()
        if ok:
            lines.append("✅ الاتصال ناجح — الخدمة شغّالة وترد فوراً.")
        else:
            lines.append(f"❌ فشل الاتصال: {detail}\n"
                          "تأكدي إن مشروع Railway شغّال (مو نايم) وإن الرابط صحيح.")
    else:
        lines.append("اضغطي «اختبار الاتصال الآن» للتأكد إنها شغّالة فعلياً.")

    return "\n".join(lines)


def _deliver_song_request(chat_id, user_name, song_query, reply_to_message_id=None):
    """يحمّل أغنية من يوتيوب عبر خدمة Railway المنفصلة ويرسلها صوتياً بالمجموعة.
    يعمل بخيط منفصل (run_async) عشان التحميل يأخذ وقت وما يوقف باقي البوت."""
    if not youtube_service.service_configured():
        send_message(chat_id, "🎵 خدمة الأغاني غير مفعّلة حالياً — لازم المالك يضبطها من لوحة "
                               "المالك أولاً (رابط ومفتاح خدمة Railway).",
                      reply_to_message_id=reply_to_message_id)
        return

    send_message(chat_id, f"🎵 أدور على «{song_query}»، ثانية...", reply_to_message_id=reply_to_message_id)
    ok, result, filename = youtube_service.download_song(song_query)

    if not ok:
        send_message(chat_id, f"⚠️ ما قدرت أجيب الأغنية: {result}", reply_to_message_id=reply_to_message_id)
        return

    sent = send_audio_bytes(chat_id, result, is_mp3=True, timeout=120, filename=filename,
                             caption=f"🎵 {song_query}")
    if not sent:
        send_message(chat_id, "⚠️ حمّلت الأغنية لكن صار خطأ بإرسالها — جرّب مرة ثانية.",
                      reply_to_message_id=reply_to_message_id)


def _deliver_persona_reply(chat_id, user_name, text, reply_to_message_id=None):
    reply = persona.ai_persona_reply(chat_id, user_name, text)
    # رد Reply حقيقي مرتبط برسالة المستخدم نفسها (زي أي رد تيليجرام عادي)،
    # عشان بمجموعة نشيطة يبان بوضوح أي رسالة رد عليها سيزار بالضبط.
    send_message(chat_id, reply, reply_to_message_id=reply_to_message_id)


def _deliver_persona_voice_reply(chat_id, user_name, text, user_id):
    from telegram_client import send_audio_bytes
    reply = persona.ai_persona_reply(chat_id, user_name, text)
    ok, audio_or_err, is_mp3 = persona.ai_voice_reply(reply)
    if ok:
        send_audio_bytes(chat_id, audio_or_err, is_mp3, caption=f"🎙️ {PERSONA_NAME}")
    else:
        # فشل توليد الصوت — لا نترك المستخدم بدون رد، نرسل النص
        send_message(chat_id, reply)



def is_owner_present(chat_id, chat_type):
    """
    حماية من السرقة: يتحقق هل المالك (MASTER_ADMIN_ID) لسا عضو بهذي المجموعة.
    يستخدم تخزين مؤقت (10 دقايق افتراضياً) لتفادي طلب شبكة بكل رسالة.
    الدردشات الخاصة (private) دايماً مسموحة (ما فيها مفهوم "عضوية" أصلاً).
    عند فشل الفحص نفسه (مشكلة شبكة مؤقتة) نعتمد على آخر نتيجة معروفة إن وُجدت،
    وإلا نسمح افتراضياً حتى ما يتعطل البوت بالكامل بسبب عطل مؤقت بالفحص نفسه.
    """
    if not REQUIRE_OWNER_PRESENCE:
        return True
    if chat_type == "private":
        return True

    cached = db.get_owner_presence_cache(chat_id)
    if cached:
        try:
            checked_at = datetime.datetime.fromisoformat(cached["checked_at"])
            age_minutes = (datetime.datetime.utcnow() - checked_at).total_seconds() / 60
            if age_minutes < OWNER_PRESENCE_CACHE_MINUTES:
                return bool(cached["present"])
        except (ValueError, TypeError):
            pass

    status = get_chat_member_status(chat_id, MASTER_ADMIN_ID)
    if status is None:
        # فشل الفحص نفسه (مشكلة شبكة) — استخدمي آخر نتيجة معروفة لو موجودة، وإلا اسمحي مؤقتاً
        return bool(cached["present"]) if cached else True

    present = status in ("creator", "administrator", "member")
    db.set_owner_presence_cache(chat_id, present, datetime.datetime.utcnow().isoformat())
    return present


def parse_duration_to_seconds(text):
    """يحوّل نص مدة عربي بسيط لثوانٍ. يرجع None يعني كتم دائم."""
    text = (text or "").strip()
    if not text:
        return 600  # افتراضي: 10 دقايق لو ما حددت مدة
    if any(w in text for w in ["دائم", "دايم", "نهائي", "ابد"]):
        return None
    m = re.match(r"(\d+)\s*(دقيقة|دقيقه|دقايق|دقائق|ساعة|ساعه|ساعات|يوم|أيام|ايام)?", text)
    if not m:
        return 600
    n = int(m.group(1))
    unit = m.group(2) or "دقيقة"
    if "ساع" in unit:
        return n * 3600
    if "يوم" in unit:
        return n * 86400
    return n * 60


def inline_keyboard(buttons):
    return {"inline_keyboard": [[{"text": t, "callback_data": d} for t, d in row] for row in buttons]}


def _vote_message_text(s, threshold):
    counts = db.get_vote_counts(s["id"])
    return (f"💡 اقتراح #{s['id']} من {s['submitted_by_name']}:\n{s['content']}\n\n"
            f"✅ موافق: {counts['agree']}/{threshold}   |   ❌ غير موافق: {counts['disagree']}")


MAIN_MENU_KEYBOARD = {
    "keyboard": [
        ["📖 القصة", "💡 الاقتراحات"],
        ["🗳️ تصويت", "🏆 الترتيب"],
        ["🧑 الشخصيات", "🧠 ملخص"],
        ["✨ اقترح فكرة", "⭐ قيّم القصة"],
        ["🎯 تحدي كتابة", "❓ مساعدة"],
    ],
    "resize_keyboard": True,
}

# لإزالة لوحة الأزرار من واجهة الأعضاء بالكامل (بدل تفعيلها تلقائياً بكل رسالة)
REMOVE_KEYBOARD = {"remove_keyboard": True}


# ----------------------------------------------------------------
# أوامر عربية بدون "/"
# ----------------------------------------------------------------
ARABIC_ALIASES = [
    (["ابدأ"], "/start"),
    (["البداية"], "/start"),
    (["مساعدة"], "/help"),
    (["الأوامر"], "/help"),
    (["الاوامر"], "/help"),
    (["اخر", "فصل"], "/lastchapter"),
    (["آخر", "فصل"], "/lastchapter"),
    (["القصة"], "/story"),
    (["قصة", "جديدة"], "/newarc"),
    (["قصة"], "/story"),
    (["صدر", "القصة"], "/export"),
    (["تصدير"], "/export"),
    (["تصدير", "pdf"], "/exportpdf"),
    (["تصدير", "PDF"], "/exportpdf"),
    (["تنزيل", "القصة"], "/exportpdf"),
    (["ولد", "صورة"], "/genimage"),
    (["ولّد", "صورة"], "/genimage"),
    (["كتم"], "/mute"),
    (["الغاء", "الكتم"], "/unmute"),
    (["إلغاء", "الكتم"], "/unmute"),
    (["فك", "الكتم"], "/unmute"),
    (["طرد"], "/kick"),
    (["حظر"], "/ban"),
    (["فك", "الحظر"], "/unban"),
    (["الغاء", "الحظر"], "/unban"),
    (["قوانين"], "/rules"),
    (["القوانين"], "/rules"),
    (["قوانين", "القروب"], "/rules"),
    (["قوانين", "المجموعة"], "/rules"),
    (["انذار"], "/warn"),
    (["إنذار"], "/warn"),
    (["انذر"], "/warn"),
    (["أنذر"], "/warn"),
    (["سحب", "انذار"], "/unwarn"),
    (["سحب", "إنذار"], "/unwarn"),
    (["مسح", "انذارات"], "/resetwarnings"),
    (["مسح", "إنذارات"], "/resetwarnings"),
    (["مسح", "الانذارات"], "/resetwarnings"),
    (["مسح", "الإنذارات"], "/resetwarnings"),
    (["انذاراتي"], "/warnings"),
    (["إنذاراتي"], "/warnings"),
    (["انذاراته"], "/warnings"),
    (["إنذاراته"], "/warnings"),
    (["الانذارات"], "/warninglist"),
    (["الإنذارات"], "/warninglist"),
    (["قائمة", "الانذارات"], "/warninglist"),
    (["قائمة", "الإنذارات"], "/warninglist"),
    (["ثبت"], "/pin"),
    (["الغاء", "التثبيت"], "/unpin"),
    (["فك", "التثبيت"], "/unpin"),
    (["احذف"], "/delmsg"),
    (["امسح", "الكل"], "/clearall"),
    (["حذف", "الكل"], "/clearall"),
    (["مسح", "كل", "الرسائل"], "/clearall"),
    (["مسابقة"], "/trivia"),
    (["اقتباس"], "/quotegame"),
    (["خمن", "الاقتباس"], "/quotegame"),
    (["لعبة", "الاقتباس"], "/quotegame"),
    (["شخصيات", "الاقتباس"], "/quotecharacters"),
    (["اضافة", "اقتباس"], "/addquote"),
    (["إضافة", "اقتباس"], "/addquote"),
    (["اضف", "اقتباس"], "/addquote"),
    (["أضف", "اقتباس"], "/addquote"),
    (["حذف", "اقتباس"], "/deletequote"),
    (["احذف", "اقتباس"], "/deletequote"),
    (["خمن", "الشخصية"], "/guesscharacterphoto"),
    (["لعبة", "الصور"], "/guesscharacterphoto"),
    (["صور", "الشخصيات"], "/characterphotolist"),
    (["قائمة", "صور", "الشخصيات"], "/characterphotolist"),
    (["حذف", "صورة", "شخصية"], "/deletecharacterphoto"),
    (["احذف", "صورة", "شخصية"], "/deletecharacterphoto"),
    (["تغيير", "اسم", "شخصية"], "/renamecharacterphoto"),
    (["غير", "اسم", "شخصية"], "/renamecharacterphoto"),
    (["اضافة", "صورة", "شخصية"], "/addcharacterphoto"),
    (["إضافة", "صورة", "شخصية"], "/addcharacterphoto"),
    (["اضافة", "صورة", "وحش"], "/addmonsterphoto"),
    (["إضافة", "صورة", "وحش"], "/addmonsterphoto"),
    (["حذف", "صورة", "وحش"], "/deletemonsterphoto"),
    (["احذف", "صورة", "وحش"], "/deletemonsterphoto"),
    (["صور", "الوحوش"], "/monsterphotolist"),
    (["قائمة", "صور", "الوحوش"], "/monsterphotolist"),
    (["صدارة", "المسابقة"], "/trivialeaderboard"),
    (["نتيجة", "المسابقة"], "/trivialeaderboard"),
    (["العاب"], "/games"),
    (["ألعاب"], "/games"),
    (["بطولة"], "/tournament"),
    (["بطولة", "جديدة"], "/tournament"),
    (["الغاء", "البطولة"], "/canceltournament"),
    (["إلغاء", "البطولة"], "/canceltournament"),
    (["خمن", "الرقم"], "/guessnumber"),
    (["لعبة", "تخمين"], "/guessnumber"),
    (["تخمين", "الرقم"], "/guessnumber"),
    (["صراحة", "او", "تحدي"], "/truthdare"),
    (["صراحة", "أو", "تحدي"], "/truthdare"),
    (["صراحة"], "/truthdare"),
    (["انهاء", "اللعب"], "/endgame"),
    (["إنهاء", "اللعب"], "/endgame"),
    (["انهاء", "اللعبة"], "/endgame"),
    (["إنهاء", "اللعبة"], "/endgame"),
    (["انهي", "اللعبة"], "/endgame"),
    (["اكس", "او"], "/tictactoe"),
    (["إكس", "أو"], "/tictactoe"),
    (["اكس", "أو"], "/tictactoe"),
    (["إكس", "او"], "/tictactoe"),
    (["لعبة", "اكس", "او"], "/tictactoe"),
    (["الصندوق", "الذهبي"], "/connect4"),
    (["اربعة", "متتالية"], "/connect4"),
    (["أربعة", "متتالية"], "/connect4"),
    (["كونيكت", "فور"], "/connect4"),
    (["تحدي", "الصندوق"], "/connect4"),
    (["أوثيلو"], "/othello"),
    (["اوثيلو"], "/othello"),
    (["ريفيرسي"], "/othello"),
    (["لعبة", "أوثيلو"], "/othello"),
    (["لعبة", "اوثيلو"], "/othello"),
    (["الذاكرة"], "/memory"),
    (["ذاكرة"], "/memory"),
    (["لعبة", "الذاكرة"], "/memory"),
    (["ميموري"], "/memory"),
    (["ميموري", "ماتش"], "/memory"),
    (["عجلة"], "/wheel"),
    (["عجلة", "الاسماء"], "/wheel"),
    (["عجلة", "الأسماء"], "/wheel"),
    (["منافسة"], "/duel"),
    (["مين", "الاحسن"], "/duel"),
    (["مين", "الأحسن"], "/duel"),
    (["اسم", "القروب"], "/setgrouptitle"),
    (["اسم", "المجموعة"], "/setgrouptitle"),
    (["تغيير", "صورة", "القروب"], "/setgroupphoto"),
    (["غير", "صورة", "القروب"], "/setgroupphoto"),
    (["تغيير", "صورة", "المجموعة"], "/setgroupphoto"),
    (["قفل", "المحادثة"], "/lockchat"),
    (["قفل", "القروب"], "/lockchat"),
    (["فتح", "المحادثة"], "/unlockchat"),
    (["فتح", "القروب"], "/unlockchat"),
    (["نادي"], "/tag"),
    (["نادِ"], "/tag"),
    (["ناده"], "/tag"),
    (["طاق"], "/tagall"),
    (["تاق"], "/tagall"),
    (["@الكل"], "/tagall"),
    (["@all"], "/tagall"),
    (["استدعاء", "الجميع"], "/tagall"),
    (["نادي", "الجميع"], "/tagall"),
    (["نادِ", "الجميع"], "/tagall"),
    (["ملخص", "القصة"], "/summary"),
    (["ملخص"], "/summary"),
    (["اقترح", "فكرة"], "/ideas"),
    (["فكرة", "فصل"], "/ideas"),
    (["قيم", "القصة"], "/rate"),
    (["قيّم", "القصة"], "/rate"),
    (["تحدي", "كتابة"], "/challenge"),
    (["تحدي"], "/challenge"),
    (["بحث"], "/search"),
    (["اقترح"], "/suggest"),
    (["الاقتراحات"], "/suggestions"),
    (["اقتراحات"], "/suggestions"),
    (["تصويت"], "/pollvote"),
    (["استفتاء"], "/pollvote"),
    (["اعتماد"], "/approvesuggestion"),
    (["رفض"], "/rejectsuggestion"),
    (["لوحة", "التحكم"], "/adminpanel"),
    (["ازالة", "الازرار"], "/removekeyboard"),
    (["إزالة", "الأزرار"], "/removekeyboard"),
    (["حذف", "الازرار"], "/removekeyboard"),
    (["عدل", "اقتراح"], "/editsuggestion"),
    (["الغ", "اقتراح"], "/cancel"),
    (["الغاء", "اقتراح"], "/cancel"),
    (["حسن", "اقتراح"], "/improve"),
    (["اضف", "شخصية"], "/addcharacter"),
    (["اضافة", "شخصية"], "/addcharacter"),
    (["عدل", "شخصية"], "/editcharacter"),
    (["احذف", "شخصية"], "/deletecharacter"),
    (["شخصيتي", "رقم"], "/mycharacter"),
    (["شخصيتي"], "/mycharacter"),
    (["الشخصيات"], "/characters"),
    (["شخصيات"], "/characters"),
    (["الترتيب"], "/leaderboard"),
    (["ترتيب"], "/leaderboard"),
    (["احصائياتي"], "/mystats"),
    (["احصائيات"], "/mystats"),
    (["الأكثر", "تفاعلاً"], "/active"),
    (["الأكثر", "تفاعلا"], "/active"),
    (["الاكثر", "تفاعلا"], "/active"),
    (["الاكثر", "نشاطاً"], "/active"),
    (["الاكثر", "نشاطا"], "/active"),
    (["كنية"], "/nickname"),
    (["الغ", "كنية"], "/removenickname"),
    (["الغاء", "كنية"], "/removenickname"),
    (["حذف", "كنية"], "/removenickname"),
    (["صيرني", "ادمن"], "/makeadmin"),
    (["ضيف", "ادمن"], "/addadmin"),
    (["اضف", "ادمن"], "/addadmin"),
    (["احذف", "ادمن"], "/removeadmin"),
    (["ازالة", "ادمن"], "/removeadmin"),
    (["شيل", "ادمن"], "/removeadmin"),
    (["اطلب", "نزع"], "/requestremoveadmin"),
    (["طلب", "نزع"], "/requestremoveadmin"),
    (["اطلب", "نزع", "ادمن"], "/requestremoveadmin"),
    (["رتبتي"], "/myrank"),
    (["رتبة", "من"], "/myrank"),
    (["المشرفين"], "/adminlist"),
    (["قائمة", "المشرفين"], "/adminlist"),
    (["صلاحيات", "الرتب"], "/rankpermissions"),
    (["الرتب"], "/rankpermissions"),
    (["اضف", "فصل"], "/addchapterdirect"),
    (["اضافة", "فصل"], "/addchapterdirect"),
    (["عدل", "فصل"], "/editchapter"),
    (["احذف", "فصل"], "/deletechapter"),
    (["تراجع", "فصل"], "/undolastchapter"),
    (["اصوات", "التلقائي"], "/setautovotes"),
    (["غير", "الاصوات"], "/setautovotes"),
    (["نسيان", "المحادثة"], "/forgetchat"),
    (["انسي", "المحادثة"], "/forgetchat"),
    (["اذاعة"], "/broadcast"),
    (["اختبار", "الذكاء"], "/aitest"),
    (["تشخيص"], "/aitest"),
    (["افحص", "الاعدادات"], "/checkenv"),
    (["افحص", "الإعدادات"], "/checkenv"),
    (["الميزات"], "/features"),
    (["ادارة", "الميزات"], "/features"),
    (["إدارة", "الميزات"], "/features"),
    (["المحفوظات"], "/medialist"),
    (["احذف", "محفوظ"], "/deletemedia"),
]
ARABIC_ALIASES.sort(key=lambda item: -len(item[0]))


def _strip_leading_symbols(tokens):
    while tokens and not any(ch.isalpha() for ch in tokens[0]):
        tokens.pop(0)
    return tokens


def match_arabic_alias(text):
    raw_tokens = text.strip().split()
    tokens = _strip_leading_symbols(list(raw_tokens))
    if not tokens:
        return None
    for words, cmd in ARABIC_ALIASES:
        n = len(words)
        if len(tokens) < n:
            continue
        candidate = [t.strip("،.!؟:") for t in tokens[:n]]
        if candidate == words:
            rest = " ".join(tokens[n:])
            return cmd, rest
    return None


PUBLIC_HELP_SECTIONS = [
    ("💬 سيزار (الشخصية الذكية)", [
        "نادِ على \"سيزار\" بأي رسالة وبيرد عليك ويتذكر آخر كلامكم فعلياً — محادثة حقيقية متواصلة.",
        "أرسل صورة بكابشن فيه \"سيزار\" وبيوصفها لك (بدون كابشن يذكره، يتجاهلها).",
        "نادِ على سيزار مع كلمة \"صوت\" وبيرد عليك برسالة صوتية بدل نص.",
    ]),
    ("🎮 الألعاب", [
        "العاب - قائمة كل الألعاب بأزرار سريعة",
        "مسابقة - سؤال ثقافة عامة جماعي (AI) | صدارة المسابقة - لوحة صدارة دائمة",
        "خمن الرقم - يظهر لوحة أرقام (1-20)، اضغطوا رقمكم وسيزار يقول أعلى/أقل بردّ خاص",
        "صراحة - سؤال صراحة أو تحدي عشوائي بضغطة زر، ردّوا على رسالته وسيزار يتفاعل معكم",
        "اقتباس - يعرض شخصية أنمي (وصورتها لو محفوظة) و3 مقولات، خمّنوا مقولتها الأصلية",
        "شخصيات الاقتباس - قائمة كل الشخصيات (الأساسية + المضافة بأرقامها) عشان تحفظي صورهم",
        "خمن الشخصية - يرسل صورة شخصية عشوائية من مكتبة اللعبة، اكتبوا الاسم مباشرة، أول إجابة صح تاخذ نقاط",
        "صور الشخصيات - قائمة كل الصور المضافة للعبة بأرقامها",
        "اكس او - إكس-أو بين لاعبين، أول ضاغط X وأول عضو ثاني يضغط يصير O، تبادل أدوار حقيقي",
        "أربعة متتالية - Connect 4 بين لاعبين، اختر عمود وتسقط قطعتك فيه، أول 4 متتالية يفوز",
        "أوثيلو - أوثيلو/ريفيرسي بين لاعبين، شبكة 8×8، حاصر أقراص الخصم لتقلبها للونك",
        "لعبة الذاكرة - Memory Match بين لاعبين، شبكة 4×4، افتحوا بطاقتين بدوركم وطابقوا الصور",
        "عجلة اسم1 اسم2 اسم3... - يظهر زر «دوران»، كل ضغطة تختار اسم عشوائي من القائمة",
        "منافسة شي1 مقابل شي2 - يظهر زرين، كل عضو يصوّت لواحد منهم والعداد يتحدث لحظياً",
        "بطولة - (أدمن يبدأها) اختر عدد المشاركين واللعبة (إكس-أو/أربعة متتالية/حظ/عشوائي)، "
        "أي عضو ينضم بزر «انضم»، وشجرة إقصاء تلقائية لحد ما يطلع بطل واحد بنقاط إضافية",
        "الغاء البطولة - (أدمن) يلغي البطولة النشطة",
        "انهاء اللعب - ينهي أي لعبة نشطة (وأي بطولة) ويمسح رسائلها",
    ]),
    ("📖 القصة", [
        "قصة - عرض القصة كاملة | آخر فصل - عرض أحدث فصل فقط",
        "تصدير - نسخة نصية بالمحادثة | تصدير PDF - ملف PDF منسّق للتنزيل",
        "بحث كلمة - بحث داخل القصة",
        "ملخص - ملخص ذكي (AI) | اقترح فكرة - فكرة للفصل القادم",
        "قيّم القصة - تقييم سيزار من 10 | تحدي كتابة - تحدي إبداعي جديد",
    ]),
    ("💡 الاقتراحات والتصويت", [
        "اقترح نص - قدّم اقتراح | الاقتراحات - عرض القائمة",
        "تصويت - زر «صوّت» حي لكل اقتراح (صوت واحد للشخص)، يُعتمد ويُحذف تلقائياً عند اكتمال العدد "
        "(أو: تصويت رقم لاقتراح محدد)",
        "عدل اقتراح رقم نص_جديد | الغ اقتراح رقم",
        "حسن اقتراح رقم - تحسين الصياغة بالذكاء الاصطناعي",
    ]),
    ("🧑 الشخصيات والإحصائيات", [
        "اضف شخصية اسم - وصف | عدل شخصية رقم اسم - وصف | احذف شخصية رقم (أدمن)",
        "الشخصيات - عرض الكل | شخصيتي رقم - اربط نفسك بشخصية بالقصة",
        "الترتيب - الأكثر مساهمة | احصائياتي - إحصائياتك",
        "الأكثر تفاعلاً - أنشط أعضاء المجموعة برسائلهم",
        "بطاقة (أو: بروفايل) - بطاقة تعريف تعرض اليوزر والآيدي واللقب وعدد رسائلك وبايوك + صورتك "
        "(رد على شخص بنفس الأمر لعرض بطاقته هو بدلك)",
    ]),
    ("🖼️ صور من الإنترنت", [
        "ولد صورة وصف (أو: ولّد صورة وصف) - يجيب صورة حقيقية من الإنترنت تطابق الوصف "
        "(بحث صور عام، مو رسم بالذكاء الاصطناعي)",
    ]),
    ("🎞️ الوسائط المحفوظة", [
        "بس اكتب اسم أي عنصر محفوظ (بأي رسالة) وسيزار يرسله فوراً — متاحة لكل الأعضاء",
    ]),
    ("📞 تواصل مع الإدارة", [
        "تواصل نص_رسالتك - يوصل المسؤول مباشرة برسالة خاصة، ويرد عليك من هناك",
    ]),
    ("🗒️ قوانين المجموعة والإنذارات", [
        "قوانين - عرض قوانين المجموعة كاملة",
        "انذاراتي - عدد إنذاراتك الحالية (أو رد على شخص لعرض إنذاراته)",
        "الانذارات - قائمة كل من عنده إنذار حالياً (أدمن)",
    ]),
    ("🎖️ نظام رتب الإشراف (3 رتب)", [
        "صيرني ادمن - أول شخص يكتبها بمجموعة بلا أدمن يصير 🥇 مشرف عام مباشرة",
        "رتبتي - عرض رتبتك الحالية (أو رد على شخص لعرض رتبته)",
        "المشرفين - قائمة كل مشرفي المجموعة ورتبهم",
        "صلاحيات الرتب - شرح كامل لصلاحيات كل رتبة",
        "اطلب نزع - (رد على مشرف) يرسل طلب نزع رتبته لمالك البوت للموافقة "
        "(منح ونزع الرتب مباشرة حصراً لمالك البوت)",
    ]),
    ("👮 أوامر الإدارة العامة (أدمن)", [
        "صيرني ادمن | ضيف ادمن (رد على شخص) | لوحة التحكم - قائمة أزرار سريعة",
        "اعتماد رقم | رفض رقم - قرار سريع باقتراح دون انتظار التصويت",
        "اضف فصل نص | عدل فصل رقم نص_جديد | احذف فصل رقم | تراجع فصل - يحذف آخر فصل مباشرة",
        "قصة جديدة - يبدأ خطاً سردياً جديداً (القديم يبقى بالتصدير)",
        "نسيان المحادثة - يمسح ذاكرة سيزار بهذي المجموعة",
        "نادي (رد على شخص) - ينده بالمحادثة",
        "طاق (أو: @الكل / استدعاء الجميع) - ينادي كل الأعضاء المسجّلين لدى البوت بهذي المجموعة",
        "اختبار الذكاء / تشخيص - يفحص الاتصال بـ Gemini بالتفصيل",
        "افحص الاعدادات - يتأكد من ضبط المفاتيح على الاستضافة",
    ]),
    ("⚔️ نظام الصيادين", [
        "بطاقتي (أو: حالتي) - نافذة حالة الصياد: الرتبة، المستوى، الإحصائيات، المعدات، جيش الظلال",
        "الصيادين - لوحة صدارة الصيادين بالمجموعة",
        "بوابة - قتال حي متعدد الجولات: صورة الوحش + شريط صحته وصحتك، 4 قرارات كل جولة "
        "(هجوم/تفادي/فحص لكشف نقطة ضعف/انسحاب)، يعطي XP ومعدات وأحياناً ظل تابع",
        "توزيع الإحصائية العدد - يوزّع نقاط ترقية المستوى (مثال: توزيع قوة 2)",
        "حقيبتي - عرض المعدات المملوكة | تجهيز الرقم - يجهّز عنصر",
        "متجر - عرض متجر المعدات | شراء الرقم - شراء عنصر بالنقاط",
        "جيشي - عرض جيش الظلال المستخرج من البوابات",
        "غارة - (أدمن) يبدأ بوس جماعي تتعاون عليه المجموعة كلها",
        "هجوم - هجمة على الغارة النشطة (كل صياد له تبريد بين الهجمات)",
        "صور الوحوش - (المالك) قائمة صور وحوش البوابات المضافة والناقصة",
    ]),
    ("🎴 درافت الأنمي", [
        "درافت - يبدأ لعبة درافت: اختر فئة الأنمي (جوجيتسو كايسن / قاتل الشياطين / سولو لفلينج)",
        "بعد الاختيار: عضو ثاني يضغط «🙋 انضم» ليبدأ التحدي",
        "كل دور: بطاقة ظاهرة معروفة - تاخذها بضغطة، أو تجازف بسحب مخفي عشوائي",
        "لو جازفت بالمخفي: البطاقة الظاهرة اللي رفضتها تروح مجاناً للخصم!",
        "كل لاعب يجمع 4 شخصيات من نفس الأنمي، وبعدها Gemini يحكم أي فريق أقوى بدقة ويوزّع النقاط",
    ]),
    ("👑 خاص بالأدمن", [
        "كنية الكنية_الجديدة - (كرد على رسالة العضو) يضبط كنية يعتمدها سيزار بنداءه وقوائمه",
        "الغ كنية - (كرد على رسالته) يشيل كنية العضو ويرجّع اسمه الأصلي",
    ]),
]


def _public_help_plain_text():
    """نص احتياطي (لو مكتبات/خط الـ PDF مو جاهزة على الاستضافة) — نفس محتوى الدليل كنص عادي."""
    lines = ["📖 بوت الرواية الجماعية — سيزار",
             "تقدر تكتب أي أمر بـ / أو بالعربي مباشرة (مثلاً: \"قصة\" بدل /story).\n"]
    for title, section_lines in PUBLIC_HELP_SECTIONS:
        lines.append(title)
        lines.extend(section_lines)
        lines.append("")
    return "\n".join(lines).strip()


def _send_help(chat_id):
    ready, _ = pdf_export.pdf_ready()
    if ready:
        send_chat_action(chat_id, "upload_document")
        ok, result = pdf_export.build_generic_text_pdf("📖 دليل أوامر سيزار", PUBLIC_HELP_SECTIONS)
        if ok:
            sent = send_document(chat_id, result, "دليل_اوامر_سيزار.pdf", caption="📖 دليل كل أوامر سيزار")
            if sent:
                return
    # احتياط: لو الـ PDF مو جاهز أو فشل الإرسال، نرسل نفس المحتوى كنص عادي بدل ما نترك المستخدم بدون شي
    send_message(chat_id, _public_help_plain_text())


# ----------------------------------------------------------------
# 👑 دليل أوامر المالك — مجمّع كامل، يظهر فقط بالخاص وللمالك (MASTER_ADMIN_IDS).
# التوثيق للمالك نفسه، ما يظهر أبداً بدليل الأوامر العام (PDF) ولا لأي عضو آخر.
# ----------------------------------------------------------------
OWNER_COMMANDS_TEXT = (
    "👑 <b>دليل أوامر المالك الكامل</b> (يظهر لك أنت فقط، من الخاص)\n\n"

    "🔒 <b>تحكم كامل بأي مجموعة (رد على شخص داخل المجموعة)</b>\n"
    "أنت (المالك) دايماً برتبة 🥇 مشرف عام تلقائياً بكل مجموعة — الأوامر التالية صارت متاحة أيضاً "
    "لمشرفي المجموعة حسب رتبتهم (راجع «🎖️ نظام رتب الإشراف» تحت):\n"
    "كتم / الغاء الكتم (بمدة: كتم 10 دقايق / ساعة / يوم / دائم) — رتبة 1+\n"
    "طرد — رتبة 2+ | حظر / فك الحظر — رتبة 3+\n"
    "ثبت / الغاء التثبيت (رد على رسالة) | احذف (رد على رسالة) — رتبة 1+\n"
    "امسح الكل - يحذف كل الرسائل الأخيرة دفعة وحدة — رتبة 3+\n"
    "قفل المحادثة / فتح المحادثة — رتبة 3+\n"
    "اسم القروب اسم_جديد | تغيير صورة القروب (رد على صورة) — لك أنت فقط\n"
    "اصوات التلقائي رقم | اذاعة نص (لكل المجموعات) — لك أنت فقط\n\n"

    "🎖️ <b>نظام رتب الإشراف الثلاث (فوق أي مجموعة)</b>\n"
    "منح ونزع رتب الإشراف مباشرة حصراً لك أنت (المالك) — ولا حد ثاني (حتى 🥇 مشرف عام) يقدر يمنح "
    "أو ينزع رتبة بنفسه:\n"
    "ضيف ادمن [1/2/3] (رد على شخص) - يمنحه رتبة (افتراضياً 1 لو ما حددت رقم)\n"
    "احذف ادمن (رد على مشرف) - ينزع رتبته مباشرة\n"
    "أي مشرف (أي رتبة) يقدر بس يقدّم طلب نزع لمشرف ثاني وينتظر موافقتك: اطلب نزع (رد على المشرف) "
    "— توصلك رسالة فيها زر ✅ وافق / ❌ ارفض\n"
    "المشرفين - قائمة كل مشرفي المجموعة ورتبهم | صلاحيات الرتب - شرح كامل لصلاحيات كل رتبة\n\n"

    "⚙️ <b>الميزات والمحفوظات</b>\n"
    "الميزات - تفعيل/تعطيل أي ميزة بكل مجموعات البوت بأزرار\n"
    "احفظ باسم اسم - كابشن على صورة/فيديو لحفظه بالمكتبة (أضف | نص بعد الاسم "
    "عشان يظهر نص مرافق مع الفيديو/الصورة دايماً، مثال: احفظ باسم يوسف | فيديو "
    "يوسف الأسطوري 🔥). يظهر تلقائياً لأي عضو لو ذكر نفس الاسم بأي مكان من رسالته.\n"
    "المحفوظات - عرض كل الأسماء المحفوظة | احذف محفوظ اسم\n\n"

    "🎭 <b>إدارة لعبة الاقتباس</b>\n"
    "اضافة اقتباس الشخصية | الأنمي | نص المقولة\n"
    "حذف اقتباس #الرقم (أو: اسم_الشخصية) | شخصيات الاقتباس - عرض الأرقام\n"
    "احفظ باسم اسم_الشخصية - صورة لها | احذف محفوظ اسم_الشخصية\n\n"

    "🖼️ <b>إدارة لعبة خمن الشخصية</b>\n"
    "اضافة صورة شخصية الاسم (أو: الاسم | الأنمي)\n"
    "حذف صورة شخصية #الرقم (أو: اسم_الشخصية) | تغيير اسم شخصية #الرقم الاسم_الجديد\n\n"

    "🛰️ <b>لوحة التحكم عبر الخاص (خاص بالمالك — دي إم فقط)</b>\n"
    "لوحة المالك - قائمة أزرار رئيسية لكل شي تحت\n"
    "رابط اضافة سيزار (أو زر ➕ من لوحة المالك) - رابط رسمي يضيف سيزار مباشرة لأي مجموعة تختارها، بصلاحيات أدمن مقترحة تلقائياً\n"
    "قائمة المجموعات - كل مجموعة (اسم + عدد أعضاء)، وزر لإدارة كل وحدة\n"
    "من داخل كل مجموعة: تعطيل/تفعيل ميزة خاصة فيها فقط، رقّني أدمن هنا، رابط دعوة، إخراج البوت منها\n"
    "اخرج من مجموعة معرف_المجموعة - خروج فوري بأمر نصي مباشر\n"
    "رقني ادمن معرف_المجموعة - ترقيتك أدمن فيها مباشرة\n"
    "ضيف عضو معرف_المجموعة [آيدي_العضو] - رابط دعوة، أو إرسال مباشر لو العضو بدأ محادثة مع البوت\n"
    "سجل التنبيهات - كل محاولات إزالة البوت أو تقليص صلاحياته (تلقائي وفوري لحظة حدوثها)\n"
    "نسخة احتياطية (أو زر 💾 من لوحة المالك) - يجمع كل ملفات البوت + قاعدة البيانات بملف ZIP "
    "ويرسله لك فوراً بالخاص. تلقائياً أيضاً كل BACKUP_INTERVAL_DAYS يوم (افتراضياً 15) لو ضبطت "
    "BACKUP_SECRET وربطت /backup_check بمهمة مجدولة يومية، بنفس فكرة /weekly_check\n\n"

    "💌 <b>تواصل الأعضاء معك</b>\n"
    "أي عضو يكتب: تواصل نص_رسالته (من الخاص أو من أي مجموعة) - توصلك الرسالة فوراً "
    "بالخاص، فيها اسمه ويوزره وآيديه\n"
    "رسائل تواصل (أو زر 💌 من لوحة المالك) - آخر 15 رسالة تواصل وصلتك\n"
    "رد للمستخدم آيدي_العضو نص_الرد - يرسل ردك مباشرة لذاك العضو بالخاص "
    "(لازم يكون بدأ محادثة مع البوت من قبل)\n\n"

    "🕵️ <b>من يستخدم سيزار (خاص/مجموعات) + تعطيل شخص أو مجموعة محددة</b>\n"
    "من يستخدم سيزار الخاص (أو زر 🕵️ من لوحة المالك) - كل شخص استخدم سيزار بالخاص، "
    "بالاسم واليوزر والآيدي، وزر بجانب كل واحد لتعطيل/تفعيل سيزار له بالتحديد\n"
    "من يستخدم سيزار بالمجموعات (أو زر 👥 من لوحة المالك) - كل مجموعة استُخدم فيها سيزار، "
    "وزر بجانب كل مجموعة لتعطيل/تفعيل سيزار فيها بالتحديد\n"
)

# ----------------------------------------------------------------
# 👑 لوحة تحكم المالك عبر الخاص — أوامر شفافة لكنها غير معلنة بقائمة المساعدة
# العامة (لا تظهر بـ HELP_TEXT). كل شي هنا محصور بـ MASTER_ADMIN_IDS فقط.
# تسمح للمالك يتحكم بأي مجموعة البوت فيها من محادثته الخاصة مع سيزار مباشرة:
# عرض المجموعات، تعطيل/تفعيل ميزة بمجموعة محددة، إخراج البوت منها فوراً،
# ترقية نفسه أدمن فيها مباشرة، وإنشاء رابط دعوة لإضافة عضو.
# ----------------------------------------------------------------

def _is_master(user_id):
    return user_id in MASTER_ADMIN_IDS


def _is_private_chat(chat_id):
    """آيدي الدردشات الخاصة بتلغرام دائماً موجب، والمجموعات/السوبرقروبات دائماً سالب."""
    return chat_id > 0


def _owner_only_guard(chat_id, user_id):
    """يتحقق إن المستخدم مالك البوت وإنه يكتب من الخاص. يرجع True لو مسموح، وإلا يرسل رفض ويرجع False."""
    if not _is_master(user_id):
        send_message(chat_id, "هذا الأمر لمالك البوت فقط.")
        return False
    if not _is_private_chat(chat_id):
        send_message(chat_id, "هذا الأمر يشتغل من خاص البوت فقط، مو من داخل المجموعة.")
        return False
    return True


def _owner_main_menu_keyboard():
    return inline_keyboard([
        [("📋 قائمة المجموعات", "own_groups")],
        [("➕ رابط إضافة سيزار لمجموعة جديدة", "own_addlink")],
        [("📜 كل أوامر المالك (دليل نصي)", "own_cmds")],
        [("🔔 سجل التنبيهات الأمنية", "own_alerts")],
        [("💌 رسائل تواصل الأعضاء", "own_contacts")],
        [("🕵️ من يستخدم سيزار - الخاص", "own_riodm")],
        [("👥 من يستخدم سيزار - المجموعات", "own_riogroups")],
        [("⚙️ الميزات العامة للبوت", "own_globalfeat")],
        [("🕐 الوقت الحي وضبط المنطقة الزمنية", "own_time")],
        [("🧠 نماذج Gemini والاستهلاك", "own_models")],
        [("🎵 خدمة الأغاني (يوتيوب)", "own_ytsvc")],
        [("💾 نسخة احتياطية الآن", "own_backup")],
    ])


# ----------------------------------------------------------------
# 💾 نسخة احتياطية تلقائية — تُجمّع كل ملفات الكود + قاعدة البيانات الحالية
# بملف ZIP وتُرسل لكل مالكي البوت (MASTER_ADMIN_IDS) بالخاص، إما تلقائياً كل
# BACKUP_INTERVAL_DAYS يوم (عبر /backup_check المجدولة بـapp.py) أو فوراً عند
# طلب المالك من لوحة التحكم (زر "نسخة احتياطية الآن").
# ----------------------------------------------------------------
def backup_due():
    """يتحقق هل مرّت BACKUP_INTERVAL_DAYS يوم من آخر نسخة احتياطية مُرسلة (أو ما فيه أي نسخة بعد)."""
    last = db.get_last_backup_at()
    if not last:
        return True
    try:
        last_dt = datetime.datetime.fromisoformat(last)
    except ValueError:
        return True
    return (datetime.datetime.utcnow() - last_dt).days >= BACKUP_INTERVAL_DAYS


def send_backup_now(reason="يدوية (من لوحة المالك)"):
    """يبني نسخة ZIP فوراً ويرسلها لكل مالكي البوت. يرجع عدد المالكين اللي وصلتهم فعلاً."""
    ok, result = backup_export.build_backup_zip()
    if not ok:
        for admin_id in MASTER_ADMIN_IDS:
            send_message(admin_id, f"⚠️ فشلت النسخة الاحتياطية ({reason}):\n{result}")
        return 0

    filename = backup_export.backup_filename()
    caption = f"💾 نسخة احتياطية كاملة لملفات البوت — {reason}"
    sent = 0
    for admin_id in MASTER_ADMIN_IDS:
        if send_document_bytes(admin_id, result, filename, "application/zip", caption=caption):
            sent += 1
    if sent:
        db.set_last_backup_at(datetime.datetime.utcnow().isoformat())
    return sent


def _owner_main_menu_text():
    return ("👑 لوحة تحكم المالك\n\n"
            "من هنا تقدر تتحكم بأي مجموعة البوت فيها مباشرة من الخاص:\n"
            "تعطيل/تفعيل ميزة بمجموعة محددة، إخراج البوت من مجموعة، ترقية "
            "نفسك أدمن فيها، أو إنشاء رابط دعوة لإضافة عضو.")


def _group_display_name(chat_id, title):
    count = get_chat_member_count(chat_id)
    count_txt = f"{count} عضو" if count is not None else "عدد غير معروف"
    return f"{title or chat_id} — {count_txt}"


def _owner_groups_message():
    groups = db.get_known_groups()
    if not groups:
        return "🚫 ما فيه أي مجموعة مسجّلة لدى البوت حالياً.", inline_keyboard(
            [[("🔙 رجوع", "own_menu")]])
    lines = ["📋 المجموعات اللي سيزار فيها حالياً (الاسم وعدد الأعضاء):\n"]
    buttons = []
    for g in groups:
        label = _group_display_name(g["chat_id"], g["title"])
        lines.append(f"• {label}")
        short_title = (g["title"] or str(g["chat_id"]))[:28]
        buttons.append([(f"⚙️ {short_title}", f"own_g:{g['chat_id']}")])
    buttons.append([("🔙 رجوع", "own_menu")])
    return "\n".join(lines), inline_keyboard(buttons)


def _owner_group_detail(chat_id):
    info = get_chat(chat_id)
    title = info.get("title") if info else str(chat_id)
    count = get_chat_member_count(chat_id)
    count_txt = f"{count} عضو" if count is not None else "غير معروف"
    text = (f"⚙️ إدارة المجموعة: {title}\n"
            f"عدد الأعضاء: {count_txt}\n"
            f"معرّف المجموعة: {chat_id}")
    kb = inline_keyboard([
        [("🧩 ميزات هذي المجموعة فقط", f"own_gf:{chat_id}")],
        [("👑 رقّني أدمن هنا", f"own_promote:{chat_id}")],
        [("🔗 رابط دعوة لإضافة عضو", f"own_invite:{chat_id}")],
        [("🚪 إخراج البوت من المجموعة", f"own_leave:{chat_id}")],
        [("🔙 رجوع لقائمة المجموعات", "own_groups")],
    ])
    return text, kb


def _owner_group_features_keyboard(chat_id):
    overrides = db.get_chat_feature_overrides(chat_id)
    global_states = db.get_all_feature_states(FEATURE_LABELS.keys())
    buttons = []
    for key, label in FEATURE_LABELS.items():
        if key in overrides:
            enabled = overrides[key]
            icon = "✅" if enabled else "🚫"
            suffix = " (تخصيص خاص)"
        else:
            enabled = global_states[key]
            icon = "✅" if enabled else "🚫"
            suffix = ""
        buttons.append([(f"{icon} {label}{suffix}", f"own_ft:{chat_id}:{key}")])
    buttons.append([("♻️ إلغاء كل التخصيصات الخاصة", f"own_ftreset:{chat_id}")])
    buttons.append([("🔙 رجوع", f"own_g:{chat_id}")])
    return inline_keyboard(buttons)


def _bot_add_to_group_link():
    """
    يبني رابط تلغرام الرسمي يفتح للمالك قائمة مجموعاته يختار منها وحدة، ويضيف
    سيزار لها مباشرة (مع اقتراح صلاحيات أدمن كاملة تلقائياً). يرجع None لو getMe فشل.
    """
    me = get_me()
    if not me or not me.get("username"):
        return None
    admin_rights = ("change_info,delete_messages,invite_users,restrict_members,"
                     "pin_messages,promote_members,manage_chat,manage_video_chats")
    return f"https://t.me/{me['username']}?startgroup=owner&admin={admin_rights}"


def _owner_alerts_text():
    rows = db.get_recent_owner_alerts(15)
    if not rows:
        return "✅ ما فيه أي تنبيهات أمنية مسجّلة — لا محاولة إزالة ولا تغيير صلاحيات."
    lines = ["🔔 آخر التنبيهات الأمنية (محاولات إزالة البوت أو تغيير صلاحياته):\n"]
    for r in rows:
        lines.append(f"• {r['created_at']} — {r['chat_title'] or r['chat_id']}\n   {r['detail']}")
    return "\n".join(lines)


def _owner_contacts_text():
    rows = db.get_recent_contact_messages(15)
    if not rows:
        return "📭 ما وصل أي رسالة تواصل من الأعضاء لين الحين."
    lines = ["💌 آخر رسائل تواصل الأعضاء (الأحدث أولاً):\n"]
    for r in rows:
        uname = f"@{r['username']}" if r["username"] else "بدون يوزرنيم"
        origin = r["origin_chat_title"] or str(r["origin_chat_id"])
        lines.append(f"• {r['created_at']}\n"
                     f"   {r['first_name'] or 'مستخدم'} ({uname}) — آيدي {r['user_id']} — من: {origin}\n"
                     f"   ✉️ {r['message_text']}\n"
                     f"   للرد: رد للمستخدم {r['user_id']} نص_الرد")
    return "\n".join(lines)


def _persona_toggle_line(chat_id, label, callback_action):
    """يبني سطر زر تفعيل/تعطيل سيزار لشخص أو مجموعة محددة، بحسب حالة التخصيص الحالية."""
    overrides = db.get_chat_feature_overrides(chat_id)
    blocked = overrides.get("persona_chat") is False
    icon = "🚫 مُعطَّل — اضغط للتفعيل" if blocked else "✅ مفعّل — اضغط للتعطيل"
    return [(f"{icon} | {label}", f"{callback_action}:{chat_id}")]


def _owner_riodm_message():
    rows = db.get_persona_dm_usage(30)
    if not rows:
        return "🚫 ما فيه أي شخص استخدم سيزار بالخاص لين الحين.", inline_keyboard(
            [[("🔙 رجوع", "own_menu")]])
    lines = ["🕵️ من يستخدم سيزار بالخاص (الأحدث أولاً):\n"]
    buttons = []
    for r in rows:
        name = r["first_name"] or "مستخدم"
        uname = f"@{r['username']}" if r["username"] else "بدون يوزرنيم"
        lines.append(f"• {name} ({uname}) — آيدي {r['user_id']} — {r['use_count']} رسالة، "
                      f"آخر مرة {r['last_used_at']}")
        short_label = f"{name} ({uname})"[:35]
        buttons.append(_persona_toggle_line(r["user_id"], short_label, "own_riodm_t"))
    buttons.append([("🔙 رجوع", "own_menu")])
    return "\n".join(lines), inline_keyboard(buttons)


def _owner_riogroups_message():
    rows = db.get_persona_group_usage(30)
    if not rows:
        return "🚫 ما فيه أي مجموعة استُخدم فيها سيزار لين الحين.", inline_keyboard(
            [[("🔙 رجوع", "own_menu")]])
    lines = ["👥 المجموعات اللي يستخدمون فيها سيزار (الأحدث أولاً):\n"]
    buttons = []
    for r in rows:
        info = get_chat(r["chat_id"])
        title = info.get("title") if info else str(r["chat_id"])
        lines.append(f"• {title} — {r['user_count']} مستخدم، {r['total_uses']} رسالة إجمالاً، "
                      f"آخر مرة {r['last_used_at']}")
        short_title = (title or str(r["chat_id"]))[:30]
        buttons.append(_persona_toggle_line(r["chat_id"], short_title, "own_riogrp_t"))
    buttons.append([("🔙 رجوع", "own_menu")])
    return "\n".join(lines), inline_keyboard(buttons)


_ADMIN_PERMISSION_KEYS = [
    "can_manage_chat", "can_delete_messages", "can_manage_video_chats",
    "can_restrict_members", "can_promote_members", "can_change_info",
    "can_invite_users", "can_pin_messages",
]


def handle_my_chat_member_update(payload):
    """
    يُستدعى مع كل تحديث my_chat_member من تليجرام (تغيّرت عضوية/صلاحيات البوت
    نفسه بمجموعة). يسجّل بسجل التنبيهات الأمنية وينبّه كل مالكي البوت بالخاص
    فوراً لو صار شي يستدعي انتباه: طرد البوت، تقييده، أو تقليص صلاحياته كأدمن.
    """
    chat = payload.get("chat", {})
    chat_id = chat.get("id")
    chat_title = chat.get("title") or str(chat_id)
    actor = payload.get("from", {})
    actor_name = actor.get("first_name", "شخص غير معروف")
    actor_id = actor.get("id")
    old = payload.get("old_chat_member", {}) or {}
    new = payload.get("new_chat_member", {}) or {}
    old_status = old.get("status")
    new_status = new.get("status")

    detail = None
    event_type = None

    if new_status in ("left", "kicked"):
        verb = "طرد البوت" if new_status == "kicked" else "أخرج البوت"
        event_type = "bot_removed"
        detail = f"{actor_name} (آيدي {actor_id}) {verb} من المجموعة."

    elif new_status == "restricted":
        event_type = "bot_restricted"
        detail = f"{actor_name} (آيدي {actor_id}) قيّد صلاحيات البوت بالمجموعة."

    elif old_status == "administrator" and new_status == "member":
        event_type = "bot_demoted"
        detail = f"{actor_name} (آيدي {actor_id}) سحب صلاحية الأدمن من البوت."

    elif old_status == "administrator" and new_status == "administrator":
        lost = [k for k in _ADMIN_PERMISSION_KEYS if old.get(k) and not new.get(k)]
        if lost:
            event_type = "permissions_reduced"
            lost_txt = "، ".join(lost)
            detail = f"{actor_name} (آيدي {actor_id}) قلّص صلاحيات البوت: {lost_txt}."

    if not event_type:
        return  # تغييرات إيجابية أو محايدة (مثل ترقية البوت لأدمن) — لا تنبيه لازم

    db.log_owner_alert(chat_id, chat_title, event_type, detail)
    alert_text = f"🚨 تنبيه أمني بمجموعة «{chat_title}»:\n{detail}"
    for admin_id in MASTER_ADMIN_IDS:
        send_message(admin_id, alert_text)


def _handle_admin_removal_callback(data, chat_id, user_id, user_name, cq):
    """يعالج ضغط المالك على وافق/ارفض بطلب نزع رتبة إشراف مُقدَّم من أحد المشرفين."""
    cq_id = cq["id"]
    parts = data.split("_")
    action = parts[1]  # approve | reject
    req_id = int(parts[2])

    if user_id not in MASTER_ADMIN_IDS:
        answer_callback_query(cq_id, "🚫 هذا الإجراء لمالك البوت فقط.", show_alert=True)
        return

    req = db.get_removal_request(req_id)
    if not req:
        answer_callback_query(cq_id, "⚠️ الطلب غير موجود.", show_alert=True)
        return
    if req["status"] != "pending":
        answer_callback_query(cq_id, "ℹ️ تم البت بهذا الطلب مسبقاً.", show_alert=True)
        return

    if action == "approve":
        db.set_removal_request_status(req_id, "approved")
        db.remove_admin_rank(req["chat_id"], req["target_id"])
        answer_callback_query(cq_id, "✅ تم نزع الرتبة.")
        edit_message_text(chat_id, cq["message"]["message_id"],
                            f"✅ تمت الموافقة — تم نزع رتبة {req['target_name']}.")
        send_message(req["chat_id"], f"✅ تمت الموافقة على طلب {req['requester_name']} — "
                                       f"تم نزع رتبة الإشراف عن {req['target_name']}.")
    else:
        db.set_removal_request_status(req_id, "rejected")
        answer_callback_query(cq_id, "❌ تم رفض الطلب.")
        edit_message_text(chat_id, cq["message"]["message_id"],
                            f"❌ تم رفض طلب نزع رتبة {req['target_name']}.")
        send_message(req["chat_id"], f"❌ رفض المالك طلب {req['requester_name']} بنزع رتبة {req['target_name']}.")


def _handle_owner_panel_callback(data, chat_id, user_id, cq):
    """يعالج كل أزرار لوحة تحكم المالك (بادئة own_). محصور بـ MASTER_ADMIN_IDS فقط."""
    cq_id = cq["id"]
    message_id = cq["message"]["message_id"]

    if not _is_master(user_id):
        answer_callback_query(cq_id, "هذا الإجراء لمالك البوت فقط.", show_alert=True)
        return
    if not _is_private_chat(chat_id):
        answer_callback_query(cq_id, "هذا الإجراء يشتغل من خاص البوت فقط.", show_alert=True)
        return

    parts = data.split(":")
    action = parts[0]

    if action == "own_menu":
        answer_callback_query(cq_id)
        edit_message_text(chat_id, message_id, _owner_main_menu_text(), reply_markup=_owner_main_menu_keyboard())
        return

    if action == "own_groups":
        answer_callback_query(cq_id)
        text, kb = _owner_groups_message()
        edit_message_text(chat_id, message_id, text, reply_markup=kb)
        return

    if action == "own_g":
        target_id = int(parts[1])
        answer_callback_query(cq_id)
        text, kb = _owner_group_detail(target_id)
        edit_message_text(chat_id, message_id, text, reply_markup=kb)
        return

    if action == "own_gf":
        target_id = int(parts[1])
        answer_callback_query(cq_id)
        edit_message_text(chat_id, message_id, "🧩 ميزات هذي المجموعة فقط — اضغط لتبديل حالة أي ميزة:",
                            reply_markup=_owner_group_features_keyboard(target_id))
        return

    if action == "own_ft":
        target_id = int(parts[1])
        key = parts[2]
        if key not in FEATURE_LABELS:
            answer_callback_query(cq_id)
            return
        overrides = db.get_chat_feature_overrides(target_id)
        current = overrides.get(key, db.is_feature_enabled(key))
        new_state = not current
        db.set_chat_feature_override(target_id, key, new_state)
        answer_callback_query(cq_id, "✅ تم التفعيل لهذي المجموعة" if new_state else "🚫 تم التعطيل لهذي المجموعة")
        edit_message_text(chat_id, message_id, "🧩 ميزات هذي المجموعة فقط — اضغط لتبديل حالة أي ميزة:",
                            reply_markup=_owner_group_features_keyboard(target_id))
        return

    if action == "own_ftreset":
        target_id = int(parts[1])
        for key in FEATURE_LABELS:
            db.clear_chat_feature_override(target_id, key)
        answer_callback_query(cq_id, "♻️ رجعت كل الميزات لهذي المجموعة للحالة العامة للبوت.")
        edit_message_text(chat_id, message_id, "🧩 ميزات هذي المجموعة فقط — اضغط لتبديل حالة أي ميزة:",
                            reply_markup=_owner_group_features_keyboard(target_id))
        return

    if action == "own_globalfeat":
        answer_callback_query(cq_id)
        edit_message_text(chat_id, message_id, "⚙️ تفعيل/تعطيل الميزات لكل مجموعات البوت — اضغط لتبديل الحالة:",
                            reply_markup=_features_keyboard())
        return

    if action == "own_leave":
        target_id = int(parts[1])
        answer_callback_query(cq_id)
        info = get_chat(target_id)
        title = info.get("title") if info else str(target_id)
        edit_message_text(chat_id, message_id,
                            f"⚠️ متأكد تبي تخرج البوت من «{title}»؟ ما يرجع إلا لو تُدعى من جديد.",
                            reply_markup=inline_keyboard([
                                [("✅ تأكيد الخروج", f"own_leaveok:{target_id}")],
                                [("❌ إلغاء", f"own_g:{target_id}")],
                            ]))
        return

    if action == "own_leaveok":
        target_id = int(parts[1])
        if leave_chat(target_id):
            db.forget_known_chat(target_id)
            answer_callback_query(cq_id, "🚪 تم الخروج من المجموعة.")
            edit_message_text(chat_id, message_id, "🚪 تم إخراج البوت من المجموعة بنجاح.",
                                reply_markup=inline_keyboard([[("🔙 رجوع لقائمة المجموعات", "own_groups")]]))
        else:
            answer_callback_query(cq_id, "⚠️ ما قدرت أخرج منها.", show_alert=True)
        return

    if action == "own_promote":
        target_id = int(parts[1])
        if promote_chat_member(target_id, user_id):
            answer_callback_query(cq_id, "👑 تم ترقيتك أدمن كامل الصلاحيات بالمجموعة.", show_alert=True)
        else:
            answer_callback_query(
                cq_id, "⚠️ ما قدرت — تأكد إن البوت نفسه أدمن هناك بصلاحية تعيين أدمن.", show_alert=True)
        return

    if action == "own_invite":
        target_id = int(parts[1])
        link = create_chat_invite_link(target_id)
        if link:
            answer_callback_query(cq_id)
            send_message(chat_id, f"🔗 رابط دعوة لهذي المجموعة:\n{link}\n\n"
                                    "ترسله لأي عضو تبي تضيفه — أو استخدم أمر: ضيف عضو معرف_المجموعة آيدي_العضو "
                                    "لو العضو بدأ محادثة مع البوت من قبل، وبرسله له مباشرة بالخاص.")
        else:
            answer_callback_query(cq_id, "⚠️ ما قدرت أنشئ رابط دعوة — تأكد إن البوت أدمن بصلاحية دعوة أعضاء.",
                                    show_alert=True)
        return

    if action == "own_addlink":
        link = _bot_add_to_group_link()
        if link:
            answer_callback_query(cq_id)
            send_message(chat_id, "➕ اضغط الرابط، اختار المجموعة، وسيزار ينضم لها مباشرة "
                                    f"(مع اقتراح صلاحيات أدمن كاملة تلقائياً):\n{link}")
        else:
            answer_callback_query(cq_id, "⚠️ ما قدرت أجيب يوزر البوت — تأكد إن التوكن شغال.", show_alert=True)
        return

    if action == "own_time":
        answer_callback_query(cq_id)
        text, dt, tz_name = time_utils.default_now_text()
        buttons = [
            [("🇸🇦 السعودية", "own_tz:Asia/Riyadh"), ("🇦🇪 الإمارات", "own_tz:Asia/Dubai")],
            [("🇰🇼 الكويت", "own_tz:Asia/Kuwait"), ("🇶🇦 قطر", "own_tz:Asia/Qatar")],
            [("🇪🇬 مصر", "own_tz:Africa/Cairo"), ("🇯🇴 الأردن", "own_tz:Asia/Amman")],
            [("🔄 تحديث", "own_time")],
            [("🔙 رجوع", "own_menu")],
        ]
        edit_message_text(chat_id, message_id,
                            f"🕐 <b>الوقت الحي الحالي</b>\n\n"
                            f"المنطقة الزمنية المضبوطة: <code>{tz_name}</code>\n"
                            f"الوقت الآن فعلياً: {text}\n\n"
                            "سيزار يعتمد هذا الوقت الحقيقي بكل رد له. اختر منطقة زمنية "
                            "جديدة من الأزرار تحت لتغييرها، أو اضغط تحديث لتحديث العرض:",
                            reply_markup=inline_keyboard(buttons), parse_mode="HTML")
        return

    if action == "own_tz":
        tz_name = parts[1]
        if time_utils.set_default_timezone(tz_name):
            answer_callback_query(cq_id, f"✅ تم ضبط المنطقة الزمنية على {tz_name}.")
        else:
            answer_callback_query(cq_id, "⚠️ منطقة زمنية غير صالحة.", show_alert=True)
            return
        text, dt, tz_name = time_utils.default_now_text()
        buttons = [
            [("🇸🇦 السعودية", "own_tz:Asia/Riyadh"), ("🇦🇪 الإمارات", "own_tz:Asia/Dubai")],
            [("🇰🇼 الكويت", "own_tz:Asia/Kuwait"), ("🇶🇦 قطر", "own_tz:Asia/Qatar")],
            [("🇪🇬 مصر", "own_tz:Africa/Cairo"), ("🇯🇴 الأردن", "own_tz:Asia/Amman")],
            [("🔄 تحديث", "own_time")],
            [("🔙 رجوع", "own_menu")],
        ]
        edit_message_text(chat_id, message_id,
                            f"🕐 <b>الوقت الحي الحالي</b>\n\n"
                            f"المنطقة الزمنية المضبوطة: <code>{tz_name}</code>\n"
                            f"الوقت الآن فعلياً: {text}\n\n"
                            "سيزار يعتمد هذا الوقت الحقيقي بكل رد له. اختر منطقة زمنية "
                            "جديدة من الأزرار تحت لتغييرها، أو اضغط تحديث لتحديث العرض:",
                            reply_markup=inline_keyboard(buttons), parse_mode="HTML")
        return

    if action == "own_models":
        answer_callback_query(cq_id)
        edit_message_text(chat_id, message_id, _build_models_hud_text(), parse_mode="HTML",
                            reply_markup=inline_keyboard(_build_models_hud_buttons()))
        return

    if action == "own_setmodel":
        model_id = parts[1]
        if model_registry.set_active_model(model_id):
            answer_callback_query(cq_id, f"✅ تم التبديل إلى {model_id}.")
        else:
            answer_callback_query(cq_id, "⚠️ نموذج غير معروف.", show_alert=True)
            return
        edit_message_text(chat_id, message_id, _build_models_hud_text(), parse_mode="HTML",
                            reply_markup=inline_keyboard(_build_models_hud_buttons()))
        return

    if action == "own_ytsvc":
        answer_callback_query(cq_id)
        edit_message_text(chat_id, message_id, _build_ytsvc_status_text(), parse_mode="HTML",
                            reply_markup=inline_keyboard([
                                [("🔄 اختبار الاتصال الآن", "own_ytsvc_test")],
                                [("🔙 رجوع", "own_menu")],
                            ]))
        return

    if action == "own_ytsvc_test":
        answer_callback_query(cq_id, "⏳ جاري فحص الاتصال بالخدمة...")
        edit_message_text(chat_id, message_id, _build_ytsvc_status_text(testing=True), parse_mode="HTML",
                            reply_markup=inline_keyboard([
                                [("🔄 اختبار الاتصال الآن", "own_ytsvc_test")],
                                [("🔙 رجوع", "own_menu")],
                            ]))
        return

    if action == "own_backup":
        answer_callback_query(cq_id, "💾 جاري تجهيز النسخة الاحتياطية...")
        sent = send_backup_now(reason="يدوية (من لوحة المالك)")
        if sent:
            send_message(chat_id, f"✅ تم إرسال النسخة الاحتياطية لك ({sent} مالك).")
        else:
            send_message(chat_id, "⚠️ ما قدرت أرسل النسخة الاحتياطية — راجع الرسالة السابقة لتفاصيل الخطأ.")
        return

    if action == "own_cmds":
        answer_callback_query(cq_id)
        send_message(chat_id, OWNER_COMMANDS_TEXT, parse_mode="HTML")
        return

    if action == "own_alerts":
        answer_callback_query(cq_id)
        edit_message_text(chat_id, message_id, _owner_alerts_text(),
                            reply_markup=inline_keyboard([[("🔙 رجوع", "own_menu")]]))
        return

    if action == "own_contacts":
        answer_callback_query(cq_id)
        edit_message_text(chat_id, message_id, _owner_contacts_text(),
                            reply_markup=inline_keyboard([[("🔙 رجوع", "own_menu")]]))
        return

    if action == "own_riodm":
        answer_callback_query(cq_id)
        text, kb = _owner_riodm_message()
        edit_message_text(chat_id, message_id, text, reply_markup=kb)
        return

    if action == "own_riodm_t":
        target_id = int(parts[1])
        overrides = db.get_chat_feature_overrides(target_id)
        if overrides.get("persona_chat") is False:
            db.clear_chat_feature_override(target_id, "persona_chat")
            answer_callback_query(cq_id, "✅ تم تفعيل سيزار لهذا الشخص بالخاص.")
        else:
            db.set_chat_feature_override(target_id, "persona_chat", False)
            answer_callback_query(cq_id, "🚫 تم تعطيل سيزار لهذا الشخص بالخاص.")
        text, kb = _owner_riodm_message()
        edit_message_text(chat_id, message_id, text, reply_markup=kb)
        return

    if action == "own_riogroups":
        answer_callback_query(cq_id)
        text, kb = _owner_riogroups_message()
        edit_message_text(chat_id, message_id, text, reply_markup=kb)
        return

    if action == "own_riogrp_t":
        target_id = int(parts[1])
        overrides = db.get_chat_feature_overrides(target_id)
        if overrides.get("persona_chat") is False:
            db.clear_chat_feature_override(target_id, "persona_chat")
            answer_callback_query(cq_id, "✅ تم تفعيل سيزار بهذي المجموعة.")
        else:
            db.set_chat_feature_override(target_id, "persona_chat", False)
            answer_callback_query(cq_id, "🚫 تم تعطيل سيزار بهذي المجموعة.")
        text, kb = _owner_riogroups_message()
        edit_message_text(chat_id, message_id, text, reply_markup=kb)
        return

    answer_callback_query(cq_id)


def _profile_stast_label(chat_id, target_id, nickname):
    """يبني قيمة حقل STAST (اللقب/الحالة) لبطاقة التعريف: المالك > مشرف > الكنية المضبوطة > عضو عادي."""
    if target_id in MASTER_ADMIN_IDS:
        return "👑 المالك"
    if db.is_admin(chat_id, target_id, MASTER_ADMIN_IDS):
        return "🛡️ مشرف"
    if nickname:
        return nickname
    return "🙂 عضو"


def _send_profile_card(chat_id, target_id, target_name, target_username):
    """يبني ويرسل بطاقة تعريف لعضو: الاسم، اليوزر، الآيدي، اللقب، عدد الرسائل، والبايو + صورته لو متاحة."""
    row = db.get_user_row(chat_id, target_id)
    message_count = row["message_count"] if row and row["message_count"] else 0
    nickname = row["nickname"] if row else None

    chat_info = get_chat(target_id)
    bio = (chat_info.get("bio") if chat_info else None) or "."
    photo_id = None
    if chat_info and chat_info.get("photo"):
        photo_id = chat_info["photo"].get("big_file_id") or chat_info["photo"].get("small_file_id")

    username_txt = f"@{target_username}" if target_username else "بدون يوزرنيم"
    stast = _profile_stast_label(chat_id, target_id, nickname)

    caption = (
        f"{target_name}\n\n"
        f"-> USERNAME | {username_txt} .\n"
        f"-> ID | {target_id} .\n"
        f"-> STAST | {stast} .\n"
        f"-> MSGS | {message_count} .\n"
        f"-> bio | {bio} ."
    )

    if photo_id:
        sent = send_photo(chat_id, photo_id, caption=caption)
        if sent:
            return
    # ما فيه صورة بروفايل متاحة (أو فشل الإرسال) — نرسل نفس البطاقة كنص عادي
    send_message(chat_id, caption)


def handle_command(chat_id, user_id, user_name, text, reply_to_user=None, reply_to_message_id=None,
                    reply_to_photo=None, username=None):
    parts = text.strip().split(maxsplit=1)
    cmd = parts[0].split("@")[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    db.ensure_user(chat_id, user_id, user_name)

    feature_key = CMD_FEATURE_MAP.get(cmd)
    if feature_key and not db.is_feature_enabled(feature_key, chat_id):
        _feature_blocked_message(chat_id, feature_key)
        return

    if cmd in ("/start", "/help"):
        _send_help(chat_id)

    elif cmd == "/story":
        chapters = db.get_all_chapters(chat_id)
        if not chapters:
            send_message(chat_id, "لا توجد فصول بعد. ابدأ بـ «اقترح»!")
            return
        text_out = "\n\n".join(f"📖 الفصل {c['order_num']}:\n{c['content']}" for c in chapters)
        for i in range(0, len(text_out), 4000):
            send_message(chat_id, text_out[i:i + 4000])

    elif cmd == "/lastchapter":
        c = db.get_last_chapter(chat_id)
        if not c:
            send_message(chat_id, "لا توجد فصول بعد.")
            return
        send_message(chat_id, f"📖 آخر فصل ({c['order_num']}):\n{c['content']}")

    elif cmd == "/newarc":
        if not is_admin(chat_id, user_id):
            send_message(chat_id, "هذا الأمر للأدمن فقط.")
            return
        new_arc = db.start_new_arc(chat_id)
        send_message(chat_id, f"🌱 بدأنا خطاً سردياً جديداً (#{new_arc})! القصة السابقة محفوظة وتقدر تشوفها بـ «تصدير».")

    elif cmd == "/export":
        chapters = db.get_all_chapters(chat_id)
        if not chapters:
            send_message(chat_id, "لا توجد قصة بعد لتصديرها.")
            return
        text_out = "\n\n".join(f"الفصل {c['order_num']}\n{c['content']}" for c in chapters)
        # نرسل كملف نصي مباشرة بالرسالة إذا قصير، أو مجزأ إذا طويل (بدون الحاجة لملفات مؤقتة على القرص)
        send_message(chat_id, "📄 نسخة القصة:")
        for i in range(0, len(text_out), 4000):
            send_message(chat_id, text_out[i:i + 4000])

    elif cmd == "/exportpdf":
        chapters = db.get_all_chapters(chat_id)
        if not chapters:
            send_message(chat_id, "لا توجد قصة بعد لتصديرها.")
            return
        characters = db.get_characters(chat_id)
        send_chat_action(chat_id, "upload_document")
        ok, result = pdf_export.build_story_pdf("قصتنا الجماعية 📖", chapters, characters)
        if not ok:
            send_message(chat_id, f"⚠️ {result}")
            return
        sent = send_document(chat_id, result, "story.pdf", caption="📄 نسخة PDF من القصة")
        if not sent:
            send_message(chat_id, "⚠️ ما قدرت أرسل الملف، جرّب مرة ثانية.")

    elif cmd == "/search":
        if not arg:
            send_message(chat_id, "استخدم: بحث كلمة_البحث")
            return
        chapters = db.get_all_chapters(chat_id)
        matches = [c for c in chapters if arg in c["content"]]
        if not matches:
            send_message(chat_id, f"لا توجد نتائج لـ «{arg}»")
            return
        text_out = "\n\n".join(f"📖 الفصل {c['order_num']}:\n{c['content']}" for c in matches)
        send_message(chat_id, f"🔍 نتائج البحث عن «{arg}»:\n\n{text_out[:3800]}")

    elif cmd == "/summary":
        if not _cooldown_ok(user_id):
            return
        send_chat_action(chat_id)
        result = persona.ai_summarize_story(chat_id)
        if result is None:
            send_message(chat_id, "⚠️ ميزة الملخص الذكي غير مفعّلة حالياً (تحتاج مفتاح GEMINI_API_KEY).")
            return
        send_message(chat_id, f"🧠 ملخص القصة:\n\n{result}")

    elif cmd == "/ideas":
        if not _cooldown_ok(user_id):
            return
        send_chat_action(chat_id)
        idea = persona.ai_suggest_idea(chat_id)
        if idea is None:
            send_message(chat_id, "⚠️ ميزة اقتراح الأفكار غير مفعّلة حالياً (تحتاج مفتاح GEMINI_API_KEY).")
            return
        send_message(chat_id, f"✨ فكرة سيزار للفصل القادم:\n\n{idea}")

    elif cmd == "/rate":
        if not _cooldown_ok(user_id):
            return
        send_chat_action(chat_id)
        result = persona.ai_rate_story(chat_id)
        if result is None:
            send_message(chat_id, "⚠️ هذه الميزة تحتاج مفتاح GEMINI_API_KEY.")
            return
        send_message(chat_id, f"⭐ {result}")

    elif cmd == "/challenge":
        if not _cooldown_ok(user_id):
            return
        send_chat_action(chat_id)
        result = persona.ai_writing_challenge(chat_id)
        if result is None:
            send_message(chat_id, "⚠️ هذه الميزة تحتاج مفتاح GEMINI_API_KEY.")
            return
        send_message(chat_id, f"🎯 تحدي سيزار:\n\n{result}")

    elif cmd == "/suggest":
        if not arg:
            send_message(chat_id, "استخدم: اقترح نص اقتراحك لتطور القصة")
            return
        sid = db.add_suggestion(chat_id, arg, user_id, user_name)
        send_message(chat_id, f"✅ تم تسجيل اقتراحك #{sid}. شوف «الاقتراحات» للتصويت.")

    elif cmd == "/suggestions":
        pending = db.get_pending_suggestions(chat_id)
        if not pending:
            send_message(chat_id, "لا توجد اقتراحات حالياً. أضف واحد عبر «اقترح نص»")
            return
        lines = []
        for i, s in enumerate(pending):
            crown = "🥇 " if i == 0 and s["votes"] > 0 else ""
            lines.append(f"{crown}💡 #{s['id']} من {s['submitted_by_name']} (أصوات: {s['votes']}):\n{s['content']}")
        text_out = "\n\n".join(lines)
        send_message(chat_id, f"📋 الاقتراحات المعلقة (الأكثر تصويتاً أولاً):\n\n{text_out[:3800]}\n\n"
                                "صوّتوا عبر «تصويت» — صوت واحد لكل شخص 🗳️")
        if is_admin(chat_id, user_id):
            buttons = [[("✅ اعتماد #%d" % s["id"], f"approve_{s['id']}"),
                        ("❌ رفض #%d" % s["id"], f"reject_{s['id']}")] for s in pending]
            send_message(chat_id, "🛠 إجراء إداري سريع:", reply_markup=inline_keyboard(buttons))

    elif cmd == "/pollvote":
        threshold = db.get_auto_approve_votes(chat_id)

        if arg.strip():
            try:
                target_id = int(arg.strip())
            except ValueError:
                send_message(chat_id, "استخدم: تصويت (لكل الاقتراحات المعلقة) أو تصويت رقم_الاقتراح")
                return
            s = db.get_suggestion(target_id)
            if not s or s["status"] != "pending":
                send_message(chat_id, "❌ الاقتراح غير موجود أو تم البت فيه.")
                return
            pending = [s]
        else:
            pending = db.get_pending_suggestions(chat_id)[:5]  # حد أقصى لتفادي إغراق المجموعة دفعة وحدة
            if not pending:
                send_message(chat_id, "لا توجد اقتراحات حالياً للتصويت عليها. أضف واحد عبر «اقترح نص»")
                return

        created = 0
        current_seq = db.get_chat_counter(chat_id)
        for s in pending:
            text = _vote_message_text(s, threshold)
            buttons = inline_keyboard([[("✅ موافق", f"agree_{s['id']}"), ("❌ غير موافق", f"disagree_{s['id']}")]])
            message_id = send_message(chat_id, text, reply_markup=buttons)
            if message_id:
                db.set_suggestion_vote_message(chat_id, s["id"], message_id, current_seq)
                created += 1

        if created == 0:
            send_message(chat_id, "⚠️ ما قدرت أنشئ رسائل التصويت. جرّب مرة ثانية.")
            return
        send_message(chat_id, f"🗳️ صوّتوا بـ«موافق ✅» أو «غير موافق ❌» تحت كل اقتراح — صوت واحد لكل شخص "
                                f"(الضغط على نفس الخيار مرة ثانية يلغي صوتك). يُعتمد الاقتراح ويُحذف تصويته "
                                f"تلقائياً عند وصوله لـ {threshold} صوت «موافق»، أو يُحذف تلقائياً بعد 10 "
                                f"رسائل لاحقة بالمجموعة لو ما اكتمل.")

    elif cmd == "/approvesuggestion":
        if not is_admin(chat_id, user_id):
            send_message(chat_id, "هذا الأمر للأدمن فقط.")
            return
        try:
            sid = int(arg.strip())
        except ValueError:
            send_message(chat_id, "استخدم: اعتماد رقم_الاقتراح")
            return
        order = db.approve_suggestion(chat_id, sid, user_id)
        if order:
            send_message(chat_id, f"📖 تمت إضافته كالفصل {order}.")
        else:
            send_message(chat_id, "❌ الاقتراح غير موجود.")

    elif cmd == "/rejectsuggestion":
        if not is_admin(chat_id, user_id):
            send_message(chat_id, "هذا الأمر للأدمن فقط.")
            return
        try:
            sid = int(arg.strip())
        except ValueError:
            send_message(chat_id, "استخدم: رفض رقم_الاقتراح")
            return
        db.reject_suggestion(sid)
        send_message(chat_id, "❌ تم رفض الاقتراح.")

    elif cmd == "/removekeyboard":
        send_message(chat_id, "✅ تم إخفاء لوحة الأزرار. الأوامر النصية والعربية تشتغل عادي بدونها.",
                     reply_markup=REMOVE_KEYBOARD)

    elif cmd == "/adminpanel":
        if not is_admin(chat_id, user_id):
            send_message(chat_id, "هذا الأمر للأدمن فقط.")
            return
        buttons = [
            [("💡 الاقتراحات المعلقة", "panel_pending")],
            [("🗳️ إنشاء استفتاء تصويت", "panel_poll")],
            [("⚙️ إعدادات التصويت التلقائي", "panel_votesettings")],
            [("🔍 تشخيص الذكاء الاصطناعي", "panel_diag")],
            [("📢 كيفية الإذاعة", "panel_broadcasthelp")],
        ]
        send_message(chat_id, "🎛 لوحة تحكم الأدمن:", reply_markup=inline_keyboard(buttons))

    elif cmd == "/editsuggestion":
        try:
            sid_str, new_content = arg.split(maxsplit=1)
            sid = int(sid_str)
        except ValueError:
            send_message(chat_id, "استخدم: عدل اقتراح رقم_الاقتراح النص_الجديد")
            return
        ok = db.edit_suggestion(sid, user_id, new_content)
        send_message(chat_id, "✅ تم تعديل الاقتراح." if ok else "❌ ما قدرت أعدّل (تأكد إنه اقتراحك وما زال معلّق).")

    elif cmd == "/cancel":
        try:
            sid = int(arg.strip())
        except ValueError:
            send_message(chat_id, "استخدم: الغ اقتراح رقم_الاقتراح")
            return
        ok = db.delete_suggestion(sid, user_id)
        send_message(chat_id, "🗑 تم حذف اقتراحك." if ok else "❌ ما قدرت أحذف (تأكد إنه اقتراحك وما زال معلّق).")

    elif cmd == "/improve":
        if not _cooldown_ok(user_id):
            return
        try:
            sid = int(arg.strip())
        except ValueError:
            send_message(chat_id, "استخدم: حسن اقتراح رقم_الاقتراح")
            return
        s = db.get_suggestion(sid)
        if not s or s["status"] != "pending":
            send_message(chat_id, "الاقتراح غير موجود أو تم البت فيه.")
            return
        send_chat_action(chat_id)
        improved = persona.ai_improve_text(s["content"])
        if not improved:
            send_message(chat_id, "⚠️ ميزة التحسين غير مفعّلة حالياً (تحتاج مفتاح GEMINI_API_KEY).")
            return
        db.edit_suggestion(sid, s["submitted_by"], improved)
        send_message(chat_id, f"✨ تم تحسين اقتراحك #{sid}:\n\n{improved}")

    elif cmd == "/addcharacter":
        if "-" not in arg:
            send_message(chat_id, "استخدم: اضف شخصية الاسم - الوصف")
            return
        name, desc = arg.split("-", 1)
        cid = db.add_character(chat_id, name.strip(), desc.strip(), user_id)
        send_message(chat_id, f"✅ تمت إضافة الشخصية «{name.strip()}».")

    elif cmd == "/editcharacter":
        try:
            num_str, rest = arg.split(maxsplit=1)
            order_num = int(num_str)
            name, desc = rest.split("-", 1)
        except ValueError:
            send_message(chat_id, "استخدم: عدل شخصية رقم الاسم - الوصف")
            return
        ok = db.edit_character(chat_id, order_num, name.strip(), desc.strip())
        send_message(chat_id, "✅ تم التعديل." if ok else "❌ الشخصية غير موجودة.")

    elif cmd == "/deletecharacter":
        if not is_admin(chat_id, user_id):
            send_message(chat_id, "هذا الأمر للأدمن فقط.")
            return
        try:
            order_num = int(arg.strip())
        except ValueError:
            send_message(chat_id, "استخدم: احذف شخصية رقم")
            return
        ok = db.delete_character(chat_id, order_num)
        send_message(chat_id, "🗑 تم الحذف." if ok else "❌ الشخصية غير موجودة.")

    elif cmd == "/mycharacter":
        try:
            order_num = int(arg.strip())
        except ValueError:
            chars = db.get_characters(chat_id)
            if not chars:
                send_message(chat_id, "لا توجد شخصيات مسجّلة بعد. استخدم «اضف شخصية» أول.")
                return
            listing = "\n".join(f"{i+1}. {ch['name']}" for i, ch in enumerate(chars))
            send_message(chat_id, f"استخدم: شخصيتي رقم\n\nالشخصيات المتاحة:\n{listing}")
            return
        ch = db.get_character_by_order(chat_id, order_num)
        if not ch:
            send_message(chat_id, "❌ الشخصية غير موجودة.")
            return
        db.link_user_character(chat_id, user_id, ch["id"])
        send_message(chat_id, f"🔗 تم ربطك بشخصية «{ch['name']}».")

    elif cmd == "/characters":
        chars = db.get_characters(chat_id)
        if not chars:
            send_message(chat_id, "لا توجد شخصيات مسجّلة بعد. استخدم «اضف شخصية»")
            return
        text_out = "\n\n".join(f"{i+1}. {ch['name']}: {ch['description']}" for i, ch in enumerate(chars))
        send_message(chat_id, f"🧑 الشخصيات:\n\n{text_out}")

    elif cmd == "/leaderboard":
        rows = db.leaderboard(chat_id)
        if not rows:
            send_message(chat_id, "لا توجد بيانات بعد.")
            return
        text_out = "\n".join(f"{i+1}. {r['nickname'] or r['name']} — {r['points']} نقطة"
                              for i, r in enumerate(rows))
        send_message(chat_id, f"🏆 الترتيب:\n\n{text_out}")

    elif cmd == "/active":
        rows = db.get_top_active(chat_id, limit=10)
        if not rows:
            send_message(chat_id, "ما فيه بيانات تفاعل كافية بعد.")
            return
        lines = []
        for i, r in enumerate(rows):
            display = r["nickname"] or r["name"]
            lines.append(f"{i+1}. {display} — {r['message_count']} رسالة")
        send_message(chat_id, "🔥 الأكثر تفاعلاً بالمجموعة:\n\n" + "\n".join(lines))

    elif cmd == "/nickname":
        if not _require_rank(chat_id, user_id, 2):
            return
        if not reply_to_user:
            send_message(chat_id, "استخدم هذا الأمر كرد على رسالة العضو، مع كتابة الكنية بعده.\n"
                                    "مثال: كنية القبطان (كرد على رسالته)")
            return
        nickname = arg.strip()
        if not nickname:
            send_message(chat_id, "اكتب الكنية بعد الأمر. مثال: كنية القبطان")
            return
        target_id = reply_to_user["id"]
        target_name = reply_to_user.get("first_name", "مستخدم")
        db.set_nickname(chat_id, target_id, target_name, nickname)
        send_message(chat_id, f"🏷️ صارت كنية {target_name} هي «{nickname}» — بينادونه فيها سيزار بالنداء والقوائم.")

    elif cmd == "/removenickname":
        if not _require_rank(chat_id, user_id, 2):
            return
        if not reply_to_user:
            send_message(chat_id, "استخدم هذا الأمر كرد على رسالة العضو اللي تبي تشيل كنيته.")
            return
        target_id = reply_to_user["id"]
        db.remove_nickname(chat_id, target_id)
        send_message(chat_id, "🏷️ تم حذف الكنية، رجع الاسم الأصلي.")

    elif cmd == "/mystats":
        u, approved, pending = db.user_stats(chat_id, user_id)
        if not u:
            send_message(chat_id, "ما عندك بيانات بعد، شارك بالقصة أول!")
            return
        char_line = ""
        if u["character_id"]:
            send_message(chat_id, f"📊 إحصائياتك:\nالنقاط: {u['points']}\n"
                                    f"اقتراحات معتمدة: {approved}\nاقتراحات معلّقة: {pending}")
            return
        send_message(chat_id, f"📊 إحصائياتك:\nالنقاط: {u['points']}\n"
                                f"اقتراحات معتمدة: {approved}\nاقتراحات معلّقة: {pending}")

    elif cmd == "/profilecard":
        if reply_to_user:
            target_id = reply_to_user.get("id")
            target_name = reply_to_user.get("first_name", "مستخدم")
            target_username = reply_to_user.get("username")
        else:
            target_id = user_id
            target_name = user_name
            target_username = username
        _send_profile_card(chat_id, target_id, target_name, target_username)

    elif cmd == "/makeadmin":
        if db.has_any_admin(chat_id):
            send_message(chat_id, "يوجد أدمن مسجّل بالفعل بهذي المجموعة.")
            return
        db.set_admin(chat_id, user_id)
        send_message(chat_id, f"👑 تم تعيينك {RANK_NAMES[3]} يا {user_name}.")

    elif cmd == "/addadmin":
        if user_id not in MASTER_ADMIN_IDS:
            send_message(chat_id, "🚫 منح رتب الإشراف لمالك البوت فقط.")
            return
        if not reply_to_user:
            send_message(chat_id, "استخدم هذا الأمر كرد على رسالة الشخص اللي تبي تضيفه أدمن، مع تحديد "
                                    "الرتبة اختيارياً (1، 2، أو 3 — افتراضياً 1).\n"
                                    "مثال: ضيف ادمن 2 (كرد على رسالته)")
            return
        rank_arg = arg.strip()
        target_rank = 1
        if rank_arg:
            if not rank_arg.isdigit() or int(rank_arg) not in (1, 2, 3):
                send_message(chat_id, "الرتبة لازم تكون 1 أو 2 أو 3.")
                return
            target_rank = int(rank_arg)
        target_id = reply_to_user["id"]
        target_name = reply_to_user.get("first_name", "مستخدم")
        if target_id in MASTER_ADMIN_IDS:
            send_message(chat_id, "هذا الشخص أصلاً مالك البوت — عنده كل الصلاحيات دايماً.")
            return
        db.ensure_user(chat_id, target_id, target_name)
        db.set_admin_rank(chat_id, target_id, target_name, target_rank)
        send_message(chat_id, f"{RANK_NAMES[target_rank]}\nتمت ترقية {target_name} لهذي الرتبة.")

    elif cmd == "/removeadmin":
        if user_id not in MASTER_ADMIN_IDS:
            send_message(chat_id, "🚫 نزع رتب الإشراف لمالك البوت فقط.\n"
                                    "تقدر تقدّم طلب نزع بدل كذا: اطلب نزع (رد على المشرف)")
            return
        if not reply_to_user:
            send_message(chat_id, "استخدم هذا الأمر كرد على رسالة المشرف اللي تبي تشيل إشرافه.")
            return
        target_id = reply_to_user["id"]
        target_name = reply_to_user.get("first_name", "مستخدم")
        if target_id in MASTER_ADMIN_IDS:
            send_message(chat_id, "🚫 ما تقدر تشيل صلاحيات مالك البوت.")
            return
        if _get_rank(chat_id, target_id) == 0:
            send_message(chat_id, f"{target_name} أصلاً مو مشرف.")
            return
        db.remove_admin_rank(chat_id, target_id)
        send_message(chat_id, f"✅ تم سحب صلاحيات الإشراف من {target_name}.")

    elif cmd == "/requestremoveadmin":
        if not _require_rank(chat_id, user_id, 1):
            return
        if not reply_to_user:
            send_message(chat_id, "استخدم هذا الأمر كرد على رسالة المشرف اللي تبي تطلب نزع رتبته.")
            return
        target_id = reply_to_user["id"]
        target_name = reply_to_user.get("first_name", "مستخدم")
        if target_id in MASTER_ADMIN_IDS:
            send_message(chat_id, "🚫 ما تقدر تطلب نزع صلاحيات مالك البوت.")
            return
        target_rank = _get_rank(chat_id, target_id)
        if target_rank == 0:
            send_message(chat_id, f"{target_name} أصلاً مو مشرف.")
            return
        if target_id == user_id:
            send_message(chat_id, "ما تقدر تقدّم طلب نزع على نفسك.")
            return
        chat_info = get_chat(chat_id)
        chat_title = (chat_info.get("title") if chat_info else None) or str(chat_id)
        req_id = db.create_removal_request(chat_id, target_id, target_name, user_id, user_name)
        alert = (f"📋 طلب نزع رتبة إشراف جديد\n\n"
                 f"المجموعة: {chat_title}\n"
                 f"المطلوب نزعه: {target_name} ({RANK_NAMES.get(target_rank, '')}) — آيدي {target_id}\n"
                 f"مقدّم الطلب: {user_name} — آيدي {user_id}")
        kb = inline_keyboard([[("✅ وافق ونزع", f"admrm_approve_{req_id}"),
                                 ("❌ ارفض", f"admrm_reject_{req_id}")]])
        for admin_id in MASTER_ADMIN_IDS:
            send_message(admin_id, alert, reply_markup=kb)
        send_message(chat_id, f"✅ تم إرسال طلب نزع {target_name} للمالك، بينتظر موافقته.")

    elif cmd == "/myrank":
        if reply_to_user:
            target_id = reply_to_user["id"]
            target_name = reply_to_user.get("first_name", "مستخدم")
        else:
            target_id = user_id
            target_name = user_name
        rank = _get_rank(chat_id, target_id)
        send_message(chat_id, f"رتبة {target_name}: {RANK_NAMES.get(rank, '🙂 عضو عادي')}")

    elif cmd == "/adminlist":
        if not _require_rank(chat_id, user_id, 1):
            return
        rows = db.list_admins_with_rank(chat_id)
        lines = ["🎖️ مشرفو المجموعة:\n"]
        lines.append(f"👑 المالك: مالك البوت (رتبة ثابتة دايماً)")
        if rows:
            for r in rows:
                display = r["nickname"] or r["name"] or str(r["telegram_id"])
                lines.append(f"{RANK_NAMES.get(r['admin_rank'], '')} — {display}")
        else:
            lines.append("ما فيه أي مشرف مسجّل بعد غير المالك.")
        lines.append(f"\nℹ️ لعرض صلاحيات كل رتبة: صلاحيات الرتب")
        send_message(chat_id, "\n".join(lines))

    elif cmd == "/rankpermissions":
        send_message(chat_id, "🎖️ <b>رتب الإشراف الثلاث وصلاحياتها</b>\n\n" + RANK_PERMISSIONS_TEXT,
                      parse_mode="HTML")

    elif cmd == "/addchapterdirect":
        if not is_admin(chat_id, user_id):
            send_message(chat_id, "هذا الأمر للأدمن فقط.")
            return
        if not arg:
            send_message(chat_id, "استخدم: اضف فصل نص_الفصل")
            return
        order = db.add_chapter(chat_id, arg, user_id)
        send_message(chat_id, f"📖 تمت إضافة الفصل {order}.")

    elif cmd == "/editchapter":
        if not is_admin(chat_id, user_id):
            send_message(chat_id, "هذا الأمر للأدمن فقط.")
            return
        try:
            num_str, new_content = arg.split(maxsplit=1)
            order_num = int(num_str)
        except ValueError:
            send_message(chat_id, "استخدم: عدل فصل رقم النص_الجديد")
            return
        ok = db.edit_chapter(chat_id, order_num, new_content)
        send_message(chat_id, "✅ تم تعديل الفصل." if ok else "❌ الفصل غير موجود.")

    elif cmd == "/deletechapter":
        if not is_admin(chat_id, user_id):
            send_message(chat_id, "هذا الأمر للأدمن فقط.")
            return
        try:
            order_num = int(arg.strip())
        except ValueError:
            send_message(chat_id, "استخدم: احذف فصل رقم_الفصل")
            return
        ok = db.delete_chapter(chat_id, order_num)
        send_message(chat_id, "🗑 تم حذف الفصل." if ok else "❌ الفصل غير موجود.")

    elif cmd == "/undolastchapter":
        if not is_admin(chat_id, user_id):
            send_message(chat_id, "هذا الأمر للأدمن فقط.")
            return
        last = db.get_last_chapter(chat_id)
        if not last:
            send_message(chat_id, "لا توجد فصول لحذفها.")
            return
        db.delete_chapter(chat_id, last["order_num"])
        send_message(chat_id, f"🗑 تم التراجع عن الفصل {last['order_num']}.")

    elif cmd == "/mute":
        if not _require_rank(chat_id, user_id, 1):
            return
        if not reply_to_user:
            send_message(chat_id, "استخدمي الأمر كرد على رسالة الشخص، مع المدة اختيارياً "
                                    "(مثال: كتم 10 دقايق | كتم 2 ساعة | كتم دائم).")
            return
        target_id = reply_to_user["id"]
        target_name = reply_to_user.get("first_name", "مستخدم")
        seconds = parse_duration_to_seconds(arg)
        until_ts = None if seconds is None else int(time.time()) + seconds
        ok = restrict_chat_member(chat_id, target_id, until_date=until_ts, allow_messages=False)
        if not ok:
            send_message(chat_id, "⚠️ ما قدرت أكتمه — تأكدي إن البوت أدمن بالمجموعة وعنده "
                                    "صلاحية تقييد الأعضاء (Restrict Members).")
            return
        label = "بشكل دائم" if seconds is None else f"لمدة {arg.strip() or '10 دقايق'}"
        send_message(chat_id, f"🔇 تم كتم {target_name} {label}.")

    elif cmd == "/unmute":
        if not _require_rank(chat_id, user_id, 1):
            return
        if not reply_to_user:
            send_message(chat_id, "استخدمي الأمر كرد على رسالة الشخص المطلوب فك كتمه.")
            return
        target_id = reply_to_user["id"]
        target_name = reply_to_user.get("first_name", "مستخدم")
        ok = restrict_chat_member(chat_id, target_id, until_date=None, allow_messages=True)
        if ok:
            send_message(chat_id, f"🔊 تم فك الكتم عن {target_name}.")
        else:
            send_message(chat_id, "⚠️ ما قدرت أفك الكتم — تأكدي إن البوت أدمن بالمجموعة.")

    elif cmd == "/tag":
        if reply_to_user:
            target_id = reply_to_user["id"]
            target_name = reply_to_user.get("first_name", "عضو")
            extra = arg.strip()
            text = f'📣 <a href="tg://user?id={target_id}">{target_name}</a> ناداك {user_name}!'
            if extra:
                text += f"\n{extra}"
            send_message(chat_id, text, parse_mode="HTML")
        elif arg.strip():
            perform_tag(chat_id, user_name, arg.strip())
        else:
            send_message(chat_id, "استخدمي الأمر كرد على رسالة الشخص، أو اكتبي: نادي اسمه")

    elif cmd == "/tagall":
        if not is_admin(chat_id, user_id):
            send_message(chat_id, "هذا الأمر للأدمن فقط (تفادياً لإزعاج الأعضاء).")
            return
        if not _tagall_cooldown_ok(chat_id):
            send_message(chat_id, f"⏳ لحظات... مناداة الكل تحتاج {TAGALL_COOLDOWN_SECONDS} ثانية بين كل استخدام.")
            return
        members = db.get_all_users(chat_id)
        if not members:
            send_message(chat_id, "ما فيه أعضاء مسجّلين لدى البوت بهذي المجموعة بعد "
                                    "(لازم يتفاعلوا معه بأمر واحد على الأقل عشان يسجّلوا).")
            return
        note = arg.strip()
        header = f"📣 <b>{user_name}</b> يستدعي الجميع!"
        if note:
            header += f"\n{note}\n"
        mentions = [f'<a href="tg://user?id={m["telegram_id"]}">{m["name"]}</a>' for m in members]
        # نرسلها على دفعات عشان ما نتجاوز حد طول رسالة تلغرام لو المجموعة كبيرة
        batch_size = 40
        for i in range(0, len(mentions), batch_size):
            chunk = " ".join(mentions[i:i + batch_size])
            text = f"{header}\n{chunk}" if i == 0 else chunk
            send_message(chat_id, text, parse_mode="HTML")

    elif cmd == "/kick":
        if not _require_rank(chat_id, user_id, 2):
            return
        if not reply_to_user:
            send_message(chat_id, "استخدمي الأمر كرد على رسالة الشخص المطلوب طرده.")
            return
        target_id = reply_to_user["id"]
        target_name = reply_to_user.get("first_name", "مستخدم")
        if ban_chat_member(chat_id, target_id):
            unban_chat_member(chat_id, target_id)  # يفكه فوراً عشان يقدر ينضم مرة ثانية لو حد ضافه
            send_message(chat_id, f"👢 تم طرد {target_name} (يقدر يرجع لو انضاف مرة ثانية).")
        else:
            send_message(chat_id, "⚠️ ما قدرت أطرده — تأكدي إن البوت أدمن بصلاحية حظر الأعضاء.")

    elif cmd == "/ban":
        if not _require_rank(chat_id, user_id, 3):
            return
        if not reply_to_user:
            send_message(chat_id, "استخدمي الأمر كرد على رسالة الشخص المطلوب حظره.")
            return
        target_id = reply_to_user["id"]
        target_name = reply_to_user.get("first_name", "مستخدم")
        if ban_chat_member(chat_id, target_id):
            send_message(chat_id, f"🚫 تم حظر {target_name} نهائياً من المجموعة.")
        else:
            send_message(chat_id, "⚠️ ما قدرت أحظره — تأكدي إن البوت أدمن بصلاحية حظر الأعضاء.")

    elif cmd == "/unban":
        if not _require_rank(chat_id, user_id, 3):
            return
        target_id = None
        if reply_to_user:
            target_id = reply_to_user["id"]
        elif arg.strip().isdigit():
            target_id = int(arg.strip())
        if not target_id:
            send_message(chat_id, "استخدمي الأمر كرد على رسالة الشخص، أو: فك الحظر آيديه_الرقمي")
            return
        if unban_chat_member(chat_id, target_id):
            send_message(chat_id, "✅ تم فك الحظر.")
        else:
            send_message(chat_id, "⚠️ ما قدرت أفك الحظر — تأكدي إن البوت أدمن بالمجموعة.")

    elif cmd == "/rules":
        send_message(chat_id, GROUP_RULES_TEXT)

    elif cmd == "/warn":
        if not _require_rank(chat_id, user_id, 1):
            return
        if not reply_to_user:
            send_message(chat_id, "استخدمي الأمر كرد على رسالة الشخص، مع السبب اختيارياً "
                                    "(مثال: انذار سب وتلفظ).")
            return
        target_id = reply_to_user["id"]
        target_name = reply_to_user.get("first_name", "مستخدم")
        reason = arg.strip() or "مخالفة قوانين المجموعة"
        new_count = db.add_warning(chat_id, target_id, target_name, reason, user_id, user_name)

        if new_count >= MAX_WARNINGS_BEFORE_KICK:
            db.reset_warnings(chat_id, target_id)
            if ban_chat_member(chat_id, target_id):
                unban_chat_member(chat_id, target_id)
                send_message(chat_id,
                              f"⚠️ إنذار #{new_count} لـ {target_name} — السبب: {reason}\n\n"
                              f"👢 وصل للحد الأقصى ({MAX_WARNINGS_BEFORE_KICK} إنذارات) وتم طرده تلقائياً.")
            else:
                send_message(chat_id,
                              f"⚠️ إنذار #{new_count} لـ {target_name} — السبب: {reason}\n\n"
                              f"🚫 وصل للحد الأقصى لكن ما قدرت أطرده — تأكدي إن البوت أدمن بصلاحية حظر الأعضاء.")
            return

        if new_count == MAX_WARNINGS_BEFORE_KICK - 1:
            until_ts = int(time.time()) + 3600
            restrict_chat_member(chat_id, target_id, until_date=until_ts, allow_messages=False)
            send_message(chat_id,
                          f"⚠️ إنذار #{new_count}/{MAX_WARNINGS_BEFORE_KICK} لـ {target_name} — السبب: {reason}\n\n"
                          f"🔇 تم كتمه ساعة كإجراء إضافي. إنذار واحد آخر = طرد تلقائي.")
            return

        send_message(chat_id,
                      f"⚠️ إنذار #{new_count}/{MAX_WARNINGS_BEFORE_KICK} لـ {target_name} — السبب: {reason}\n\n"
                      f"عند وصوله لـ {MAX_WARNINGS_BEFORE_KICK} إنذارات راح يُطرد تلقائياً.")

    elif cmd == "/unwarn":
        if not _require_rank(chat_id, user_id, 1):
            return
        if not reply_to_user:
            send_message(chat_id, "استخدمي الأمر كرد على رسالة الشخص المطلوب سحب إنذار منه.")
            return
        target_id = reply_to_user["id"]
        target_name = reply_to_user.get("first_name", "مستخدم")
        new_count = db.remove_one_warning(chat_id, target_id)
        send_message(chat_id, f"✅ تم سحب إنذار من {target_name} — الإنذارات الحالية: {new_count}/{MAX_WARNINGS_BEFORE_KICK}.")

    elif cmd == "/resetwarnings":
        if not _require_rank(chat_id, user_id, 2):
            return
        if not reply_to_user:
            send_message(chat_id, "استخدمي الأمر كرد على رسالة الشخص المطلوب مسح إنذاراته.")
            return
        target_id = reply_to_user["id"]
        target_name = reply_to_user.get("first_name", "مستخدم")
        db.reset_warnings(chat_id, target_id)
        send_message(chat_id, f"🧹 تم مسح كل إنذارات {target_name}.")

    elif cmd == "/warnings":
        if reply_to_user:
            target_id = reply_to_user["id"]
            target_name = reply_to_user.get("first_name", "مستخدم")
        else:
            target_id = user_id
            target_name = user_name
        count = db.get_warning_count(chat_id, target_id)
        send_message(chat_id, f"⚠️ إنذارات {target_name}: {count}/{MAX_WARNINGS_BEFORE_KICK}")

    elif cmd == "/warninglist":
        if not is_admin(chat_id, user_id):
            send_message(chat_id, "هذا الأمر للأدمن فقط.")
            return
        rows = db.get_all_warnings(chat_id)
        if not rows:
            send_message(chat_id, "🧹 لا يوجد أعضاء عندهم إنذارات حالياً.")
            return
        lines = [f"⚠️ {r['name'] or r['telegram_id']}: {r['count']}/{MAX_WARNINGS_BEFORE_KICK}" for r in rows]
        send_message(chat_id, "📋 قائمة الإنذارات الحالية:\n\n" + "\n".join(lines))

    elif cmd == "/pin":
        if not _require_rank(chat_id, user_id, 1):
            return
        if not reply_to_message_id:
            send_message(chat_id, "استخدمي الأمر كرد على الرسالة المطلوب تثبيتها.")
            return
        if pin_chat_message(chat_id, reply_to_message_id):
            send_message(chat_id, "📌 تم تثبيت الرسالة.")
        else:
            send_message(chat_id, "⚠️ ما قدرت أثبتها — تأكدي إن البوت أدمن بصلاحية تثبيت الرسائل.")

    elif cmd == "/unpin":
        if not _require_rank(chat_id, user_id, 1):
            return
        if unpin_chat_message(chat_id):
            send_message(chat_id, "📌 تم إلغاء تثبيت كل الرسائل.")
        else:
            send_message(chat_id, "⚠️ ما قدرت — تأكدي إن البوت أدمن بالمجموعة.")

    elif cmd == "/delmsg":
        if not _require_rank(chat_id, user_id, 1):
            return
        if not reply_to_message_id:
            send_message(chat_id, "استخدمي الأمر كرد على الرسالة المطلوب حذفها.")
            return
        delete_message(chat_id, reply_to_message_id)

    elif cmd == "/clearall":
        if not _require_rank(chat_id, user_id, 3):
            return
        ids = db.get_and_clear_recent_messages(chat_id)
        if not ids:
            send_message(chat_id, "ما فيه رسائل مسجّلة أحذفها (تقدر أحذف بس الرسائل اللي شافها البوت "
                                    "وهو شغّال، وضمن آخر 48 ساعة حسب قيود تلغرام).")
            return
        delete_messages_batch(chat_id, ids)
        send_message(chat_id, f"🧹 تم مسح {len(ids)} رسالة.")

    elif cmd == "/games":
        buttons = [
            [("🧠 مسابقة معلومات", "starttrivia"), ("🏆 صدارة المسابقة", "starttrivialb")],
            [("🔢 تخمين الرقم", "startguess"), ("🗣️ صراحة أو تحدي", "starttruthdare")],
            [("🎭 خمن الاقتباس", "startquotegame")],
            [("🖼️ خمن الشخصية (صور)", "startcharacterphoto")],
            [("🎴 درافت الأنمي", "startanimedraft")],
            [("❌⭕ إكس-أو", "starttictactoe"), ("🔴🟡 أربعة متتالية", "startconnect4")],
            [("⚫⚪ أوثيلو", "startothello"), ("🧠 الذاكرة", "startmemory")],
            [("🎡 عجلة الأسماء", "howwheel"), ("⚔️ منافسة تصويت", "howduel")],
            [("🏆 بطولة", "starttournament")],
            [("🧹 إنهاء اللعبة", "endgame")],
        ]
        send_message(chat_id, "🎮 اختر لعبة:", reply_markup=inline_keyboard(buttons))

    elif cmd == "/tournament":
        if chat_id in TOURNAMENTS:
            send_message(chat_id, "🚫 فيه بطولة نشطة حالياً بهذي المجموعة.\n"
                                    "اكتب «الغاء البطولة» (أدمن) لإلغائها قبل بدء وحدة جديدة.")
            return
        if not is_admin(chat_id, user_id):
            send_message(chat_id, "🏆 بدء بطولة جديدة للأدمن فقط. بس أي عضو يقدر ينضم لبطولة موجودة بزر «انضم»!")
            return
        _tournament_start_setup(chat_id, user_id)

    elif cmd == "/canceltournament":
        if chat_id not in TOURNAMENTS:
            send_message(chat_id, "🚫 ما فيه بطولة نشطة حالياً.")
            return
        if not is_admin(chat_id, user_id):
            send_message(chat_id, "إلغاء البطولة للأدمن فقط.")
            return
        TOURNAMENTS.pop(chat_id, None)
        send_message(chat_id, "❌ تم إلغاء البطولة.")

    elif cmd == "/tictactoe":
        if is_tictactoe_active(chat_id):
            send_message(chat_id, "❌⭕ فيه جولة إكس-أو شغّالة حالياً! اضغطوا مربعكم برسالة اللعبة بالأعلى ⬆️")
            return
        start_tictactoe_game(chat_id, user_id, user_name)

    elif cmd == "/connect4":
        if is_connect4_active(chat_id):
            send_message(chat_id, "🔴🟡 فيه جولة أربعة متتالية شغّالة حالياً! اضغطوا رقم العمود برسالة اللعبة بالأعلى ⬆️")
            return
        start_connect4_game(chat_id, user_id, user_name)

    elif cmd == "/othello":
        if is_othello_active(chat_id):
            send_message(chat_id, "⚫⚪ فيه جولة أوثيلو شغّالة حالياً! اضغطوا خانتكم برسالة اللعبة بالأعلى ⬆️")
            return
        start_othello_game(chat_id, user_id, user_name)

    elif cmd == "/memory":
        if is_memory_active(chat_id):
            send_message(chat_id, "🧠 فيه جولة ذاكرة شغّالة حالياً! اضغطوا بطاقتكم برسالة اللعبة بالأعلى ⬆️")
            return
        start_memory_game(chat_id, user_id, user_name)

    elif cmd == "/wheel":
        if not arg:
            send_message(chat_id, "🎡 استخدم: عجلة اسم1 اسم2 اسم3 ...\n(أو مفصولين بفاصلة) — لازم اسمين على الأقل.")
            return
        start_wheel_game(chat_id, arg)

    elif cmd == "/duel":
        if not arg:
            send_message(chat_id, "⚔️ استخدم: منافسة الشي_الاول مقابل الشي_الثاني\nمثال: منافسة القهوة مقابل الشاي")
            return
        start_duel_vote(chat_id, arg)

    elif cmd == "/guessnumber":
        if is_guess_game_active(chat_id):
            send_message(chat_id, f"🔢 فيه جولة تخمين شغّالة حالياً! اضغطوا رقمكم برسالة اللعبة بالأعلى ⬆️")
            return
        start_guess_game(chat_id)

    elif cmd == "/truthdare":
        buttons = [[("🗣️ صراحة", "td_truth"), ("🎭 تحدي", "td_dare")]]
        mid = send_message(chat_id, "صراحة ولا تحدي؟ 😏", reply_markup=inline_keyboard(buttons))
        _track_game_msg(chat_id, mid)

    elif cmd == "/endgame":
        deleted_count, had_game = end_active_games(chat_id)
        if not had_game:
            send_message(chat_id, "🚫 ما فيه لعبة نشطة حالياً.")
        else:
            send_message(chat_id, f"🧹 تم إنهاء اللعبة ومسح رسائلها ({deleted_count} رسالة).")

    elif cmd == "/trivia":
        if not _cooldown_ok(user_id):
            return
        send_chat_action(chat_id)
        q = persona.ai_generate_trivia_question()
        if not q:
            send_message(chat_id, "⚠️ ما قدرت أولّد سؤال الآن (يحتاج GEMINI_API_KEY مفعّل). جرّبي مرة ثانية.")
            return
        question_text = f"🧠 [{q.get('category', 'ثقافة عامة')}] {q['question']}"
        poll_id, message_id = send_poll(chat_id, question_text, q["options"], is_anonymous=False,
                                          quiz_correct_option_id=q["correct_index"])
        if not poll_id:
            send_message(chat_id, "⚠️ ما قدرت أنشئ سؤال المسابقة.")
            return
        db.register_trivia_poll(poll_id, chat_id, q["correct_index"], q.get("category", "عام"))

    elif cmd == "/trivialeaderboard":
        rows = db.get_trivia_leaderboard(chat_id)
        if not rows:
            send_message(chat_id, "لا توجد نتائج بعد. ابدأوا بـ «مسابقة»!")
            return
        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, r in enumerate(rows):
            prefix = medals[i] if i < 3 else f"{i + 1}."
            lines.append(f"{prefix} {r['user_name']} — {r['score']} نقطة ({r['correct_count']} إجابة صح)")
        send_message(chat_id, "🏆 صدارة مسابقة المعلومات:\n\n" + "\n".join(lines))

    elif cmd == "/quotegame":
        if not _cooldown_ok(user_id):
            return
        character, options, correct_index = _pick_quote_question()
        media = db.get_media(chat_id, character["character"])
        if media:
            skip_kb = {"inline_keyboard": [[{"text": "⏭️ تخطي / التالي", "callback_data": "quoteskip"}]]}
            if media["media_type"] == "video":
                send_video(chat_id, media["file_id"])
            else:
                send_photo(chat_id, media["file_id"], reply_markup=skip_kb)
        question_text = (f"🎭 [{character['anime']}] الشخصية: {character['character']}\n"
                          f"وش من هالمقولات هي مقولتها فعلاً؟")
        poll_id, message_id = send_poll(chat_id, question_text, options, is_anonymous=False,
                                          quiz_correct_option_id=correct_index)
        if not poll_id:
            send_message(chat_id, "⚠️ ما قدرت أنشئ سؤال اللعبة.")
            return
        db.register_trivia_poll(poll_id, chat_id, correct_index, "اقتباسات الأنمي")

    elif cmd == "/quotecharacters":
        names = sorted({q["character"] for q in QUOTE_GAME_DATA})
        added_rows = db.list_quote_entries()
        lines = ["🎭 أسماء شخصيات لعبة الاقتباس (احفظي صورة لأي وحدة منهم بنفس الاسم بالضبط "
                 "عبر: احفظ باسم الاسم — وبتنعرض تلقائياً بالسؤال):\n"]
        lines += [f"• {n}" for n in names]
        if added_rows:
            lines.append("\n➕ اقتباسات مضافة من المالك:")
            lines += [f"  #{r['id']} — {r['character']} ({r['anime']})" for r in added_rows]
        send_message(chat_id, "\n".join(lines))

    elif cmd == "/addquote":
        if user_id != MASTER_ADMIN_ID:
            send_message(chat_id, "هذي الميزة للمالك الأصلي للبوت فقط.")
            return
        pieces = [p.strip() for p in arg.split("|")]
        if len(pieces) != 3 or not all(pieces):
            send_message(chat_id, "استخدم الصيغة (٣ أجزاء مفصولة بـ |):\n"
                                    "اضافة اقتباس الشخصية | الأنمي | نص المقولة\n\n"
                                    "مثال:\nاضافة اقتباس ليفاي أكرمان | هجوم العمالقة | نضج الإنسان يبان بمقدار خساراته")
            return
        character, anime, quote = pieces
        new_id = db.add_quote_entry(character, anime, quote, user_id)
        send_message(chat_id, f"✅ تمت إضافة اقتباس «{character}» برقم #{new_id}.\n"
                                f"لإضافة صورة لها: احفظ باسم {character} (كابشن على صورة/فيديو).")

    elif cmd == "/deletequote":
        if user_id != MASTER_ADMIN_ID:
            send_message(chat_id, "هذي الميزة للمالك الأصلي للبوت فقط.")
            return
        target = arg.strip()
        if not target:
            send_message(chat_id, "استخدم: حذف اقتباس #الرقم\nأو: حذف اقتباس اسم_الشخصية\n"
                                    "(اعرضي الأرقام عبر: شخصيات الاقتباس)")
            return
        target_id = target.lstrip("#").strip()
        if target_id.isdigit():
            if db.delete_quote_entry_by_id(int(target_id)):
                send_message(chat_id, f"🗑️ تم حذف الاقتباس #{target_id}.")
            else:
                send_message(chat_id, f"ما فيه اقتباس مضاف برقم #{target_id}.")
            return
        count = db.delete_quote_entry_by_character(target)
        if count:
            send_message(chat_id, f"🗑️ تم حذف {count} اقتباس مضاف باسم «{target}».")
        else:
            send_message(chat_id, f"ما فيه اقتباس مضاف بهذا الاسم بالضبط: «{target}».\n"
                                    "(الاقتباسات الأساسية بالبوت ما تنحذف، بس المضافة من المالك)")

    elif cmd == "/addcharacterphoto":
        if user_id != MASTER_ADMIN_ID:
            send_message(chat_id, "هذي الميزة للمالك الأصلي للبوت فقط.")
            return
        send_message(chat_id, "أرسل صورة الشخصية مباشرة بكابشن على هالصيغة:\n"
                                "اضافة صورة شخصية الاسم\n"
                                "أو: اضافة صورة شخصية الاسم | الأنمي")

    elif cmd == "/addmonsterphoto":
        if user_id != MASTER_ADMIN_ID:
            send_message(chat_id, "هذي الميزة للمالك الأصلي للبوت فقط.")
            return
        send_message(chat_id, "أرسل صورة الوحش مباشرة بكابشن على هالصيغة:\nاضافة صورة وحش الاسم\n"
                                "(نفس الاسم العربي المستخدم بقائمة وحوش البوابات بالضبط)")

    elif cmd == "/deletemonsterphoto":
        if user_id != MASTER_ADMIN_ID:
            send_message(chat_id, "هذي الميزة للمالك الأصلي للبوت فقط.")
            return
        target = arg_text.strip()
        if not target:
            send_message(chat_id, "استخدم: حذف صورة وحش #الرقم\nأو: حذف صورة وحش اسم_الوحش")
            return
        if target.startswith("#") and target[1:].isdigit():
            if db.delete_monster_photo_by_id(int(target[1:])):
                send_message(chat_id, "🗑️ تم الحذف.")
            else:
                send_message(chat_id, "ما لقيت صورة بهذا الرقم.")
            return
        count = db.delete_monster_photo_by_name(target)
        if count:
            send_message(chat_id, f"🗑️ تم حذف {count} صورة مضافة باسم «{target}».")
        else:
            send_message(chat_id, f"ما فيه صورة وحش بهذا الاسم بالضبط: «{target}».")

    elif cmd == "/monsterphotolist":
        rows = db.list_monster_photos()
        all_monster_names = [name for pool in hunter_system.GATE_MONSTERS.values() for name, _q in pool]
        have_names = {r["name"] for r in rows}
        lines = [f"👹 حالة صور وحوش البوابات: {len(have_names & set(all_monster_names))}/"
                 f"{len(all_monster_names)} مكتملة"]
        if rows:
            lines.append("")
            for r in rows:
                lines.append(f"#{r['id']} — {r['name']}")
        missing = [n for n in all_monster_names if n not in have_names]
        if missing:
            lines.append("\nناقصة: " + "، ".join(missing))
        lines.append("\nلإضافة: أرسل الصورة بالخاص بكابشن «اضافة صورة وحش الاسم».")
        send_message(chat_id, "\n".join(lines))

    elif cmd == "/guesscharacterphoto":
        if not _cooldown_ok(user_id):
            return
        if is_character_guess_active(chat_id):
            send_message(chat_id, "🖼️ فيه جولة «خمن الشخصية» شغّالة حالياً! اكتبوا الاسم مباشرة بالمحادثة.")
            return
        pool = db.list_character_photos()
        distinct_names = sorted({r["name"] for r in pool})
        if len(distinct_names) < 1:
            send_message(chat_id, "🚫 لسا ما فيه صور مضافة للعبة.\n"
                                    "المالك يقدر يضيف عبر: اضافة صورة شخصية الاسم (كابشن على صورة).")
            return
        start_character_guess_game(chat_id, db.get_random_character_photo())

    elif cmd == "/characterphotolist":
        rows = db.list_character_photos()
        if not rows:
            send_message(chat_id, "🚫 ما فيه أي صور مضافة للعبة بعد.")
            return
        lines = ["🖼️ صور لعبة خمن الشخصية:"]
        lines += [f"• #{r['id']} — {r['name']}" + (f" ({r['anime']})" if r["anime"] else "")
                  for r in rows]
        send_message(chat_id, "\n".join(lines))

    elif cmd == "/deletecharacterphoto":
        if user_id != MASTER_ADMIN_ID:
            send_message(chat_id, "هذي الميزة للمالك الأصلي للبوت فقط.")
            return
        target = arg.strip()
        if not target:
            send_message(chat_id, "استخدم: حذف صورة شخصية #الرقم\nأو: حذف صورة شخصية اسم_الشخصية\n"
                                    "(اعرضي الأرقام عبر: صور الشخصيات)")
            return
        target_id = target.lstrip("#").strip()
        if target_id.isdigit():
            if db.delete_character_photo_by_id(int(target_id)):
                send_message(chat_id, f"🗑️ تم حذف صورة #{target_id}.")
            else:
                send_message(chat_id, f"ما فيه صورة مضافة برقم #{target_id}.")
            return
        count = db.delete_character_photo_by_name(target)
        if count:
            send_message(chat_id, f"🗑️ تم حذف {count} صورة مضافة باسم «{target}».")
        else:
            send_message(chat_id, f"ما فيه صورة مضافة بهذا الاسم بالضبط: «{target}».")

    elif cmd == "/renamecharacterphoto":
        if user_id != MASTER_ADMIN_ID:
            send_message(chat_id, "هذي الميزة للمالك الأصلي للبوت فقط.")
            return
        pieces = arg.strip().split(maxsplit=1)
        if len(pieces) != 2 or not pieces[0].lstrip("#").isdigit():
            send_message(chat_id, "استخدم: تغيير اسم شخصية #الرقم الاسم_الجديد\n"
                                    "(اعرضي الأرقام عبر: صور الشخصيات)")
            return
        target_id = int(pieces[0].lstrip("#"))
        new_name = pieces[1].strip()
        if db.rename_character_photo(target_id, new_name):
            send_message(chat_id, f"✏️ تم تغيير اسم الصورة #{target_id} إلى «{new_name}».")
        else:
            send_message(chat_id, f"ما فيه صورة مضافة برقم #{target_id}.")

    elif cmd == "/setgrouptitle":
        if user_id not in MASTER_ADMIN_IDS:
            send_message(chat_id, "هذا الأمر للمالك فقط.")
            return
        if not arg.strip():
            send_message(chat_id, "استخدمي: اسم القروب الاسم_الجديد")
            return
        if set_chat_title(chat_id, arg.strip()):
            send_message(chat_id, f"✅ تم تغيير اسم المجموعة إلى «{arg.strip()}».")
        else:
            send_message(chat_id, "⚠️ ما قدرت أغيّر الاسم — تأكدي إن البوت أدمن بصلاحية تغيير معلومات المجموعة.")

    elif cmd == "/setgroupphoto":
        if user_id not in MASTER_ADMIN_IDS:
            send_message(chat_id, "هذا الأمر للمالك فقط.")
            return
        if not reply_to_photo:
            send_message(chat_id, "استخدمي الأمر كرد على الصورة اللي تبين تخلينها صورة المجموعة.")
            return
        file_id = reply_to_photo[-1]["file_id"]  # آخر عنصر = أعلى دقة
        file_path = get_file_path(file_id)
        if not file_path:
            send_message(chat_id, "⚠️ ما قدرت أجيب الصورة من تليجرام.")
            return
        photo_bytes = download_file_bytes(file_path)
        if not photo_bytes:
            send_message(chat_id, "⚠️ ما قدرت أحمّل الصورة.")
            return
        if set_chat_photo(chat_id, photo_bytes):
            send_message(chat_id, "🖼️ تم تغيير صورة المجموعة.")
        else:
            send_message(chat_id, "⚠️ ما قدرت أغيّرها — تأكدي إن البوت أدمن بصلاحية تغيير معلومات المجموعة.")

    elif cmd == "/lockchat":
        if not _require_rank(chat_id, user_id, 3):
            return
        if set_chat_lock(chat_id, locked=True):
            send_message(chat_id, "🔒 تم قفل المحادثة — الأعضاء العاديين ما يقدرون يرسلون رسائل الآن.")
        else:
            send_message(chat_id, "⚠️ ما قدرت أقفلها — تأكدي إن البوت أدمن بصلاحية تقييد الأعضاء.")

    elif cmd == "/unlockchat":
        if not _require_rank(chat_id, user_id, 3):
            return
        if set_chat_lock(chat_id, locked=False):
            send_message(chat_id, "🔓 تم فتح المحادثة — الكل يقدر يرسل رسائل من جديد.")
        else:
            send_message(chat_id, "⚠️ ما قدرت أفتحها — تأكدي إن البوت أدمن بصلاحية تقييد الأعضاء.")

    elif cmd == "/setautovotes":
        if user_id not in MASTER_ADMIN_IDS:
            send_message(chat_id, "هذا الأمر للمسؤول الرئيسي فقط.")
            return
        try:
            n = int(arg.strip())
        except ValueError:
            send_message(chat_id, "استخدم: اصوات التلقائي رقم")
            return
        db.set_auto_approve_votes(chat_id, n)
        send_message(chat_id, f"✅ الاعتماد التلقائي الآن عند {n} أصوات.")

    elif cmd == "/forgetchat":
        if not is_admin(chat_id, user_id):
            send_message(chat_id, "هذا الأمر للأدمن فقط.")
            return
        db.clear_conversation_history(chat_id)
        send_message(chat_id, "🧹 تم مسح ذاكرة محادثة سيزار بهذي المجموعة (القصة نفسها ما تأثرت).")

    elif cmd == "/broadcast":
        if user_id not in MASTER_ADMIN_IDS:
            send_message(chat_id, "هذا الأمر للأدمن الرئيسي فقط.")
            return
        if not arg:
            send_message(chat_id, "استخدم: اذاعة نص_الرسالة")
            return
        chats = db.get_known_chats()
        sent = 0
        for row in chats:
            try:
                send_message(row["chat_id"], f"📢 إعلان:\n\n{arg}")
                sent += 1
            except Exception:
                continue
        send_message(chat_id, f"✅ تم إرسال الإذاعة إلى {sent} مجموعة.")

    elif cmd == "/aitest":
        if not is_admin(chat_id, user_id):
            send_message(chat_id, "هذا الأمر للأدمن فقط.")
            return
        from gemini_client import ai_diagnostic
        ok, detail = ai_diagnostic()
        icon = "✅" if ok else "❌"
        send_message(chat_id, f"{icon} نتيجة اختبار الاتصال بالذكاء الاصطناعي:\n\n{detail}")

    elif cmd == "/checkenv":
        if not is_admin(chat_id, user_id):
            send_message(chat_id, "هذا الأمر للأدمن فقط.")
            return
        from config import BOT_TOKEN, GEMINI_API_KEY, GEMINI_MODEL, GEMINI_FALLBACK_MODEL

        def _mask(value):
            if not value:
                return "❌ غير مضبوط"
            tail = value[-4:] if len(value) >= 4 else value
            return f"✅ مضبوط (ينتهي بـ ...{tail}, الطول: {len(value)})"

        token_status = "❌ غير مضبوط (لا يزال القيمة الافتراضية)" if BOT_TOKEN == "ضع_التوكن_هنا" else _mask(BOT_TOKEN)
        key_status = _mask(GEMINI_API_KEY)
        send_message(
            chat_id,
            "🔍 فحص إعدادات البيئة على الاستضافة:\n\n"
            f"BOT_TOKEN: {token_status}\n"
            f"GEMINI_API_KEY: {key_status}\n"
            f"الموديل الأساسي: {GEMINI_MODEL}\n"
            f"الموديل الاحتياطي: {GEMINI_FALLBACK_MODEL}\n\n"
            "لو أي قيمة \"غير مضبوطة\"، تأكد إنك أضفتها بملف WSGI configuration "
            "فوق سطر from app import app بالضبط، ثم اضغط Reload من تبويب Web.",
        )

    elif cmd == "/features":
        if user_id not in MASTER_ADMIN_IDS:
            send_message(chat_id, "هذا الأمر لمالك البوت فقط.")
            return
        send_message(chat_id, "⚙️ تفعيل/تعطيل الميزات — اضغط على أي ميزة لتبديل حالتها:",
                      reply_markup=_features_keyboard())

    elif cmd == "/medialist":
        if user_id not in MASTER_ADMIN_IDS:
            send_message(chat_id, "هذا الأمر لمالك البوت فقط.")
            return
        rows = db.list_media(chat_id)
        if not rows:
            send_message(chat_id, "ما فيه أي صور/فيديوهات محفوظة بهذي المجموعة بعد.\n"
                                    "احفظ وحدة بإرسال صورة/فيديو بكابشن: احفظ باسم الاسم")
            return
        icons = {"photo": "🖼️", "video": "🎬"}
        lines = [f"{icons.get(r['media_type'], '📎')} {r['name']}" for r in rows]
        send_message(chat_id, "🎞️ المحفوظات بهذي المجموعة:\n\n" + "\n".join(lines))

    elif cmd == "/deletemedia":
        if user_id not in MASTER_ADMIN_IDS:
            send_message(chat_id, "هذا الأمر لمالك البوت فقط.")
            return
        name = _normalize_media_name(arg)
        if not name:
            send_message(chat_id, "استخدم: احذف محفوظ الاسم")
            return
        if db.delete_media(chat_id, name):
            send_message(chat_id, f"🗑️ تم حذف «{name}» من المحفوظات.")
        else:
            send_message(chat_id, f"ما فيه محفوظ بهذا الاسم: «{name}».")

    elif cmd == "/genimage":
        if not arg.strip():
            send_message(chat_id, "استخدم: ولد صورة وصف_الصورة (مثال: ولد صورة قطة بيضاء)")
            return
        if not _cooldown_ok(user_id):
            return
        send_chat_action(chat_id, "upload_photo")
        ok, result = image_search_client.search_photo(arg.strip())
        if not ok:
            send_message(chat_id, f"⚠️ {result}")
            return
        sent = send_photo(chat_id, result, caption=f"🖼️ نتيجة البحث عن «{arg.strip()}»")
        if not sent:
            send_message(chat_id, "⚠️ ما قدرت أرسل الصورة، جرّب مرة ثانية.")

    # ---- 👑 لوحة تحكم المالك عبر الخاص (شفافة، غير معلنة بقائمة المساعدة) ----
    elif cmd == "/ownerpanel":
        if not _owner_only_guard(chat_id, user_id):
            return
        send_message(chat_id, _owner_main_menu_text(), reply_markup=_owner_main_menu_keyboard())

    elif cmd == "/ownercommands":
        if not _owner_only_guard(chat_id, user_id):
            return
        send_message(chat_id, OWNER_COMMANDS_TEXT, parse_mode="HTML")

    elif cmd == "/ownerbackup":
        if not _owner_only_guard(chat_id, user_id):
            return
        send_message(chat_id, "💾 جاري تجهيز النسخة الاحتياطية...")
        sent = send_backup_now(reason="يدوية (من أمر نصي)")
        if sent:
            send_message(chat_id, f"✅ تم إرسال النسخة الاحتياطية لك ({sent} مالك).")
        else:
            send_message(chat_id, "⚠️ ما قدرت أرسل النسخة الاحتياطية — راجع الرسالة السابقة لتفاصيل الخطأ.")

    elif cmd == "/owneraddlink":
        if not _owner_only_guard(chat_id, user_id):
            return
        link = _bot_add_to_group_link()
        if link:
            send_message(chat_id, "➕ اضغط الرابط، اختار المجموعة، وسيزار ينضم لها مباشرة "
                                    f"(مع اقتراح صلاحيات أدمن كاملة تلقائياً):\n{link}")
        else:
            send_message(chat_id, "⚠️ ما قدرت أجيب يوزر البوت — تأكد إن التوكن شغال.")

    elif cmd == "/ownergroups":
        if not _owner_only_guard(chat_id, user_id):
            return
        text, kb = _owner_groups_message()
        send_message(chat_id, text, reply_markup=kb)

    elif cmd == "/owneralerts":
        if not _owner_only_guard(chat_id, user_id):
            return
        send_message(chat_id, _owner_alerts_text())

    elif cmd == "/ownercontacts":
        if not _owner_only_guard(chat_id, user_id):
            return
        send_message(chat_id, _owner_contacts_text())

    elif cmd == "/ownerriodm":
        if not _owner_only_guard(chat_id, user_id):
            return
        text, kb = _owner_riodm_message()
        send_message(chat_id, text, reply_markup=kb)

    elif cmd == "/ownerriogroups":
        if not _owner_only_guard(chat_id, user_id):
            return
        text, kb = _owner_riogroups_message()
        send_message(chat_id, text, reply_markup=kb)

    elif cmd == "/contactowner":
        msg_text = arg.strip()
        if not msg_text:
            send_message(chat_id, "اكتب رسالتك بعد الأمر، مثلاً: تواصل عندي استفسار عن كذا")
            return
        # المالك نفسه ما يحتاج يراسل نفسه
        if _is_master(user_id):
            send_message(chat_id, "أنت المالك أصلاً 😄")
            return
        chat_info = get_chat(chat_id) if chat_id != user_id else None
        origin_title = (chat_info.get("title") if chat_info else None) or "خاص البوت"
        db.log_contact_message(user_id, username, user_name, chat_id, origin_title, msg_text)
        uname_txt = f"@{username}" if username else "بدون يوزرنيم"
        alert = (f"💌 رسالة تواصل جديدة من {user_name} ({uname_txt})\n"
                 f"آيدي: {user_id}\n"
                 f"من: {origin_title}\n\n"
                 f"✉️ {msg_text}\n\n"
                 f"للرد: رد للمستخدم {user_id} نص_الرد")
        for admin_id in MASTER_ADMIN_IDS:
            send_message(admin_id, alert)
        send_message(chat_id, "✅ تم إرسال رسالتك للمسؤول، بيرد عليك قريباً.")

    elif cmd == "/ownerreply":
        if not _owner_only_guard(chat_id, user_id):
            return
        pieces = arg.strip().split(maxsplit=1)
        if len(pieces) < 2 or not pieces[0].lstrip("-").isdigit():
            send_message(chat_id, "استخدم: رد للمستخدم آيدي_العضو نص_الرد\n"
                                    "(الآيدي موجود برسالة التواصل اللي وصلتك)")
            return
        target_user_id = int(pieces[0])
        reply_text = pieces[1]
        sent_id = send_message(target_user_id, f"📩 رد من المسؤول:\n{reply_text}")
        if sent_id:
            send_message(chat_id, "✅ تم إرسال ردك للعضو.")
        else:
            send_message(chat_id, "⚠️ ما قدرت أرسل له — لازم يكون بدأ محادثة مع البوت من قبل.")

    elif cmd == "/ownerleave":
        if not _owner_only_guard(chat_id, user_id):
            return
        target = arg.strip()
        if not target.lstrip("-").isdigit():
            send_message(chat_id, "استخدم: اخرج من مجموعة معرف_المجموعة\n"
                                    "(اعرضي المعرّفات عبر: قائمة المجموعات)")
            return
        target_id = int(target)
        if leave_chat(target_id):
            db.forget_known_chat(target_id)
            send_message(chat_id, f"🚪 تم إخراج البوت من المجموعة {target_id} فوراً.")
        else:
            send_message(chat_id, "⚠️ ما قدرت أخرج منها — تأكد من رقم المعرف.")

    elif cmd == "/ownerpromote":
        if not _owner_only_guard(chat_id, user_id):
            return
        target = arg.strip()
        if not target.lstrip("-").isdigit():
            send_message(chat_id, "استخدم: رقني ادمن معرف_المجموعة\n"
                                    "(اعرضي المعرّفات عبر: قائمة المجموعات)")
            return
        target_id = int(target)
        if promote_chat_member(target_id, user_id):
            send_message(chat_id, f"👑 تم ترقيتك أدمن كامل الصلاحيات بالمجموعة {target_id}.")
        else:
            send_message(chat_id, "⚠️ ما قدرت أرقّيك — تأكد إن البوت نفسه أدمن هناك بصلاحية تعيين أدمن.")

    elif cmd == "/ownerinvite":
        if not _owner_only_guard(chat_id, user_id):
            return
        pieces = arg.strip().split()
        if not pieces or not pieces[0].lstrip("-").isdigit():
            send_message(chat_id, "استخدم: ضيف عضو معرف_المجموعة [آيدي_العضو اختياري]\n"
                                    "لو أعطيتني آيدي عضو بدأ محادثة مع البوت من قبل، أرسله له مباشرة.\n"
                                    "بدون آيدي، بجيب لك رابط الدعوة وترسله انت بنفسك.")
            return
        target_id = int(pieces[0])
        link = create_chat_invite_link(target_id)
        if not link:
            send_message(chat_id, "⚠️ ما قدرت أنشئ رابط دعوة — تأكد إن البوت أدمن بصلاحية دعوة أعضاء.")
            return
        if len(pieces) > 1 and pieces[1].lstrip("-").isdigit():
            target_user_id = int(pieces[1])
            sent_id = send_message(target_user_id, f"🔗 دعوة للانضمام لمجموعة:\n{link}")
            if sent_id:
                send_message(chat_id, "✅ أرسلت له رابط الدعوة بالخاص مباشرة.")
            else:
                send_message(chat_id, f"⚠️ ما قدرت أرسل له بالخاص (لازم يكون بدأ محادثة مع البوت من قبل).\n"
                                        f"تفضل الرابط وابعثه له بنفسك:\n{link}")
        else:
            send_message(chat_id, f"🔗 رابط الدعوة:\n{link}")

    elif cmd == "/hunterstatus":
        handlers_hunter.handle_hunter_status(chat_id, user_id, user_name, send_photo_bytes, send_message)

    elif cmd == "/hunterslist":
        handlers_hunter.handle_hunters_leaderboard(chat_id, send_message)

    elif cmd == "/allocatestat":
        handlers_hunter.handle_allocate_stat(chat_id, user_id, user_name, arg, send_message)

    elif cmd == "/inventory":
        handlers_hunter.handle_inventory(chat_id, user_id, user_name, send_message)

    elif cmd == "/equipitem":
        handlers_hunter.handle_equip_item(chat_id, user_id, user_name, arg, send_message)

    elif cmd == "/huntershop":
        handlers_hunter.handle_shop(chat_id, send_message)

    elif cmd == "/buyitem":
        handlers_hunter.handle_shop_buy(chat_id, user_id, user_name, arg, send_message)

    elif cmd == "/shadowarmy":
        handlers_hunter.handle_shadow_army(chat_id, user_id, user_name, send_message)

    elif cmd == "/gate":
        if not _cooldown_ok(user_id):
            return
        handlers_hunter.handle_gate_start(chat_id, user_id, user_name, send_message, send_photo_bytes)

    elif cmd == "/raidstart":
        def _send_raid_photo(cid, photo_url, caption, keyboard_rows):
            markup = inline_keyboard(keyboard_rows) if keyboard_rows else None
            return send_photo(cid, photo_url, caption=caption, reply_markup=markup)

        handlers_hunter.handle_raid_start(chat_id, user_id, user_name, _send_raid_photo, send_message,
                                           is_admin(chat_id, user_id))

    elif cmd == "/raidattack":
        if not _cooldown_ok(user_id):
            return
        handlers_hunter.handle_raid_attack(chat_id, user_id, user_name, send_message, send_photo_bytes)

    elif cmd == "/animedraft":
        start_draft_game(chat_id, user_id, user_name)

    elif cmd == "/draftphotostatus":
        send_message(chat_id, _draft_photo_status_text())

    else:
        send_message(chat_id, "أمر غير معروف. جرّب «مساعدة» لعرض كل الأوامر.")


def _features_keyboard():
    states = db.get_all_feature_states(FEATURE_LABELS.keys())
    buttons = []
    for key, label in FEATURE_LABELS.items():
        icon = "✅" if states[key] else "🚫"
        buttons.append([(f"{icon} {label}", f"feat_{key}")])
    return inline_keyboard(buttons)


def _normalize_media_name(name):
    return (name or "").strip().strip("،.!؟:").strip()


def try_save_media_from_message(chat_id, user_id, user_name, message, media_type, file_id):
    """
    يتحقق هل الرسالة أمر حفظ صادر من المالك («احفظ باسم X» أو «احفظ X» بالكابشن).
    يرجع True لو تعامل مع الرسالة (سواء نجح الحفظ أو رفضه)، و False لو مو أمر حفظ أصلاً
    (يعني كمّلي المعالجة العادية للصورة/الفيديو).
    """
    caption = (message.get("caption") or "").strip()
    if not caption:
        return False
    tokens = caption.split(maxsplit=2)
    if not tokens or tokens[0] not in ("احفظ", "احفظي"):
        return False

    if user_id not in MASTER_ADMIN_IDS:
        send_message(chat_id, "حفظ الصور والفيديوهات لمالك البوت فقط.")
        return True

    if not db.is_feature_enabled("media_library"):
        _feature_blocked_message(chat_id, "media_library")
        return True

    rest = tokens[1:]
    if rest and rest[0] in ("باسم", "اسم"):
        rest = rest[1:]
    raw = " ".join(rest)
    # فاصل | اختياري: احفظ باسم يوسف | هذا نص مرافق يظهر مع الفيديو/الصورة
    if "|" in raw:
        name_part, note_part = raw.split("|", 1)
        name = _normalize_media_name(name_part)
        note = note_part.strip() or None
    else:
        name = _normalize_media_name(raw)
        note = None
    if not name:
        send_message(chat_id, "استخدم الكابشن هالشكل: احفظ باسم الاسم — أو مع نص مرافق: "
                               "احفظ باسم الاسم | النص اللي تبيه يظهر معه")
        return True

    db.save_media(chat_id, name, media_type, file_id, note, user_id)
    icon = "🖼️" if media_type == "photo" else "🎬"
    extra = " (مع نص مرافق)" if note else ""
    send_message(chat_id, f"{icon} تم الحفظ باسم «{name}»{extra}. اكتب نفس الاسم لاحقاً عشان أعرضه.")
    return True


def try_show_saved_media(chat_id, user_id, text):
    """أي عضو: لو ذكر اسم محفوظ بأي مكان من رسالته (مو تطابق تام) يرسله ويرجع
    True، غير كذا يرجع False. (الحفظ نفسه يبقى حصراً لمالك البوت.)"""
    if not db.is_feature_enabled("media_library"):
        return False
    clean_text = _normalize_media_name(text)
    if not clean_text:
        return False

    # تطابق تام أولاً (أسرع وأدق لو الاسم لحاله بالضبط)
    media = db.get_media(chat_id, clean_text)
    matched_name = clean_text if media else None

    # لو ما طابق تماماً، دوّر هل أي اسم محفوظ مذكور بأي مكان من الرسالة
    if not media:
        for row in db.list_media(chat_id):
            saved_name = row["name"]
            if saved_name and saved_name in clean_text:
                media = db.get_media(chat_id, saved_name)
                matched_name = saved_name
                break

    if not media:
        return False

    note = media["caption"] if "caption" in media.keys() else None
    if media["media_type"] == "video":
        send_video(chat_id, media["file_id"], caption=note)
    else:
        send_photo(chat_id, media["file_id"], caption=note)
    return True


def handle_media_upload(chat_id, user_id, user_name, message, media_type, file_id):
    """نقطة دخول موحّدة من app.py لأي صورة/فيديو — تحاول أمر الحفظ أولاً."""
    return try_save_media_from_message(chat_id, user_id, user_name, message, media_type, file_id)


def handle_callback(update):
    cq = update["callback_query"]
    data = cq["data"]
    user_id = cq["from"]["id"]
    user_name = cq["from"].get("first_name", "مستخدم")
    chat_id = cq["message"]["chat"]["id"]

    db.ensure_user(chat_id, user_id, user_name)

    if data.startswith("panel_"):
        _handle_panel_action(data, chat_id, user_id, user_name, cq)
        return

    if data == "starttrivia":
        answer_callback_query(cq["id"])
        handle_command(chat_id, user_id, user_name, "/trivia")
        return

    if data == "starttrivialb":
        answer_callback_query(cq["id"])
        handle_command(chat_id, user_id, user_name, "/trivialeaderboard")
        return

    if data == "startguess":
        answer_callback_query(cq["id"])
        handle_command(chat_id, user_id, user_name, "/guessnumber")
        return

    if data == "starttruthdare":
        answer_callback_query(cq["id"])
        handle_command(chat_id, user_id, user_name, "/truthdare")
        return

    if data == "startquotegame":
        answer_callback_query(cq["id"])
        handle_command(chat_id, user_id, user_name, "/quotegame")
        return

    if data == "startcharacterphoto":
        answer_callback_query(cq["id"])
        handle_command(chat_id, user_id, user_name, "/guesscharacterphoto")
        return

    if data == "startanimedraft":
        answer_callback_query(cq["id"])
        handle_command(chat_id, user_id, user_name, "/animedraft")
        return

    if data == "charskip":
        answer_callback_query(cq["id"], text="⏭️ صورة جديدة!")
        if is_character_guess_active(chat_id):
            del CHAR_GUESS_GAMES[chat_id]
        pool = db.list_character_photos()
        if pool:
            start_character_guess_game(chat_id, db.get_random_character_photo())
        else:
            send_message(chat_id, "🚫 لسا ما فيه صور مضافة للعبة.")
        return

    if data == "quoteskip":
        answer_callback_query(cq["id"], text="⏭️ سؤال جديد!")
        handle_command(chat_id, user_id, user_name, "/quotegame")
        return

    if data == "endgame":
        answer_callback_query(cq["id"])
        handle_command(chat_id, user_id, user_name, "/endgame")
        return

    if data == "td_truth":
        answer_callback_query(cq["id"])
        send_truth_or_dare(chat_id, "truth")
        return

    if data == "td_dare":
        answer_callback_query(cq["id"])
        send_truth_or_dare(chat_id, "dare")
        return

    if data.startswith("gatechoice_"):
        rest = data[len("gatechoice_"):]
        gate_id_str, _, choice_code = rest.rpartition("_")
        try:
            gate_id = int(gate_id_str)
        except ValueError:
            answer_callback_query(cq["id"])
            return
        gate_row = db.get_active_gate(chat_id, user_id)
        if not gate_row or gate_row["id"] != gate_id:
            answer_callback_query(cq["id"], text="هذي البوابة مو نشطة لك.", show_alert=True)
            return
        answer_callback_query(cq["id"])

        handlers_hunter.handle_gate_choice(gate_id, choice_code, chat_id, user_id, user_name,
                                            send_message, send_photo_bytes)
        return

    if data.startswith("draftcat_"):
        choice_key = data[len("draftcat_"):]
        handle_draft_category_button(chat_id, cq["id"], user_id, choice_key)
        return

    if data == "draftjoin":
        handle_draft_join_button(chat_id, cq["id"], user_id, user_name)
        return

    if data == "draftai":
        handle_draft_ai_button(chat_id, cq["id"], user_id)
        return

    if data.startswith("draftpick_"):
        choice = data[len("draftpick_"):]
        handle_draft_pick_button(chat_id, cq["id"], user_id, choice)
        return

    if data.startswith("delcharphoto_"):
        handle_delete_character_photo_button(chat_id, cq["id"], user_id, data[len("delcharphoto_"):])
        return

    if data.startswith("delmonsterphoto_"):
        handle_delete_monster_photo_button(chat_id, cq["id"], user_id, data[len("delmonsterphoto_"):])
        return

    if data.startswith("gsn_"):
        guess = int(data[len("gsn_"):])
        message_id = cq["message"]["message_id"]
        handle_guess_button(chat_id, cq["id"], user_id, user_name, guess, message_id)
        return

    if data == "starttictactoe":
        answer_callback_query(cq["id"])
        handle_command(chat_id, user_id, user_name, "/tictactoe")
        return

    if data == "startconnect4":
        answer_callback_query(cq["id"])
        handle_command(chat_id, user_id, user_name, "/connect4")
        return

    if data == "startothello":
        answer_callback_query(cq["id"])
        handle_command(chat_id, user_id, user_name, "/othello")
        return

    if data == "startmemory":
        answer_callback_query(cq["id"])
        handle_command(chat_id, user_id, user_name, "/memory")
        return

    if data.startswith("ttt_"):
        cell = int(data[len("ttt_"):])
        message_id = cq["message"]["message_id"]
        handle_tictactoe_button(chat_id, cq["id"], user_id, user_name, cell, message_id)
        return

    if data.startswith("c4_"):
        col = int(data[len("c4_"):])
        message_id = cq["message"]["message_id"]
        handle_connect4_button(chat_id, cq["id"], user_id, user_name, col, message_id)
        return

    if data.startswith("otl_"):
        parts = data[len("otl_"):].split("_")
        row, col = int(parts[0]), int(parts[1])
        message_id = cq["message"]["message_id"]
        handle_othello_button(chat_id, cq["id"], user_id, user_name, row, col, message_id)
        return

    if data.startswith("mm_"):
        cell = int(data[len("mm_"):])
        message_id = cq["message"]["message_id"]
        handle_memory_button(chat_id, cq["id"], user_id, user_name, cell, message_id)
        return

    if data == "wheel_spin":
        message_id = cq["message"]["message_id"]
        handle_wheel_spin(chat_id, cq["id"], user_name, message_id)
        return

    if data in ("duel_a", "duel_b"):
        choice = "a" if data == "duel_a" else "b"
        message_id = cq["message"]["message_id"]
        handle_duel_vote(chat_id, cq["id"], user_id, choice, message_id)
        return

    if data == "howwheel":
        answer_callback_query(cq["id"], "🎡 اكتب: عجلة اسم1 اسم2 اسم3 ...", show_alert=True)
        return

    if data == "howduel":
        answer_callback_query(cq["id"], "⚔️ اكتب: منافسة شي1 مقابل شي2", show_alert=True)
        return

    if data == "starttournament":
        answer_callback_query(cq["id"])
        handle_command(chat_id, user_id, user_name, "/tournament")
        return

    if data.startswith("trn"):
        _handle_tournament_callback(data, chat_id, user_id, user_name, cq)
        return

    if data.startswith("feat_"):
        key = data[len("feat_"):]
        if user_id not in MASTER_ADMIN_IDS:
            answer_callback_query(cq["id"], "هذا الإجراء لمالك البوت فقط.", show_alert=True)
            return
        if key not in FEATURE_LABELS:
            answer_callback_query(cq["id"])
            return
        new_state = not db.is_feature_enabled(key)
        db.set_feature_enabled(key, new_state)
        answer_callback_query(cq["id"], "✅ تم التفعيل" if new_state else "🚫 تم التعطيل")
        edit_message_text(chat_id, cq["message"]["message_id"],
                            "⚙️ تفعيل/تعطيل الميزات — اضغط على أي ميزة لتبديل حالتها:",
                            reply_markup=_features_keyboard())
        return

    if data.startswith("own_"):
        _handle_owner_panel_callback(data, chat_id, user_id, cq)
        return

    if data.startswith("admrm_"):
        _handle_admin_removal_callback(data, chat_id, user_id, user_name, cq)
        return

    action, sid = data.split("_")
    sid = int(sid)

    if action == "vote":
        ok = db.vote_suggestion(sid, user_id)
        if not ok:
            answer_callback_query(cq["id"], "لقد صوّتّ لهذا الاقتراح من قبل.", show_alert=True)
            return
        db.add_points(chat_id, user_id, 1)
        answer_callback_query(cq["id"], "✅ تم تسجيل صوتك!")

        s = db.get_suggestion(sid)
        threshold = db.get_auto_approve_votes(chat_id)
        if s and s["status"] == "pending" and s["votes"] >= threshold:
            order = db.approve_suggestion(chat_id, sid, user_id)
            send_message(chat_id, f"🎉 وصل اقتراح #{sid} لعدد الأصوات المطلوب ({threshold})!\n"
                                    f"📖 تمت إضافته تلقائياً كالفصل {order}.")

    elif action == "approve":
        if not is_admin(chat_id, user_id):
            answer_callback_query(cq["id"], "هذا الإجراء للأدمن فقط.", show_alert=True)
            return
        order = db.approve_suggestion(chat_id, sid, user_id)
        answer_callback_query(cq["id"], f"✅ تمت إضافته كالفصل {order}")
        send_message(chat_id, f"📖 تمت إضافة فصل جديد (#{order}) بناءً على اقتراح معتمد!")

    elif action == "reject":
        if not is_admin(chat_id, user_id):
            answer_callback_query(cq["id"], "هذا الإجراء للأدمن فقط.", show_alert=True)
            return
        db.reject_suggestion(sid)
        answer_callback_query(cq["id"], "تم رفض الاقتراح.")

    elif action in ("agree", "disagree"):
        choice = "agree" if action == "agree" else "disagree"
        result, new_votes = db.cast_vote(sid, user_id, choice)
        if result == "added":
            db.add_points(chat_id, user_id, 1)

        s = db.get_suggestion(sid)
        threshold = db.get_auto_approve_votes(chat_id)
        vote_msg = db.get_suggestion_vote_message(sid)

        if s and s["status"] == "pending" and new_votes >= threshold:
            answer_callback_query(cq["id"], f"✅ اكتمل العدد المطلوب ({threshold}).")
            order = db.approve_suggestion(chat_id, sid, user_id)
            if vote_msg:
                delete_message(vote_msg["chat_id"], vote_msg["message_id"])
                db.delete_suggestion_vote_message_record(sid)
            send_message(chat_id, f"🎉 اقتراح #{sid} وصل لعدد الأصوات المطلوب ({threshold})!\n"
                                    f"📖 تمت إضافته تلقائياً كالفصل {order}.")
        else:
            label = {"added": "✅ تم تسجيل تصويتك", "removed": "↩️ تم إلغاء تصويتك",
                      "switched": "🔄 تم تغيير تصويتك"}[result]
            answer_callback_query(cq["id"], f"{label} ({new_votes}/{threshold})")
            if vote_msg and s:
                new_text = _vote_message_text(s, threshold)
                new_buttons = inline_keyboard([[("✅ موافق", f"agree_{sid}"), ("❌ غير موافق", f"disagree_{sid}")]])
                edit_message_text(vote_msg["chat_id"], vote_msg["message_id"], new_text, reply_markup=new_buttons)


def _handle_panel_action(data, chat_id, user_id, user_name, cq):
    if not is_admin(chat_id, user_id):
        answer_callback_query(cq["id"], "هذا الإجراء للأدمن فقط.", show_alert=True)
        return
    answer_callback_query(cq["id"])
    if data == "panel_pending":
        handle_command(chat_id, user_id, user_name, "/suggestions")
    elif data == "panel_poll":
        handle_command(chat_id, user_id, user_name, "/pollvote")
    elif data == "panel_votesettings":
        threshold = db.get_auto_approve_votes(chat_id)
        send_message(chat_id, f"⚙️ عدد الأصوات الحالي للاعتماد التلقائي: {threshold}\n"
                                f"لتغييره: اصوات التلقائي رقم_جديد")
    elif data == "panel_diag":
        handle_command(chat_id, user_id, user_name, "/aitest")
    elif data == "panel_broadcasthelp":
        send_message(chat_id, "📢 للإذاعة على كل المجموعات (الأدمن الرئيسي فقط):\nاذاعة نص_الرسالة")


def handle_poll_answer(update):
    """يعالج تحديثات poll_answer من تليجرام — أصوات الاقتراحات، وإجابات مسابقة المعلومات."""
    pa = update["poll_answer"]
    poll_id = pa["poll_id"]
    option_ids = pa.get("option_ids", [])
    user = pa.get("user")
    if not user:
        return  # تصويت مجهول (نادر بالمجموعات، الاستفتاء عندنا غير مجهول أصلاً)

    poll = db.get_suggestion_poll(poll_id)
    if poll:
        increased = db.apply_poll_vote(poll_id, user["id"], option_ids)
        if not increased:
            return
        threshold = db.get_auto_approve_votes(poll["chat_id"])
        for sid in increased:
            s = db.get_suggestion(sid)
            if s and s["status"] == "pending" and s["votes"] >= threshold:
                order = db.approve_suggestion(poll["chat_id"], sid, user["id"])
                send_message(poll["chat_id"], f"🎉 وصل اقتراح #{sid} لعدد الأصوات المطلوب ({threshold})!\n"
                                                f"📖 تمت إضافته تلقائياً كالفصل {order}.")
        return

    trivia_poll = db.get_trivia_poll(poll_id)
    if trivia_poll and option_ids:
        if option_ids[0] == trivia_poll["correct_option_id"]:
            name = user.get("first_name", "لاعب")
            db.add_trivia_score(trivia_poll["chat_id"], user["id"], name, 10)
            send_message(trivia_poll["chat_id"], f"✅ {name} أجاب صح! +10 نقاط 🎉")
        return


def cleanup_expired_vote_messages(chat_id, current_seq):
    """يحذف رسائل التصويت اللي مرّ عليها 10 رسائل لاحقة بالمجموعة بدون ما تكتمل."""
    for row in db.get_expired_vote_messages(chat_id, current_seq, ttl=10):
        delete_message(row["chat_id"], row["message_id"])
        db.delete_suggestion_vote_message_record(row["suggestion_id"])


def perform_tag(chat_id, caller_name, name_query):
    """
    ينادي عضو بالاسم (بدون الحاجة للرد على رسالته) — يبحث بين الأعضاء المسجّلين
    بالبوت بهذي المجموعة، ولو لقى تطابق يسويها منادة حقيقية (رابط بروفايل قابل
    للنقر)، وإلا يكتفي بذكر الاسم كنص عادي.
    """
    found = db.find_user_by_name(chat_id, name_query)
    if found:
        display = found["nickname"] or found["name"]
        text = f'📣 <a href="tg://user?id={found["telegram_id"]}">{display}</a> ناداك {caller_name}!'
        send_message(chat_id, text, parse_mode="HTML")
    else:
        send_message(chat_id, f"📣 {name_query} ناداك {caller_name}! (ما لقيت حساب مسجّل بهذا الاسم بالبوت، "
                                f"فالمنادة نصية بس)")


def handle_new_members(chat_id, new_members):
    names = ", ".join(m.get("first_name", "صديق") for m in new_members if not m.get("is_bot"))
    if not names:
        return
    send_message(
        chat_id,
        f"👋 أهلاً {names}! أنا سيزار، مرافق هالمجموعة بالرواية الجماعية.\n"
        f"اكتب «مساعدة» عشان تشوف كل الأوامر.",
    )


# ----------------------------------------------------------------
# ميزة جديدة: دعم الصور والفيديوهات
# ----------------------------------------------------------------
def handle_photo(chat_id, user_id, user_name, message):
    """
    يعالج أي صورة تُرسل بالمجموعة:
    - لو الكابشن «احفظ باسم X» من المالك: تُحفظ بمكتبة الوسائط (بدل أي معالجة أخرى).
    - لو الكابشن يبدأ بـ «فصل صورة رقم» (أدمن): تُربط الصورة بذاك الفصل كتوضيح بصري.
    - لو الكابشن يذكر "سيزار": يصف الصورة ويربطها بالقصة إذا ناسب.
    - غير كذا (صورة بدون كابشن أو بكابشن عادي): يتجاهلها بصمت — عشان ما يزعج
      بوصف كل صورة تُرسل بالمجموعة تلقائياً.
    """
    db.ensure_user(chat_id, user_id, user_name)
    caption = message.get("caption", "") or ""
    photos = message.get("photo")
    if not photos:
        return
    file_id = photos[-1]["file_id"]  # أعلى دقة متاحة

    if handle_media_upload(chat_id, user_id, user_name, message, "photo", file_id):
        return

    alias = match_arabic_alias(caption) if caption else None
    if alias and alias[0] == "/addcharacterphoto":
        if user_id != MASTER_ADMIN_ID:
            send_message(chat_id, "هذي الميزة للمالك الأصلي للبوت فقط.")
            return
        pieces = [p.strip() for p in alias[1].split("|")]
        name = pieces[0] if pieces else ""
        anime = pieces[1] if len(pieces) > 1 else ""
        if not name:
            send_message(chat_id, "استخدم كابشن: اضافة صورة شخصية الاسم\nأو: اضافة صورة شخصية الاسم | الأنمي")
            return
        new_id = db.add_character_photo(name, anime, file_id, user_id)
        undo_kb = inline_keyboard([[("🗑️ حذف هذي الصورة (تراجع)", f"delcharphoto_{new_id}")]])
        send_message(chat_id, f"✅ تمت إضافة صورة «{name}» برقم #{new_id}.\n"
                                f"أخطأت؟ اضغط الزر تحت للحذف الفوري.", reply_markup=undo_kb)
        return

    if alias and alias[0] == "/addmonsterphoto":
        if user_id != MASTER_ADMIN_ID:
            send_message(chat_id, "هذي الميزة للمالك الأصلي للبوت فقط.")
            return
        name = alias[1].strip()
        if not name:
            send_message(chat_id, "استخدم كابشن: اضافة صورة وحش الاسم")
            return
        new_id = db.add_monster_photo(name, file_id, user_id)
        undo_kb = inline_keyboard([[("🗑️ حذف هذي الصورة (تراجع)", f"delmonsterphoto_{new_id}")]])
        send_message(chat_id, f"✅ تمت إضافة صورة وحش «{name}» برقم #{new_id}.\n"
                                f"أخطأت؟ اضغط الزر تحت للحذف الفوري.", reply_markup=undo_kb)
        return

    if alias and alias[0] == "/attachimage":
        if not is_admin(chat_id, user_id):
            send_message(chat_id, "ربط الصور بالفصول للأدمن فقط.")
            return
        try:
            order_num = int(alias[1].strip())
        except ValueError:
            send_message(chat_id, "استخدم كابشن: فصل صورة رقم_الفصل")
            return
        db.add_chapter_image(chat_id, order_num, file_id, caption, user_id)
        send_message(chat_id, f"🖼 تم ربط الصورة بالفصل {order_num}.")
        return

    # الوصف صار يحتاج ذكر "سيزار" صراحة بالكابشن — عشان ما يوصف كل صورة تلقائياً.
    # نتحقق من هذا قبل التبريد عشان صورة بدون "سيزار" ما تستهلك من رصيد الطلبات.
    if not caption or not persona.message_mentions_persona(caption):
        return

    if not db.is_feature_enabled("persona_chat", chat_id):
        return

    if not _cooldown_ok(user_id):
        return

    chat_type = message.get("chat", {}).get("type", "private")
    username = message.get("from", {}).get("username")
    db.log_persona_usage(chat_id, chat_type, user_id, username, user_name)

    send_chat_action(chat_id)
    run_async(_deliver_persona_image_reply, chat_id, user_name, caption, file_id)


def _deliver_persona_image_reply(chat_id, user_name, caption, file_id):
    """يحمّل الصورة ويحلّلها بالذكاء الاصطناعي بخيط منفصل — تحميل الصورة نفسه
    عملية شبكة قد تاخذ وقت، فما لازم توقف استقبال باقي الرسائل بالمجموعة."""
    file_path = get_file_path(file_id)
    if not file_path:
        send_message(chat_id, "ما قدرت أحمّل الصورة، جرّب مرة ثانية.")
        return
    image_bytes = download_file_bytes(file_path)
    if not image_bytes:
        send_message(chat_id, "ما قدرت أحمّل الصورة، جرّب مرة ثانية.")
        return

    ext = file_path.split(".")[-1].lower()
    mime = "image/png" if ext == "png" else "image/webp" if ext == "webp" else "image/jpeg"

    reply = persona.ai_describe_image(image_bytes, mime, user_name, caption)
    send_message(chat_id, reply)


def handle_video(chat_id, user_id, user_name, message):
    """
    يعالج أي فيديو يُرسل بالمجموعة. حالياً الاستخدام الوحيد المدعوم هو حفظه
    بمكتبة الوسائط (المالك فقط، بكابشن «احفظ باسم X»)؛ غير كذا يتجاهله بصمت.
    """
    db.ensure_user(chat_id, user_id, user_name)
    video = message.get("video")
    if not video:
        return
    file_id = video["file_id"]
    handle_media_upload(chat_id, user_id, user_name, message, "video", file_id)


ARABIC_ALIASES.append((["فصل", "صورة"], "/attachimage"))

# ---- 👑 أوامر لوحة تحكم المالك عبر الخاص (شفافة، غير معلنة بقائمة المساعدة) ----
ARABIC_ALIASES.append((["لوحة", "المالك"], "/ownerpanel"))
ARABIC_ALIASES.append((["اوامري"], "/ownercommands"))
ARABIC_ALIASES.append((["أوامري"], "/ownercommands"))
ARABIC_ALIASES.append((["اوامر", "المالك"], "/ownercommands"))
ARABIC_ALIASES.append((["أوامر", "المالك"], "/ownercommands"))
ARABIC_ALIASES.append((["رابط", "اضافة", "سيزار"], "/owneraddlink"))
ARABIC_ALIASES.append((["ضيف", "سيزار", "لمجموعة"], "/owneraddlink"))
ARABIC_ALIASES.append((["اضافة", "سيزار", "لمجموعة"], "/owneraddlink"))
ARABIC_ALIASES.append((["قائمة", "المجموعات"], "/ownergroups"))
ARABIC_ALIASES.append((["مجموعات", "البوت"], "/ownergroups"))
ARABIC_ALIASES.append((["سجل", "التنبيهات"], "/owneralerts"))
ARABIC_ALIASES.append((["تنبيهات", "الامان"], "/owneralerts"))
ARABIC_ALIASES.append((["نسخة", "احتياطية"], "/ownerbackup"))
ARABIC_ALIASES.append((["نسخه", "احتياطية"], "/ownerbackup"))
ARABIC_ALIASES.append((["اخرج", "من", "مجموعة"], "/ownerleave"))
ARABIC_ALIASES.append((["اخرج", "من", "المجموعة"], "/ownerleave"))
ARABIC_ALIASES.append((["رقني", "ادمن"], "/ownerpromote"))
ARABIC_ALIASES.append((["رقّني", "ادمن"], "/ownerpromote"))
ARABIC_ALIASES.append((["ضيف", "عضو"], "/ownerinvite"))
ARABIC_ALIASES.append((["اضافة", "عضو"], "/ownerinvite"))
ARABIC_ALIASES.append((["رسائل", "تواصل"], "/ownercontacts"))
ARABIC_ALIASES.append((["رسائل", "التواصل"], "/ownercontacts"))
ARABIC_ALIASES.append((["يستخدم", "سيزار", "الخاص"], "/ownerriodm"))
ARABIC_ALIASES.append((["من", "يستخدم", "سيزار", "الخاص"], "/ownerriodm"))
ARABIC_ALIASES.append((["سيزار", "بالخاص", "من"], "/ownerriodm"))
ARABIC_ALIASES.append((["يستخدم", "سيزار", "بالمجموعات"], "/ownerriogroups"))
ARABIC_ALIASES.append((["من", "يستخدم", "سيزار", "بالمجموعات"], "/ownerriogroups"))
ARABIC_ALIASES.append((["سيزار", "بالمجموعات", "من"], "/ownerriogroups"))
ARABIC_ALIASES.append((["رد", "للمستخدم"], "/ownerreply"))
ARABIC_ALIASES.append((["رد", "على", "المستخدم"], "/ownerreply"))

# ---- 📞 تواصل مع المسؤول (متاح لأي عضو، خاص أو مجموعة) ----
ARABIC_ALIASES.append((["تواصل"], "/contactowner"))
ARABIC_ALIASES.append((["راسل", "المسؤول"], "/contactowner"))
ARABIC_ALIASES.append((["تواصل", "مع", "المسؤول"], "/contactowner"))

ARABIC_ALIASES.append((["بطاقتي"], "/hunterstatus"))
ARABIC_ALIASES.append((["بطاقة"], "/profilecard"))
ARABIC_ALIASES.append((["بطاقة", "تعريف"], "/profilecard"))
ARABIC_ALIASES.append((["بروفايل"], "/profilecard"))
ARABIC_ALIASES.append((["حالتي"], "/hunterstatus"))
ARABIC_ALIASES.append((["الصيادين"], "/hunterslist"))
ARABIC_ALIASES.append((["ترتيب", "الصيادين"], "/hunterslist"))
ARABIC_ALIASES.append((["بوابة"], "/gate"))
ARABIC_ALIASES.append((["توزيع"], "/allocatestat"))
ARABIC_ALIASES.append((["حقيبتي"], "/inventory"))
ARABIC_ALIASES.append((["تجهيز"], "/equipitem"))
ARABIC_ALIASES.append((["متجر"], "/huntershop"))
ARABIC_ALIASES.append((["شراء"], "/buyitem"))
ARABIC_ALIASES.append((["جيشي"], "/shadowarmy"))
ARABIC_ALIASES.append((["غارة"], "/raidstart"))
ARABIC_ALIASES.append((["هجوم"], "/raidattack"))
ARABIC_ALIASES.append((["درافت"], "/animedraft"))
ARABIC_ALIASES.append((["درافت", "الانمي"], "/animedraft"))
ARABIC_ALIASES.append((["درافت", "الأنمي"], "/animedraft"))
ARABIC_ALIASES.append((["صور", "الدرافت"], "/draftphotostatus"))
ARABIC_ALIASES.append((["حالة", "صور", "الدرافت"], "/draftphotostatus"))

ARABIC_ALIASES.sort(key=lambda item: -len(item[0]))
