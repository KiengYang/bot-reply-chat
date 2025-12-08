FROM python:3.12-slim

# Make sure Python prints straight to stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system deps if you ever need them (optional, can be removed if not needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python deps first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your source code
COPY app app

# Copy .env if you prefer to bake it in (usually mounted instead)
# COPY .env .env

# Default command: run your bot module
CMD ["python", "-m", "app.bot"]
