![Lint-free](https://github.com/nyu-software-engineering/containerized-app-exercise/actions/workflows/lint.yml/badge.svg)
![Web App CI](https://github.com/software-students-spring2025/4-containers-nbcs/actions/workflows/web-app.yml/badge.svg)
![ML Client CI](https://github.com/software-students-spring2025/4-containers-nbcs/actions/workflows/ml-client.yml/badge.svg)

# Containerized App Exercise

Build a containerized app that uses machine learning. See [instructions](./instructions.md) for details.

# Meeting Minutes Transcription System
We're making a containerized application for automatically transcribing meeting audio recordings. The system records audio from meetings, processes it using speech-to-text technology, and provides the transcribed text to users.

## Team Members

- [Jiaxi Zhang](https://github.com/SuQichen777)
- [Yilei Weng](https://github.com/ShadderD)
- [Yuquan Hu](https://github.com/N-A-E-S)
- [Henry Yu](https://github.com/ky2389)

## Prerequisites

- [Docker](https://www.docker.com/get-started) and [Docker Compose](https://docs.docker.com/compose/install/)
- Git
- Internet connection (to download the Vosk model during build)

## Getting Started

Follow these steps to set up and run the application on your local machine:

### 1. Clone the Repository

```bash
git clone https://github.com/software-students-spring2025/4-containers-nbcs
```

### 2. Set up Environment Variables

Copy the provided `.env.example` file:

```bash
cp .env.example .env
```

The default environment variables should work for most development environments.

#### Available Environment Variables

- `MONGO_URI`: MongoDB connection string (default: `mongodb://mongodb:27017/`)
- `VOSK_MODEL_PATH`: Path to the Vosk speech recognition model (default: `/app/models/vosk-model-small-en-us-0.15`)

### 3. Build and Start the Containers

```bash
docker-compose up -d --build
```

if your docker-compose version is 2.0 or above and cannot use `docker-compose` command, you can use the following command instead:

```bash
docker compose up -d --build
```

*The first build might take some time because the ML client container needs to download the Vosk speech recognition model.

### 4. Access the Application

Once all containers are running, access the web application at:

```
http://localhost:5000
```

### 5. Using the Application

1. Enter a meeting name in the input field
2. Click "Start Recording" and allow microphone access
3. Speak into your microphone
4. Click "Stop Recording" when you're finished
5. Wait for the transcription to process (this may take a moment)
6. View your transcription when it appears
7. Click "View All Recordings" to see your past transcribed meetings

## Customizing Speech Recognition

### Changing the Language Model

The system uses Vosk for speech recognition, which supports multiple languages. You can change the language model by updating the `VOSK_MODEL_PATH` environment variable in your `.env` file:

```
# Examples for other languages:
VOSK_MODEL_PATH=/app/models/vosk-model-small-es-0.42  # Spanish
VOSK_MODEL_PATH=/app/models/vosk-model-small-fr-0.22  # French
VOSK_MODEL_PATH=/app/models/vosk-model-small-de-0.15  # German
```

When changing the model, you'll need to ensure the model is downloaded into your container or mounted as a volume. You can modify the Dockerfile or docker-compose.yml to include your preferred model.

### Alternative Models

Vosk offers various models with different capabilities:

| Model Type | Description | Use Case |
|------------|-------------|----------|
| Small models | Compact size (50-100MB) | Good for most transcription needs |
| Large models | Higher accuracy (1-2GB) | When accuracy is critical |
| Speaker identification | Can identify different speakers | For multi-person meetings |

The default small English model (`vosk-model-small-en-us-0.15`) provides a good balance between accuracy and resource usage. For multi-speaker meetings, we've tested the speaker identification model (`vosk-model-spk-0.4`), but found it to be overly sensitive and always separates sentences from the same speaker incorrectly.

You can find more models on the [Vosk website](https://alphacephei.com/vosk/models).

## Development

### Running Individual Containers

If you prefer to run containers individually during development:

#### MongoDB

```bash
docker run --name mongodb -d -p 27017:27017 mongo
```

#### MongoDB through Docker

```bash
docker exec -it mongodb mongosh
```

#### Web App

```bash
cd web-app
pip install -r requirements.txt
python app.py
```

#### ML Client

```bash
cd machine-learning-client
pip install -r requirements.txt
python client.py
```

### Running Tests

#### Web App Tests

```bash
cd web-app
pytest --cov=.
```

#### ML Client Tests

```bash
cd machine-learning-client
pytest --cov=. tests/
```