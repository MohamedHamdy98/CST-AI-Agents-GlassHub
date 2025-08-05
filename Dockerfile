# Use Python 3.10 slim image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies for FastAPI and cv2 if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc ffmpeg libgl1 libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Expose FastAPI default port
EXPOSE 8000

# Run FastAPI app with uvicorn (4 workers for concurrency)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
