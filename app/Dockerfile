FROM python:3.12-slim
# Prevents Python from writing .pyc files (not needed in container)
ENV PYTHONDONTWRITEBYTECODE=1
# Ensures Python output is sent straight to terminal (for logging)
ENV PYTHONUNBUFFERED=1

# All command will run from this directory
WORKDIR /app

# System Dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application
COPY . .
RUN mkdir -p /app/logs
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]


