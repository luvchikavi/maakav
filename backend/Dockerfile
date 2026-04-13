FROM python:3.12-slim

WORKDIR /app

# System deps for pdf2image and python-docx
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run migrations then start server
CMD alembic upgrade head 2>/dev/null; uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
