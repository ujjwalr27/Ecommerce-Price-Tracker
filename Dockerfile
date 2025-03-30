FROM python:3.9-slim

# Install system dependencies required for building packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    gcc \
    g++ \
    libc-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Set up Python environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8501

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies without virtual environment
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --no-build-isolation -r requirements.txt

# Create the startup script with echo commands and make it executable
RUN echo '#!/bin/bash' > startup.sh && \
    echo 'if [ -z "$PORT" ]; then' >> startup.sh && \
    echo '  export PORT=8501' >> startup.sh && \
    echo 'fi' >> startup.sh && \
    echo 'streamlit run app/dashboard.py --server.port=$PORT --server.address=0.0.0.0' >> startup.sh && \
    chmod +x startup.sh

# Verify the script exists and is executable
RUN ls -la startup.sh

# Copy the rest of the application
COPY . .

# Expose the Streamlit port
EXPOSE 8501

# Start the application
CMD ["./startup.sh"] 