FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for document processing (pdfplumber, Pillow, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libffi-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY api/ api/
COPY data/ data/

# Ensure upload/processed directories exist
RUN mkdir -p data/uploads data/processed

EXPOSE 5002

CMD ["gunicorn", "--bind", "0.0.0.0:5002", "--workers", "2", "--timeout", "120", "api.app:create_app()"]
