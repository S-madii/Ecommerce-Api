# 1. Official lightweight Python runtime
FROM python:3.12-slim

# 2. Prevent Python from buffering stdout/stderr and writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 3. Set container working directory
WORKDIR /app

# 4. Install curl for Docker healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 5. Install dependencies as a cached layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy application source code
COPY . .

# 7. Expose default port
EXPOSE 8000

# 8. Default command for API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]