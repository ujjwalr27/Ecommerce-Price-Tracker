FROM python:3.9-slim

# Install system dependencies required for building aiohttp and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    gcc \
    g++ \
    libc-dev \
    make \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV NIXPACKS_PATH=/opt/venv/bin:$NIXPACKS_PATH

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first for better caching
COPY requirements.txt .

# Pre-compile wheels for problematic packages
RUN pip install --upgrade pip wheel setuptools
RUN pip install --upgrade cython
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . /app/

# Create non-root user for security
RUN adduser --disabled-password --gecos "" appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose the Streamlit port
EXPOSE 8501

# Start the application
CMD ["streamlit", "run", "app/dashboard.py"] 