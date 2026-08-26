# -*- coding: utf-8 -*-
"""
================================================================
 بوت الرواية الجماعية على Telegram + شخصية "سيزار" — نسخة مُعاد هيكلتها
================================================================
هذا الملف نقطة الدخول فقط (Flask + webhook). المنطق موزّع على ملفات:
  config.py         - كل الإعدادات القابلة للتغيير
  db.py             - قاعدة البيانات (SQLite)
  telegram_client.py- التواصل مع Telegram Bot API
  gemini_client.py  - التواصل مع Gemini API (نص وصور) + إصلاح انقطاع الردود
  persona.py        - شخصية سيزار وذاكرته الحقيقية للمحادثة
  handlers.py        - الأوامر، الأزرار، الأعضاء الجدد، والصور

----------------------------------------------------------------
📦 المكتبات المطلوبة (requirements.txt)
----------------------------------------------------------------
    pip install --user flask requests

----------------------------------------------------------------
🚀 التثبيت على PythonAnywhere
----------------------------------------------------------------
1) ارفع كل ملفات هذا المشروع (app.py, config.py, db.py, telegram_client.py,
   gemini_client.py, persona.py, handlers.py) بنفس المجلد (مثلاً story_bot).

2) ثبّت المكتبات من Bash console:
       cd story_bot
       pip install --user flask requests

3) من تبويب Web: Add a new web app → Flask → حدد مسار المجلد.

4) افتح ملف WSGI configuration وأضف فوق سطر from app import app:
       import os
       os.environ["BOT_TOKEN"] = "التوكن_من_BotFather"
       os.environ["GEMINI_API_KEY"] = "مفتاح_Gemini_API"
   لتوسيع الحصة اليومية المجانية (مفيد لمجموعة كبيرة نشيطة)، تقدر تضيف عدة مفاتيح
   من حسابات/مشاريع Google AI Studio مختلفة، مفصولة بفاصلة:
       os.environ["GEMINI_API_KEYS"] = "مفتاح1,مفتاح2,مفتاح3"
   البوت يتحوّل تلقائياً للمفتاح التالي فور ما مفتاح يتجاوز حصته اليومية (بدون أي
   تأخير أو انقطاع يلاحظه الأعضاء).
   ثم تأكد آخر سطر:
       from app import app as application

5) فعّل الـ Webhook (افتحه مرة وحدة بالمتصفح):
       https://api.telegram.org/botTOKEN/setWebhook?url=https://USERNAME.pythonanywhere.com/webhook

6) بعد أي تعديل بالكود: اضغط زر Reload بتبويب Web.

7) عطّل "وضع الخصوصية" (Privacy Mode) من BotFather → Bot Settings → Group
   Privacy → Turn off، ثم اطرد البوت من المجموعة وضيفه من جديد، عشان يشوف
   كل الرسائل ويقدر يرد على "سيزار" والأوامر العربية والصور.

للتفاصيل الكاملة (تشخيص الأعطال، الأدمن الرئيسي، الأوامر...) راجع ملف
README.md المرفق.
----------------------------------------------------------------
"""
from flask import Flask, request

import os
import datetime

import db
import handlers
import persona
import youtube_service
from telegram_client import send_chat_action

