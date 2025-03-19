FROM python:3.11-slim

WORKDIR /telegram_kafka_app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONBUFFERED=1

CMD ["python3", "main.py"]