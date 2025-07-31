FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies for visualization and reporting
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create export directory
RUN mkdir -p /tmp/rsai-exports

# Create non-root user
RUN groupadd -r rsai && useradd -r -g rsai rsai
RUN chown -R rsai:rsai /app /tmp/rsai-exports
USER rsai

# Expose port
EXPOSE 8005

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8005/health || exit 1

# Run application
CMD ["python", "-m", "app.main"]