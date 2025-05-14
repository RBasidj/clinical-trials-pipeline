FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Make directories
RUN mkdir -p cache data results figures

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Command to run the Flask app
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app