app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(force=True)

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        chat_type = msg["chat"].get("type", "private")
        chat_title = msg["chat"].get("title") or msg["chat"].get("first_name", "خاص")

        # حماية من السرقة: ما نرد إطلاقاً لو المالك مو عضو بهذي المجموعة
        if not handlers.is_owner_present(chat_id, chat_type):
            return "ok"

        db.record_chat(chat_id, chat_title, chat_type)

        # كل رسالة واردة بالمجموعة تُحسب بعدّاد المجموعة، وتُستخدم لحذف رسائل
        # التصويت تلقائياً بعد مرور 10 رسائل لاحقة عليها لو ما اكتملت
        current_seq = db.bump_chat_counter(chat_id)
        handlers.cleanup_expired_vote_messages(chat_id, current_seq)

        # نسجّل معرّف الرسالة عشان أمر "امسح الكل" يقدر يحذفها لاحقاً لو احتاج المالك
        if "message_id" in msg:
            db.track_message(chat_id, msg["message_id"])

        if "new_chat_members" in msg:
            handlers.handle_new_members(chat_id, msg["new_chat_members"])
            return "ok"

        user_id = msg.get("from", {}).get("id")
        user_name = msg.get("from", {}).get("first_name", "مستخدم")
        username = msg.get("from", {}).get("username")

        # ---- صور ----
        if "photo" in msg:
            handlers.handle_photo(chat_id, user_id, user_name, msg)
            return "ok"

        # ---- فيديوهات (تُستخدم فقط لحفظ فيديو بمكتبة الوسائط من المالك) ----
        if "video" in msg:
            handlers.handle_video(chat_id, user_id, user_name, msg)
            return "ok"

        if "text" in msg:
            text = msg["text"]
            # يُحسب لعداد "الأكثر تفاعلاً" (كل رسالة نصية حقيقية من عضو، ما عدا الأوامر)
            if user_id and not text.startswith("/"):
                db.bump_activity(chat_id, user_id, user_name)
            reply_to_user = None
            reply_to_message_id = None
            reply_to_photo = None
            if "reply_to_message" in msg:
                reply_to_message_id = msg["reply_to_message"].get("message_id")
                if "from" in msg["reply_to_message"]:
                    reply_to_user = msg["reply_to_message"]["from"]
                reply_to_photo = msg["reply_to_message"].get("photo")

            if text.startswith("/"):
                handlers.handle_command(chat_id, user_id, user_name, text, reply_to_user, reply_to_message_id,
                                         reply_to_photo, username=username)
            else:
                alias_match = handlers.match_arabic_alias(text)
                if alias_match:
                    cmd, rest = alias_match
                    full_text = f"{cmd} {rest}".strip()
                    handlers.handle_command(chat_id, user_id, user_name, full_text, reply_to_user,
                                             reply_to_message_id, reply_to_photo, username=username)
                elif reply_to_message_id and handlers.react_to_truthdare_reply(chat_id, user_name, reply_to_message_id):
                    pass
                elif handlers.check_character_guess_answer(chat_id, user_id, user_name, text):
                    pass
                elif handlers.try_show_saved_media(chat_id, user_id, text):
                    pass
                elif persona.message_mentions_persona(text):
                    if not db.is_feature_enabled("persona_chat", chat_id):
                        pass
                    else:
                        db.ensure_user(chat_id, user_id, user_name)
                        db.log_persona_usage(chat_id, chat_type, user_id, username, user_name)
                        tag_target = persona.extract_tag_target(text)
                        if persona.message_asks_about_creator(text):
                            # رد ثابت مباشر (بدون استدعاء الذكاء الاصطناعي) لضمان دقة معلومة الصانع دائماً
                            handlers.send_message(chat_id, persona.creator_reply())
                        elif tag_target:
                            handlers.perform_tag(chat_id, user_name, tag_target)
                        elif youtube_service.extract_song_query(text):
                            song_query = youtube_service.extract_song_query(text)
                            handlers.run_async(handlers._deliver_song_request, chat_id, user_name,
                                                song_query, msg.get("message_id"))
                        elif persona.message_requests_voice(text):
                            if handlers._voice_cooldown_ok(user_id):
                                send_chat_action(chat_id, "record_voice")
                                handlers.run_async(handlers._deliver_persona_voice_reply,
                                                    chat_id, user_name, text, user_id)
                        elif handlers._cooldown_ok(user_id):
                            send_chat_action(chat_id)
                            handlers.run_async(handlers._deliver_persona_reply, chat_id, user_name, text,
                                                msg.get("message_id"))

    elif "callback_query" in update:
        cq_chat = update["callback_query"]["message"]["chat"]
        if handlers.is_owner_present(cq_chat["id"], cq_chat.get("type", "private")):
            handlers.handle_callback(update)
        else:
            from telegram_client import answer_callback_query
            answer_callback_query(update["callback_query"]["id"])

    elif "poll_answer" in update:
        handlers.handle_poll_answer(update)

    elif "my_chat_member" in update:
        # تحديث Telegram التلقائي كل مرة تتغيّر فيها عضوية/صلاحيات البوت نفسه بأي
        # مجموعة (طُرد، خرج، اتغيّرت صلاحياته كأدمن...). نستخدمه لسجل تنبيهات أمنية
        # يوصل مباشرة لمالك البوت — دفاع مبكر لو حد حاول يشيل البوت أو يقيّده.
        handlers.handle_my_chat_member_update(update["my_chat_member"])

    return "ok"


