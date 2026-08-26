# -*- coding: utf-8 -*-
"""
عميل بسيط للاتصال بخدمة تحميل الأغاني من يوتيوب (مستضافة على Railway
بشكل منفصل عن البوت، راجع مجلد yt_service/ للسيرفر نفسه وتعليمات نشره).

سبب الفصل: PythonAnywhere (مستضيف البوت) يحجب الوصول لمعظم النطاقات
الخارجية بما فيها يوتيوب، فلا يقدر البوت نفسه يحمّل الصوت مباشرة.
"""
import re

import requests

from config import YT_SERVICE_URL, YT_SERVICE_API_KEY

# كلمات تدل على طلب أغنية بالدردشة (بعد اسم سيزار/ريو)
SONG_REQUEST_PATTERNS = [
    r"جيب\s+اغني[ةه]?\s+(.+)",
    r"شغل\s+اغني[ةه]?\s+(.+)",
    r"جيبي\s+اغني[ةه]?\s+(.+)",
    r"شغلي\s+اغني[ةه]?\s+(.+)",
    r"نزل\s+اغني[ةه]?\s+(.+)",
    r"دور\s+على\s+اغني[ةه]?\s+(.+)",
]


def extract_song_query(text):
    """يفحص نص الرسالة: لو فيها طلب أغنية بصيغة معروفة، يرجع اسم الأغنية
    المطلوبة (بدون كلمات الأمر نفسها). يرجع None لو ما فيه طلب أغنية."""
    for pattern in SONG_REQUEST_PATTERNS:
        m = re.search(pattern, text)
        if m:
            query = m.group(1).strip()
            # نظافة بسيطة: حذف علامات ترقيم زايدة بالنهاية
            query = re.sub(r"[،.!؟]+$", "", query).strip()
            if query:
                return query
    return None


def service_configured():
    """هل خدمة يوتيوب مضبوطة أصلاً (رابط ومفتاح موجودين)؟"""
    return bool(YT_SERVICE_URL and YT_SERVICE_API_KEY)


def check_health(timeout=10):
    """يختبر الاتصال بخدمة Railway فعلياً (نقطة /health). يرجع (ok, detail)."""
    if not service_configured():
        return False, "الخدمة غير مضبوطة (رابط أو مفتاح ناقص)."
    try:
        resp = requests.get(f"{YT_SERVICE_URL}/health", timeout=timeout)
        if resp.status_code == 200:
            return True, "ok"
        return False, f"رجعت الخدمة رمز HTTP {resp.status_code}"
    except requests.exceptions.Timeout:
        return False, "لم ترد الخدمة خلال الوقت المحدد (قد تكون نائمة أو بطيئة بالإقلاع)."
    except requests.exceptions.RequestException as e:
        return False, str(e)[:200]


def download_song(query, timeout=90):
    """
    يطلب من خدمة Railway البحث عن الأغنية وتحميلها.
    يرجع (ok, file_bytes_or_error_message, filename).
    - ok=True: file_bytes_or_error_message هو محتوى ملف MP3 الفعلي (bytes).
    - ok=False: file_bytes_or_error_message رسالة خطأ نصية توضّح المشكلة.
    """
    if not service_configured():
        return False, "خدمة تحميل الأغاني غير مفعّلة حالياً (لازم تُضبط من لوحة المالك أولاً).", None

    try:
        resp = requests.get(
            f"{YT_SERVICE_URL}/search-download",
            params={"q": query},
            headers={"X-API-Key": YT_SERVICE_API_KEY},
            timeout=timeout,
        )
    except requests.exceptions.Timeout:
        return False, "الخدمة أخذت وقت طويل ولم ترد — جرّب أغنية ثانية أو حاول لاحقاً.", None
    except requests.exceptions.RequestException as e:
        return False, f"تعذّر الاتصال بخدمة الأغاني: {str(e)[:200]}", None

    if resp.status_code == 401:
        return False, "مفتاح خدمة الأغاني غير صحيح — تأكدي إن YT_SERVICE_API_KEY مطابق بالطرفين.", None

    if resp.status_code != 200:
        try:
            err = resp.json()
            msg = err.get("message") or err.get("error") or "خطأ غير معروف"
        except Exception:
            msg = f"خطأ HTTP {resp.status_code}"
        return False, msg, None

    # استخراج اسم الملف من ترويجة Content-Disposition لو موجودة
    filename = "audio.mp3"
    disposition = resp.headers.get("Content-Disposition", "")
    m = re.search(r'filename="?([^"]+)"?', disposition)
    if m:
        filename = m.group(1)

    return True, resp.content, filename
