# machine-learning-client/Dockerfile
FROM python:3.10-slim-buster

WORKDIR /app

# Install necessary dependencies for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "client.py"]