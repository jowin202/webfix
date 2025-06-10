FROM node:20 AS build
WORKDIR /app
RUN npm install -g @angular/cli
COPY frontend/ .
RUN npm install
RUN npm run build --prod


FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ .
COPY --from=build /app/dist/webfix/browser/ ./static/

CMD uvicorn main:app --host 0.0.0.0 --port 8000 --log-level debug --reload

