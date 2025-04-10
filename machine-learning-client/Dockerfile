# machine-learning-client/Dockerfile
FROM python:3.10-slim-buster

WORKDIR /app

# Install necessary dependencies for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directory for Vosk model
RUN mkdir -p /app/models

# Download a small English model
RUN mkdir -p /app/models/vosk-model-small-en-us-0.15 && \
    apt-get update && apt-get install -y wget unzip && \
    wget -q -O model.zip https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip && \
    unzip model.zip -d /app/models && \
    rm model.zip && \
    apt-get purge -y wget unzip && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

COPY . .

CMD ["python", "client.py"]