@app.route("/", methods=["GET"])
def index():
    return "Story bot (Rio) is running."


@app.route("/weekly_check", methods=["GET", "POST"])
def weekly_check():
    """
    نقطة نهاية للتذكير الأسبوعي التلقائي — لا يستدعيها تليجرام، بل مهمة مجدولة
    (PythonAnywhere Tasks) تناديها مرة يومياً؛ الدالة نفسها تتحقق لكل مجموعة
    هل مرّ 7 أيام بدون نشاط ولم يُرسَل تذكير خلال آخر 7 أيام، فإن كان كذلك تُرسل
    تذكيراً واحداً. محمية بمفتاح سري (REMINDER_SECRET) عشان محد يقدر يناديها
    من برّا غير صاحب البوت.
    """
    secret = request.args.get("secret") or request.headers.get("X-Reminder-Secret")
    expected = os.environ.get("REMINDER_SECRET", "")
    if not expected or secret != expected:
        return "forbidden", 403

    now = datetime.datetime.utcnow()
    sent = 0
    for row in db.get_known_chats():
        chat_id = row["chat_id"]
        last_seen = row["last_seen"]
        if not last_seen:
            continue
        try:
            last_seen_dt = datetime.datetime.fromisoformat(last_seen)
        except ValueError:
            continue
        if (now - last_seen_dt).days < 7:
            continue

        last_reminder = db.get_last_reminder(chat_id)
        if last_reminder:
            try:
                last_reminder_dt = datetime.datetime.fromisoformat(last_reminder)
                if (now - last_reminder_dt).days < 7:
                    continue
            except ValueError:
                pass

        handlers.send_message(chat_id, "📖 القصة تنتظركم! مرّ أسبوع بدون نشاط. "
                                          "اكتبوا «اقترح» بفكرتكم القادمة ✨")
        db.set_last_reminder(chat_id, now.isoformat())
        sent += 1

    return f"ok, sent {sent}", 200


@app.route("/backup_check", methods=["GET", "POST"])
def backup_check():
    """
    نقطة نهاية للنسخة الاحتياطية التلقائية — لا يستدعيها تليجرام، بل مهمة مجدولة
    (PythonAnywhere Tasks) تناديها مرة يومياً؛ الدالة نفسها تتحقق هل مرّت
    BACKUP_INTERVAL_DAYS يوم (افتراضياً 15) من آخر نسخة احتياطية مُرسلة، وإن كان
    كذلك تبني ZIP فيه كل ملفات الكود + قاعدة البيانات الحالية وترسله لكل مالكي
    البوت بالخاص. محمية بمفتاح سري (BACKUP_SECRET) بنفس فكرة /weekly_check.
    """
    secret = request.args.get("secret") or request.headers.get("X-Reminder-Secret")
    expected = os.environ.get("BACKUP_SECRET", "")
    if not expected or secret != expected:
        return "forbidden", 403

    if not handlers.backup_due():
        return "ok, not due yet", 200

    sent = handlers.send_backup_now(reason="تلقائية (كل %s يوم)" % handlers.BACKUP_INTERVAL_DAYS)
    return (f"ok, sent {sent}", 200) if sent else ("failed to build/send backup", 500)


db.init_db()

if __name__ == "__main__":
    app.run(debug=True)
