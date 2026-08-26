FROM python:3.11-slim

# ffmpeg ضروري لـ yt-dlp عشان يحوّل الصوت المحمّل لصيغة MP3
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} --timeout 120 app:app"]
