FROM python:3.12-slim

WORKDIR /app

# System deps: postgres, PDF tools, LibreOffice for docx→pdf
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc poppler-utils libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "start.py"]
