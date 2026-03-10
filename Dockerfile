FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY laws/ /app/laws/
COPY scripts/ /app/scripts/

CMD ["python", "scripts/ingest_laws.py"]
