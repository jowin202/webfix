FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

CMD wait-for-it --service db:5432 --timeout 40 && uvicorn main:app --host 0.0.0.0 --port 8000 --log-level debug --reload

