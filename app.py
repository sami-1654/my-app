# -*- coding: utf-8 -*-
"""
خدمة صغيرة منفصلة (تُشغَّل على Render، ليست جزءاً من بوت تيليجرام) —
فيها مسارين:
  1) /search  : تستقبل اسم أغنية، تبحث بيوتيوب، ترجع أفضل عدة نتائج (بدون
                تحميل) عشان البوت يعرضها كأزرار اختيار للمستخدم.
  2) /download: تستقبل معرّف فيديو (video_id) محدد من نتائج البحث، تحمّله
                فعلياً وترجعه كملف MP3.

سبب وجود هذي الخدمة منفصلة: PythonAnywhere (مستضيف بوت تيليجرام) يحجب
الوصول لمعظم النطاقات الخارجية بما فيها يوتيوب، فلا يقدر يشغّل yt-dlp مباشرة.

الأمان: محمية بمفتاح سري بسيط (SERVICE_API_KEY) يُرسل بترويسة HTTP، عشان
ما يقدر أي شخص يستخدم الخدمة إلا بوت تيليجرام نفسه.
"""
import os
import re
import tempfile
import uuid

from flask import Flask, request, jsonify, send_file
import yt_dlp

app = Flask(__name__)

# لازم تضبطي نفس القيمة بمتغير بيئة SERVICE_API_KEY هنا بـ Render، وبمتغير
# YT_SERVICE_API_KEY بإعدادات بوت تيليجرام (config.py) — لازم يتطابقوا بالضبط.
SERVICE_API_KEY = os.environ.get("SERVICE_API_KEY", "")

DOWNLOAD_DIR = tempfile.mkdtemp(prefix="ytsvc_")

# حد أقصى لمدة الفيديو (بالثواني) — يمنع تحميل فيديوهات طويلة جداً (ساعات)
MAX_DURATION_SECONDS = 600

# عدد نتائج البحث المرجعة للاختيار منها (يطابق عدد أزرار البوت)
SEARCH_RESULTS_COUNT = 3


def _check_auth():
    key = request.headers.get("X-API-Key", "")
    return SERVICE_API_KEY and key == SERVICE_API_KEY


def _safe_filename(name):
    name = re.sub(r"[^\w\s-]", "", name, flags=re.UNICODE).strip()
    return name[:80] or "audio"


def _format_duration(seconds):
    if not seconds:
        return "؟"
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/search", methods=["GET"])
def search():
    """يبحث بيوتيوب ويرجع أفضل عدة نتائج (معرّف، عنوان، مدة) بدون تحميل —
    البوت يعرضها كأزرار، والمستخدم يختار وحدة قبل التحميل الفعلي."""
    if not _check_auth():
        return jsonify({"error": "unauthorized"}), 401

    query = (request.args.get("q") or "").strip()
    if not query:
        return jsonify({"error": "missing query parameter 'q'"}), 400

    ydl_opts = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "default_search": f"ytsearch{SEARCH_RESULTS_COUNT}",
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "extract_flat": "in_playlist",  # بحث سريع بدون تحميل معلومات ثقيلة
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            entries = info.get("entries", []) if "entries" in info else [info]

            results = []
            for e in entries[:SEARCH_RESULTS_COUNT]:
                if not e:
                    continue
                results.append({
                    "video_id": e.get("id"),
                    "title": e.get("title", "بدون عنوان"),
                    "duration": _format_duration(e.get("duration")),
                    "channel": e.get("uploader") or e.get("channel") or "",
                })

            if not results:
                return jsonify({"error": "no_results", "message": "ما لقيت أي نتيجة لهذا البحث"}), 404

            return jsonify({"results": results})

    except yt_dlp.utils.DownloadError as e:
        return jsonify({"error": "search_error", "message": str(e)[:300]}), 500
    except Exception as e:
        return jsonify({"error": "internal_error", "message": str(e)[:300]}), 500


@app.route("/download", methods=["GET"])
def download():
    """يحمّل فيديو محدد بمعرّفه (video_id) من نتائج /search السابقة، ويرجعه MP3."""
    if not _check_auth():
        return jsonify({"error": "unauthorized"}), 401

    video_id = (request.args.get("video_id") or "").strip()
    if not video_id:
        return jsonify({"error": "missing query parameter 'video_id'"}), 400

    # حماية بسيطة: معرّف يوتيوب الحقيقي حروف/أرقام/- /_ فقط، بدون أي رموز أخرى
    if not re.fullmatch(r"[\w-]{5,20}", video_id):
        return jsonify({"error": "invalid_video_id"}), 400

    url = f"https://www.youtube.com/watch?v={video_id}"
    job_id = uuid.uuid4().hex[:12]
    out_template = os.path.join(DOWNLOAD_DIR, f"{job_id}.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "noplaylist": True,
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
            info = ydl.extract_info(url, download=False)
            duration = info.get("duration") or 0
            if duration and duration > MAX_DURATION_SECONDS:
                return jsonify({
                    "error": "video_too_long",
                    "message": f"الفيديو طويل جداً ({int(duration/60)} دقيقة) — الحد الأقصى {MAX_DURATION_SECONDS//60} دقائق"
                }), 400

            ydl.download([url])

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
