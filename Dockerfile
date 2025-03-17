# 1. Используем официальный образ Python 3.12
FROM python:3.12

# 2. Устанавливаем FFmpeg
RUN apt update && apt install -y ffmpeg

# 3. Устанавливаем зависимости
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Копируем файлы бота в контейнер
COPY . .

# 5. Запускаем бота
CMD ["python", "chbot.py"]
