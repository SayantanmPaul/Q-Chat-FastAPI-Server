# --- Base Image (Builder Stage) ---
FROM python:3.11-slim AS builder

WORKDIR /app

# Install dependencies in a single RUN statement for efficient layer caching
RUN apt-get update && \
    apt-get install -y gcc curl && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install the required dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# --- Final Production Image ---
FROM python:3.11-slim

WORKDIR /app

# Copy built dependencies from the builder stage
COPY --from=builder /install /usr/local
# Ensure the correct path is used for installed Python packages
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy the necessary application files
COPY . .

# expose port run application command
EXPOSE 8000
CMD [ "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000" ]