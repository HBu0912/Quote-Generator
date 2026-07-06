FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data

ENV PORT=8080
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 120 app:app
