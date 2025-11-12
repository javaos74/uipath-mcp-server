# Multi-stage build for MCP Client
FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create .chainlit directory
#RUN mkdir -p .chainlit

# Expose port
EXPOSE 8000

# Environment variables
ENV CHAINLIT_HOST=0.0.0.0
ENV CHAINLIT_PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Run Chainlit
CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8000"]
