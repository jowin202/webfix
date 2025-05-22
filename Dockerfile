FROM node:18 AS build
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

CMD wait-for-it --service db:5432 --timeout 40 && uvicorn main:app --host 0.0.0.0 --port 8000 --log-level debug --reload

