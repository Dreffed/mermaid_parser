# ===== Dockerfile =====
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for database
RUN mkdir -p /app/data
RUN chmod 775 /app/data

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
#ENV DATABASE_URL=sqlite://data/mermaid_converter.db

# Expose port
EXPOSE 5000

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# Run the application
CMD ["python", "app.py"]
