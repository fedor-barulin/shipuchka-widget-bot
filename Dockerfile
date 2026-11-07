FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py tgwidget.py ./
COPY widgets ./widgets
ENV SESSION_PATH=/app/data/bot PYTHONUNBUFFERED=1
CMD ["python", "bot.py"]
