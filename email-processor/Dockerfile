# Email Processor Dockerfile
FROM python:3.11

# Install system dependencies including Chromium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p downloads logs config/extracted

# Set environment variables
ENV PYTHONPATH=/app/src
ENV DISPLAY=:99

# Create a non-root user
RUN useradd -m -u 1000 emailprocessor && \
    chown -R emailprocessor:emailprocessor /app

USER emailprocessor

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.path.append('/app/src'); from config.config import config; print('Health check passed')" || exit 1

# Default command
CMD ["python", "src/main.py", "--mode", "continuous", "--interval", "30"]
