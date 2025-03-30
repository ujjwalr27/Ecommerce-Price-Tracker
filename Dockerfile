FROM python:3.9-slim

# Install system dependencies required for building packages
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

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies without using a virtual environment
# Use a simpler approach that's less prone to path/activation issues
RUN pip install --upgrade pip wheel setuptools cython && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the Streamlit port
EXPOSE 8501

# Start the application
CMD ["streamlit", "run", "app/dashboard.py"] 