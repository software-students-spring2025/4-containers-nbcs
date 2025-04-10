# machine-learning-client/client.py
import os
import time
import json
import base64
import io
import logging
from typing import Dict, Optional
import soundfile as sf
import numpy as np
from vosk import Model, KaldiRecognizer
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class AudioTranscriber:
    """Class to handle audio transcription using Vosk."""

    def __init__(self, model_path: str = "/app/models/vosk-model-small-en-us-0.15"):
        """Initialize the transcriber with a Vosk model."""
        logger.info(f"Loading Vosk model from {model_path}")
        self.model = Model(model_path)
        logger.info("Vosk model loaded successfully")

    def transcribe_audio(self, audio_data: bytes) -> str:
        """
        Transcribe audio data using Vosk.

        Args:
            audio_data: Binary audio data

        Returns:
            Transcribed text
        """
        try:
            # Convert base64 to bytes if needed
            if isinstance(audio_data, str):
                audio_data = base64.b64decode(audio_data)

            # Load audio data using soundfile
            with io.BytesIO(audio_data) as audio_file:
                data, sample_rate = sf.read(audio_file)

                if data.ndim > 1:
                    data = data[:, 0]  # Use only the first channel if stereo

                # Make sure data is float32 for Vosk
                if data.dtype != np.float32:
                    data = data.astype(np.float32)

            # Create recognizer with the model
            rec = KaldiRecognizer(self.model, sample_rate)
            rec.SetWords(True)

            # Process in chunks to avoid memory issues
            chunk_size = int(sample_rate * 0.2)  # 200ms chunks
            results = []

            for i in range(0, len(data), chunk_size):
                chunk = data[i : i + chunk_size]
                if rec.AcceptWaveform(chunk):
                    part_result = json.loads(rec.Result())
                    if "text" in part_result and part_result["text"]:
                        results.append(part_result["text"])

            # Get the final result
            final_result = json.loads(rec.FinalResult())
            if "text" in final_result and final_result["text"]:
                results.append(final_result["text"])

            return " ".join(results)

        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            return f"Error transcribing audio: {str(e)}"


class MongoDBClient:
    """Class to handle MongoDB operations."""

    def __init__(self, uri: str = None):
        """Initialize the MongoDB client."""
        self.uri = uri or os.getenv("MONGO_URI", "mongodb://mongodb:27017/")
        logger.info(f"Connecting to MongoDB at {self.uri}")
        self.client = MongoClient(self.uri)
        self.db = self.client.meeting_minutes
        logger.info("Connected to MongoDB")

    def get_pending_recordings(self):
        """Get recordings that need to be transcribed."""
        return self.db.recordings.find({"status": "pending"})

    def update_recording_status(self, recording_id: str, status: str):
        """Update the status of a recording."""
        self.db.recordings.update_one(
            {"_id": ObjectId(recording_id)}, {"$set": {"status": status}}
        )

    def save_transcription(self, recording_id: str, transcription: str):
        """Save the transcription for a recording."""
        self.db.recordings.update_one(
            {"_id": ObjectId(recording_id)},
            {"$set": {"transcription": transcription, "status": "completed"}},
        )


def process_recordings():
    """Main function to process pending recordings."""
    mongodb_client = MongoDBClient()
    transcriber = AudioTranscriber()

    logger.info("Starting to process recordings")

    while True:
        try:
            # Get pending recordings
            pending_recordings = mongodb_client.get_pending_recordings()

            for recording in pending_recordings:
                recording_id = str(recording["_id"])
                logger.info(f"Processing recording {recording_id}")

                # Update status to processing
                mongodb_client.update_recording_status(recording_id, "processing")

                # Get audio data
                audio_data = recording.get("audio_data", "")

                # Transcribe audio
                transcription = transcriber.transcribe_audio(audio_data)

                # Save transcription
                mongodb_client.save_transcription(recording_id, transcription)

                logger.info(f"Completed transcription for recording {recording_id}")

            # Sleep before checking for new recordings
            time.sleep(5)

        except Exception as e:
            logger.error(f"Error processing recordings: {str(e)}")
            time.sleep(10)  # Sleep longer if there was an error


if __name__ == "__main__":
    # Wait a bit for MongoDB to start up
    logger.info("Waiting for services to start...")
    time.sleep(10)

    # Start processing recordings
    process_recordings()
