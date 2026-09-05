# Воркер Horsteppe: слушает очередь в Postgres и собирает ролики.
FROM python:3.12-slim

# fonts-dejavu-core — не украшение. Субтитры вшиваются через libass, и в
# облегчённом образе системных шрифтов нет вообще: русский текст превратится
# в пустые квадраты, причём молча, без ошибки в логах.
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ffmpeg приезжает статическим бинарником вместе с imageio-ffmpeg,
# ставить его в систему не нужно.
ENV PYTHONUNBUFFERED=1 \
    SUBTITLE_FONT_FILE=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf

CMD ["python", "main.py"]
