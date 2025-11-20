# Multi-stage build for Trading Bot
FROM python:3.10-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.10-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 trader && \
    mkdir -p /opt/trading-bot && \
    chown -R trader:trader /opt/trading-bot

# Copy Python packages from builder
COPY --from=builder /root/.local /home/trader/.local

# Set working directory
WORKDIR /opt/trading-bot

# Copy application code
COPY --chown=trader:trader . .

# Set environment variables
ENV PATH=/home/trader/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER trader

# Create necessary directories
RUN mkdir -p logs data backtest_results

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command
CMD ["python", "main.py"]
