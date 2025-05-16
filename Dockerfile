FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first to use Docker caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all files
COPY . .

# Make directories
RUN mkdir -p cache data results figures

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV PYTHONDONTWRITEBYTECODE=1
ENV REPORT_FALLBACK_ENABLED=1
ENV MAX_RETRIES=3

# Command to run the Flask app
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app