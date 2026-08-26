# -*- coding: utf-8 -*-
"""
كل استدعاءات Telegram Bot API في مكان واحد.
"""
import json
import requests

import db
from config import TG_API


def _track_sent(chat_id, data):
    """يسجّل أي رسالة يرسلها البوت نفسه بسجل الرسائل الحديثة، عشان أمر
    «امسح الكل» يقدر يحذفها هي كمان لا بس رسائل الأعضاء."""
    try:
        if data.get("ok"):
            db.track_message(chat_id, data["result"]["message_id"])
    except (KeyError, TypeError):
        pass


def send_message(chat_id, text, reply_markup=None, parse_mode=None, reply_to_message_id=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_to_message_id:
        # allow_sending_without_reply: لو الرسالة الأصلية انحذفت بينهم، يرسل الرد
        # عادي بدون ربط بدل ما يفشل الطلب كامل بخطأ "message to reply not found"
        payload["reply_parameters"] = {
            "message_id": reply_to_message_id,
            "allow_sending_without_reply": True,
        }
    try:
        resp = requests.post(f"{TG_API}/sendMessage", json=payload, timeout=20)
        data = resp.json()
        _track_sent(chat_id, data)
        if data.get("ok"):
            return data["result"]["message_id"]
    except requests.exceptions.RequestException:
        pass
    return None


def edit_message_text(chat_id, message_id, text, reply_markup=None, parse_mode=None):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        requests.post(f"{TG_API}/editMessageText", json=payload, timeout=15)
    except requests.exceptions.RequestException:
        pass


def delete_message(chat_id, message_id):
    try:
        requests.post(f"{TG_API}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id}, timeout=15)
    except requests.exceptions.RequestException:
        pass


def delete_messages_batch(chat_id, message_ids):
    """يحذف عدة رسائل دفعة وحدة (حد تليجرام: 100 رسالة بكل استدعاء). يرجع عدد الدفعات المرسلة."""
    batches_sent = 0
    for i in range(0, len(message_ids), 100):
        chunk = message_ids[i:i + 100]
        try:
            requests.post(f"{TG_API}/deleteMessages",
                           json={"chat_id": chat_id, "message_ids": chunk}, timeout=30)
            batches_sent += 1
        except requests.exceptions.RequestException:
            pass
    return batches_sent


def send_photo(chat_id, photo_file_id_or_url, caption=None, reply_markup=None):
    payload = {"chat_id": chat_id, "photo": photo_file_id_or_url}
    if caption:
        payload["caption"] = caption
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        resp = requests.post(f"{TG_API}/sendPhoto", json=payload, timeout=30)
        data = resp.json()
        _track_sent(chat_id, data)
        if data.get("ok"):
            return data["result"]["message_id"]
    except requests.exceptions.RequestException:
        pass
    return None


def send_video(chat_id, video_file_id_or_url, caption=None):
    payload = {"chat_id": chat_id, "video": video_file_id_or_url}
    if caption:
        payload["caption"] = caption
    try:
        resp = requests.post(f"{TG_API}/sendVideo", json=payload, timeout=30)
        _track_sent(chat_id, resp.json())
    except requests.exceptions.RequestException:
        pass


def send_photo_bytes(chat_id, image_bytes, filename="image.png", caption=None, reply_markup=None):
    """يرسل صورة مولّدة (بايتات خام) بدل رابط أو file_id. يرجع message_id عند النجاح أو None."""
    try:
        files = {"photo": (filename, image_bytes, "image/png")}
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        resp = requests.post(f"{TG_API}/sendPhoto", data=data, files=files, timeout=45)
        result = resp.json()
        _track_sent(chat_id, result)
        if result.get("ok"):
            return result["result"]["message_id"]
    except requests.exceptions.RequestException:
        pass
    return None


def send_document(chat_id, file_bytes, filename, caption=None):
    """يرسل ملف (مثل PDF) للمجموعة."""
    try:
        files = {"document": (filename, file_bytes, "application/pdf")}
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        resp = requests.post(f"{TG_API}/sendDocument", data=data, files=files, timeout=60)
        _track_sent(chat_id, resp.json())
        return True
    except requests.exceptions.RequestException:
        return False


def send_document_bytes(chat_id, file_bytes, filename, mime_type="application/octet-stream", caption=None):
    """يرسل أي ملف عام كبايتات خام (مثل ZIP النسخة الاحتياطية)، بدون افتراض إنه PDF
    زي send_document. مهلة أطول (120 ثانية) لأن ملفات النسخ الاحتياطية قد تكبر."""
    try:
        files = {"document": (filename, file_bytes, mime_type)}
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        resp = requests.post(f"{TG_API}/sendDocument", data=data, files=files, timeout=120)
        data_resp = resp.json()
        _track_sent(chat_id, data_resp)
        return bool(data_resp.get("ok"))
    except requests.exceptions.RequestException:
        return False


def send_dice(chat_id, emoji="🎲"):
    """يرسل رسالة زهر/لعبة أنيميشن حقيقية من تليجرام (🎲 🎯 🏀 ⚽ 🎳 🎰). يرجع القيمة العشوائية الناتجة أو None."""
    try:
        resp = requests.post(f"{TG_API}/sendDice", json={"chat_id": chat_id, "emoji": emoji}, timeout=15)
        data = resp.json()
        _track_sent(chat_id, data)
        if data.get("ok"):
            return data["result"]["dice"]["value"]
    except requests.exceptions.RequestException:
        pass
    return None


def send_audio_bytes(chat_id, audio_bytes, is_mp3, caption=None, timeout=45, filename=None):
    """يرسل ملف صوتي (رد سيزار الصوتي أو أغنية محمّلة). MP3 لو متاح، وإلا WAV."""
    ext = "mp3" if is_mp3 else "wav"
    mime = "audio/mpeg" if is_mp3 else "audio/wav"
    try:
        files = {"audio": (filename or f"rio_voice.{ext}", audio_bytes, mime)}
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        resp = requests.post(f"{TG_API}/sendAudio", data=data, files=files, timeout=timeout)
        _track_sent(chat_id, resp.json())
        return True
    except requests.exceptions.RequestException:
        return False


def leave_chat(chat_id):
    """يخرج البوت فوراً من مجموعة معينة (أمر المالك عبر الخاص)."""
    try:
        resp = requests.post(f"{TG_API}/leaveChat", json={"chat_id": chat_id}, timeout=15)
        return bool(resp.json().get("ok"))
    except requests.exceptions.RequestException:
        return False


def get_me():
    """يرجع معلومات البوت نفسه (يوزره، آيديه...) أو None عند الفشل — تُستخدم لبناء رابط الإضافة لمجموعة."""
    try:
        resp = requests.get(f"{TG_API}/getMe", timeout=15)
        data = resp.json()
        if data.get("ok"):
            return data["result"]
    except requests.exceptions.RequestException:
        pass
    return None


def get_chat(chat_id):
    """يرجع بيانات المجموعة (العنوان، النوع، رابط الدعوة الحالي...) أو None عند الفشل."""
    try:
        resp = requests.get(f"{TG_API}/getChat", params={"chat_id": chat_id}, timeout=15)
        data = resp.json()
        if data.get("ok"):
            return data["result"]
    except requests.exceptions.RequestException:
        pass
    return None


def get_chat_member_count(chat_id):
    """يرجع عدد أعضاء المجموعة أو None عند الفشل."""
    try:
        resp = requests.get(f"{TG_API}/getChatMemberCount", params={"chat_id": chat_id}, timeout=15)
        data = resp.json()
        if data.get("ok"):
            return data["result"]
    except requests.exceptions.RequestException:
        pass
    return None


def promote_chat_member(chat_id, user_id):
    """
    يرقّي مستخدم لأدمن كامل الصلاحيات بمجموعة معينة. يحتاج البوت نفسه يكون أدمن
    فيها بصلاحية تعيين أدمن (can_promote_members)، وإلا يرجع False.
    """
    payload = {
        "chat_id": chat_id,
        "user_id": user_id,
        "can_manage_chat": True,
        "can_delete_messages": True,
        "can_manage_video_chats": True,
        "can_restrict_members": True,
        "can_promote_members": True,
        "can_change_info": True,
        "can_invite_users": True,
        "can_pin_messages": True,
    }
    try:
        resp = requests.post(f"{TG_API}/promoteChatMember", json=payload, timeout=15)
        return bool(resp.json().get("ok"))
    except requests.exceptions.RequestException:
        return False


def create_chat_invite_link(chat_id, name=None):
    """
    ينشئ رابط دعوة جديد لمجموعة معينة (يُستخدم للمالك عشان يرسله لعضو يريد إضافته،
    لأن Telegram Bot API ما يسمح للبوت يضيف عضو مباشرة بدون موافقته هو بالانضمام).
    يرجع الرابط أو None عند الفشل.
    """
    payload = {"chat_id": chat_id}
    if name:
        payload["name"] = name[:32]
    try:
        resp = requests.post(f"{TG_API}/createChatInviteLink", json=payload, timeout=15)
        data = resp.json()
        if data.get("ok"):
            return data["result"].get("invite_link")
    except requests.exceptions.RequestException:
        pass
    return None


def get_chat_member_status(chat_id, user_id):
    """يرجع حالة عضوية شخص بمجموعة (creator/administrator/member/left/kicked)، أو None عند الفشل."""
    try:
        resp = requests.get(f"{TG_API}/getChatMember",
                             params={"chat_id": chat_id, "user_id": user_id}, timeout=15)
        data = resp.json()
        if data.get("ok"):
            return data["result"].get("status")
    except requests.exceptions.RequestException:
        pass
    return None


def restrict_chat_member(chat_id, user_id, until_date=None, allow_messages=False):
    """كتم/فك كتم عضو بمجموعة. يحتاج البوت يكون أدمن بصلاحية تقييد الأعضاء."""
    permissions = {
        "can_send_messages": allow_messages,
        "can_send_audios": allow_messages,
        "can_send_documents": allow_messages,
        "can_send_photos": allow_messages,
        "can_send_videos": allow_messages,
        "can_send_video_notes": allow_messages,
        "can_send_voice_notes": allow_messages,
        "can_send_polls": allow_messages,
        "can_send_other_messages": allow_messages,
        "can_add_web_page_previews": allow_messages,
    }
    payload = {"chat_id": chat_id, "user_id": user_id, "permissions": permissions}
    if until_date:
        payload["until_date"] = until_date
    try:
        resp = requests.post(f"{TG_API}/restrictChatMember", json=payload, timeout=15)
        data = resp.json()
        return bool(data.get("ok"))
    except requests.exceptions.RequestException:
        return False


def ban_chat_member(chat_id, user_id):
    try:
        resp = requests.post(f"{TG_API}/banChatMember", json={"chat_id": chat_id, "user_id": user_id}, timeout=15)
        return bool(resp.json().get("ok"))
    except requests.exceptions.RequestException:
        return False


def unban_chat_member(chat_id, user_id):
    try:
        resp = requests.post(f"{TG_API}/unbanChatMember",
                              json={"chat_id": chat_id, "user_id": user_id, "only_if_banned": True}, timeout=15)
        return bool(resp.json().get("ok"))
    except requests.exceptions.RequestException:
        return False


def pin_chat_message(chat_id, message_id):
    try:
        resp = requests.post(f"{TG_API}/pinChatMessage",
                              json={"chat_id": chat_id, "message_id": message_id}, timeout=15)
        return bool(resp.json().get("ok"))
    except requests.exceptions.RequestException:
        return False


def unpin_chat_message(chat_id):
    try:
        resp = requests.post(f"{TG_API}/unpinAllChatMessages", json={"chat_id": chat_id}, timeout=15)
        return bool(resp.json().get("ok"))
    except requests.exceptions.RequestException:
        return False


def set_chat_photo(chat_id, photo_bytes):
    """يغيّر صورة المجموعة (يحتاج البوت أدمن بصلاحية تغيير معلومات المجموعة)."""
    try:
        files = {"photo": ("group.jpg", photo_bytes, "image/jpeg")}
        data = {"chat_id": chat_id}
        resp = requests.post(f"{TG_API}/setChatPhoto", data=data, files=files, timeout=30)
        return bool(resp.json().get("ok"))
    except requests.exceptions.RequestException:
        return False


def set_chat_title(chat_id, title):
    try:
        resp = requests.post(f"{TG_API}/setChatTitle", json={"chat_id": chat_id, "title": title[:128]}, timeout=15)
        return bool(resp.json().get("ok"))
    except requests.exceptions.RequestException:
        return False


def set_chat_lock(chat_id, locked):
    """يقفل/يفتح المحادثة بمنع/سماح الأعضاء العاديين بإرسال أي رسائل (الأدمن يقدر دايماً)."""
    allow = not locked
    permissions = {
        "can_send_messages": allow,
        "can_send_audios": allow,
        "can_send_documents": allow,
        "can_send_photos": allow,
        "can_send_videos": allow,
        "can_send_video_notes": allow,
        "can_send_voice_notes": allow,
        "can_send_polls": allow,
        "can_send_other_messages": allow,
        "can_add_web_page_previews": allow,
        "can_change_info": False,
        "can_invite_users": True,
        "can_pin_messages": False,
    }
    try:
        resp = requests.post(f"{TG_API}/setChatPermissions",
                              json={"chat_id": chat_id, "permissions": permissions}, timeout=15)
        return bool(resp.json().get("ok"))
    except requests.exceptions.RequestException:
        return False


def send_poll(chat_id, question, options, is_anonymous=False, allows_multiple_answers=False,
              quiz_correct_option_id=None):
    """يرسل استفتاء تلغرام رسمي. لو quiz_correct_option_id محدد، يصير استفتاء نوع Quiz
    (يوريك تليجرام نفسه صح/غلط لحظياً). يرجع (poll_id, message_id) أو (None, None) عند الفشل."""
    payload = {
        "chat_id": chat_id,
        "question": question[:300],
        "options": [o[:100] for o in options],
        "is_anonymous": is_anonymous,
    }
    if quiz_correct_option_id is not None:
        payload["type"] = "quiz"
        payload["correct_option_id"] = quiz_correct_option_id
    else:
        payload["allows_multiple_answers"] = allows_multiple_answers
    try:
        resp = requests.post(f"{TG_API}/sendPoll", json=payload, timeout=20)
        data = resp.json()
        _track_sent(chat_id, data)
        if data.get("ok"):
            result = data["result"]
            return result["poll"]["id"], result["message_id"]
    except requests.exceptions.RequestException:
        pass
    return None, None


def send_chat_action(chat_id, action="typing"):
    """يظهر مؤشر 'يكتب الآن...' بالمحادثة أثناء انتظار رد الذكاء الاصطناعي — تحسين تجربة استخدام بسيط."""
    try:
        requests.post(f"{TG_API}/sendChatAction", json={"chat_id": chat_id, "action": action}, timeout=10)
    except requests.exceptions.RequestException:
        pass


def answer_callback_query(callback_query_id, text=None, show_alert=False):
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    payload["show_alert"] = show_alert
    try:
        requests.post(f"{TG_API}/answerCallbackQuery", json=payload, timeout=15)
    except requests.exceptions.RequestException:
        pass


def get_file_path(file_id):
    """يرجع مسار الملف على خوادم تليجرام لتحميله لاحقاً، أو None عند الفشل."""
    try:
        resp = requests.get(f"{TG_API}/getFile", params={"file_id": file_id}, timeout=15)
        data = resp.json()
        if data.get("ok"):
            return data["result"]["file_path"]
    except requests.exceptions.RequestException:
        pass
    return None


def download_file_bytes(file_path):
    """يحمّل محتوى الملف كبايتات خام من خوادم تليجرام."""
    from config import BOT_TOKEN
    url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            return resp.content
    except requests.exceptions.RequestException:
        pass
    return None
