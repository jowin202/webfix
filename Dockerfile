FROM node:24 AS frontend1-build
WORKDIR /build/frontend1
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build -- --configuration production


FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ .
COPY --from=frontend1-build /build/frontend1/dist/webfix/browser/ ./static/

CMD uvicorn main:app --host 0.0.0.0 --port 8000  --reload --log-level ${LOG_LEVEL:-info}
