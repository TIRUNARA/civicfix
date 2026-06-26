FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose dynamic Port injected by Google Cloud Run
ENV PORT=8080
ENV DB_PATH=/tmp/civicfix.db

CMD uvicorn main:app --host 0.0.0.0 --port $PORT
