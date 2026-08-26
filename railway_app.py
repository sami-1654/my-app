# -*- coding: utf-8 -*-
"""
خدمة صغيرة منفصلة (تُشغَّل على Railway، ليست جزءاً من بوت تيليجرام) —
تستقبل اسم أغنية، تبحث بيوتيوب، تحمّل الصوت، وترجعه كملف MP3 مباشرة.

سبب وجود هذي الخدمة منفصلة: PythonAnywhere (مستضيف بوت تيليجرام) يحجب
الوصول لمعظم النطاقات الخارجية بما فيها يوتيوب، فلا يقدر يشغّل yt-dlp مباشرة.
Railway يدعم شبكة صادرة كاملة، فهو المكان المناسب لهذي المهمة تحديداً.

الأمان: محمية بمفتاح سري بسيط (SERVICE_API_KEY) يُرسل بترويسة HTTP، عشان
ما يقدر أي شخص يستخدم الخدمة إلا بوت تيليجرام نفسه.
"""
import os
import re
import shutil
import tempfile
import uuid

from flask import Flask, request, jsonify, send_file
import yt_dlp

app = Flask(__name__)

# لازم تضبطي نفس القيمة بمتغير بيئة SERVICE_API_KEY هنا بـ Railway، وبمتغير
# YT_SERVICE_API_KEY بإعدادات بوت تيليجرام (config.py) — لازم يتطابقوا بالضبط.
SERVICE_API_KEY = os.environ.get("SERVICE_API_KEY", "")

# مجلد مؤقت لتحميل الملفات فيه قبل إرسالها ثم حذفها فوراً
DOWNLOAD_DIR = tempfile.mkdtemp(prefix="ytsvc_")

# حد أقصى لمدة الفيديو (بالثواني) — يمنع تحميل فيديوهات طويلة جداً (ساعات)
# تستهلك وقت واستضافة بدون داعي. 10 دقائق يغطي أغلب الأغاني بسهولة.
MAX_DURATION_SECONDS = 600


def _check_auth():
    key = request.headers.get("X-API-Key", "")
    return SERVICE_API_KEY and key == SERVICE_API_KEY


def _safe_filename(name):
    name = re.sub(r"[^\w\s-]", "", name, flags=re.UNICODE).strip()
    return name[:80] or "audio"


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/search-download", methods=["GET"])
def search_download():
    if not _check_auth():
        return jsonify({"error": "unauthorized"}), 401

    query = (request.args.get("q") or "").strip()
    if not query:
        return jsonify({"error": "missing query parameter 'q'"}), 400

    job_id = uuid.uuid4().hex[:12]
    out_template = os.path.join(DOWNLOAD_DIR, f"{job_id}.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "noplaylist": True,
        "default_search": "ytsearch1",  # يبحث بيوتيوب ويأخذ أول نتيجة فقط
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128",
        }],
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if "entries" in info:
                info = info["entries"][0]

            duration = info.get("duration") or 0
            if duration and duration > MAX_DURATION_SECONDS:
                return jsonify({
                    "error": "video_too_long",
                    "message": f"الفيديو طويل جداً ({int(duration/60)} دقيقة) — الحد الأقصى {MAX_DURATION_SECONDS//60} دقائق"
                }), 400

            ydl.download([query])

        mp3_path = os.path.join(DOWNLOAD_DIR, f"{job_id}.mp3")
        if not os.path.exists(mp3_path):
            return jsonify({"error": "download_failed", "message": "فشل التحميل أو التحويل"}), 500

        title = info.get("title", "audio")
        response = send_file(mp3_path, mimetype="audio/mpeg",
                              as_attachment=True,
                              download_name=f"{_safe_filename(title)}.mp3")

        @response.call_on_close
        def _cleanup():
            try:
                os.remove(mp3_path)
            except OSError:
                pass

        return response

    except yt_dlp.utils.DownloadError as e:
        return jsonify({"error": "download_error", "message": str(e)[:300]}), 500
    except Exception as e:
        return jsonify({"error": "internal_error", "message": str(e)[:300]}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
