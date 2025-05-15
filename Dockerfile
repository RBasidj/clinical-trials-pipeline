## File: Dockerfile
## Location: Complete replacement

FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Make directories
RUN mkdir -p cache data results figures cache/finance

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/servicekey.json

# Command to run the Flask app
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app