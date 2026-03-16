FROM node:20 AS frontend1-build
WORKDIR /build/frontend1
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build -- --configuration production


FROM node:20 AS frontend2-build
WORKDIR /build/frontend2
COPY frontend2/package*.json ./
RUN npm ci
COPY frontend2/ ./
RUN npm run build -- --configuration production --base-href /new/


FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ .
COPY --from=frontend1-build /build/frontend1/dist/webfix/browser/ ./static/
COPY --from=frontend2-build /build/frontend2/dist/webfix-frontend/browser/ ./static/new/

CMD uvicorn main:app --host 0.0.0.0 --port 8000  --reload --log-level ${LOG_LEVEL:-info}
