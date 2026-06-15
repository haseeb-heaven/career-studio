FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for python-docx, pdfplumber, etc.
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data directory for SQLite database
RUN mkdir -p /data

ENV DATABASE_URL=sqlite:////data/career_studio.db
ENV PORT=8000

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
