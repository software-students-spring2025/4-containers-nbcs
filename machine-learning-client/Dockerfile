FROM python:3.10

WORKDIR /app

# Install necessary dependencies including build essentials and toolchain
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    libatomic1 \
    libstdc++6 \
    build-essential \
    gcc \
    g++ \
    python3-dev \
    ffmpeg \  
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Force reinstall of vosk with specific options for this environment
RUN pip uninstall -y vosk || true
RUN pip install --no-cache-dir --force-reinstall vosk

# Install other requirements
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "client.py"]