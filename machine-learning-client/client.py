import os
import time
import json
import base64
import io
import wave
import logging
import subprocess
import tempfile
from typing import Dict, Optional
import soundfile as sf
import numpy as np
from vosk import Model, KaldiRecognizer, SetLogLevel
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv
import wave

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

SetLogLevel(0)

load_dotenv()


class AudioTranscriber:
    """Class to handle audio transcription using Vosk."""

    def __init__(self, model_path: str = None):
        model_path = os.getenv(
            "VOSK_MODEL_PATH", "/app/models/vosk-model-small-en-us-0.15"
        )
        logger.info(f"Loading Vosk model from {model_path}")
        self.model = Model(model_path)
        logger.info("Vosk model loaded successfully")
        # Disable Vosk debug logs
        SetLogLevel(0)

    def _convert_webm_to_wav(self, webm_data: bytes) -> str:
        """
        Convert webm audio data to wav format using ffmpeg.

        Args:
            webm_data: Binary webm audio data

        Returns:
            Path to the temporary wav file
        """
        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as webm_file:
                webm_path = webm_file.name
                webm_file.write(webm_data)

            wav_path = webm_path.replace(".webm", ".wav")

            # Use ffmpeg to convert webm to wav
            command = [
                "ffmpeg",
                "-i",
                webm_path,
                "-ar",
                "16000",  # Sample rate 16kHz
                "-ac",
                "1",  # Mono
                "-f",
                "wav",  # Format
                wav_path,
            ]

            process = subprocess.run(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            # Check if conversion was successful
            if process.returncode != 0:
                logger.error(f"FFmpeg conversion error: {process.stderr.decode()}")
                raise Exception("Failed to convert webm to wav")

            # Remove the temporary webm file
            os.unlink(webm_path)

            return wav_path

        except Exception as e:
            logger.error(f"Error converting webm to wav: {str(e)}")
            raise e

    def transcribe_audio(self, audio_data: bytes) -> str:
        """
        Args:
            audio_data: Binary audio data in webm format or base64 encoded string

        Returns:
            Transcribed text
        """

        try:
            temp_wav_path = None

            # Convert base64 to bytes if needed
            if isinstance(audio_data, str):
                audio_data = base64.b64decode(audio_data)

            # Convert webm to wav
            temp_wav_path = self._convert_webm_to_wav(audio_data)

            # Open the converted wav file
            wf = open(temp_wav_path, "rb")

            # Create a wave object
            wav_file = wave.open(temp_wav_path, "rb")

            # Check if the wav file is mono PCM
            if (
                wav_file.getnchannels() != 1
                or wav_file.getsampwidth() != 2
                or wav_file.getcomptype() != "NONE"
            ):
                logger.error("Audio file must be WAV format mono PCM.")
                return "Error: Audio file must be mono PCM."

            # Create recognizer with the model
            rec = KaldiRecognizer(self.model, wav_file.getframerate())
            rec.SetWords(True)
            rec.SetPartialWords(True)

            results = []

            # Process in chunks
            while True:
                data = wav_file.readframes(4000)
                if len(data) == 0:
                    break

                if rec.AcceptWaveform(data):
                    part_result = json.loads(rec.Result())
                    if "text" in part_result and part_result["text"]:
                        results.append(part_result["text"])

            # Get the final result
            final_result = json.loads(rec.FinalResult())
            if "text" in final_result and final_result["text"]:
                results.append(final_result["text"])

            # Close files
            wav_file.close()

            # Clean up temporary file
            if temp_wav_path and os.path.exists(temp_wav_path):
                os.unlink(temp_wav_path)

            return " ".join(results)

        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")

            # Clean up temporary file on error
            if temp_wav_path and os.path.exists(temp_wav_path):
                try:
                    os.unlink(temp_wav_path)
                except:
                    pass

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
            pending_recordings = mongodb_client.get_pending_recordings()

            for recording in pending_recordings:
                recording_id = str(recording["_id"])
                logger.info(f"Processing recording {recording_id}")

                mongodb_client.update_recording_status(recording_id, "processing")

                audio_data = recording.get("audio_data", b"")

                transcription = transcriber.transcribe_audio(audio_data)

                mongodb_client.save_transcription(recording_id, transcription)

                logger.info(f"Completed transcription for recording {recording_id}")

            time.sleep(5)

        except Exception as e:
            logger.error(f"Error processing recordings: {str(e)}")
            time.sleep(10)


if __name__ == "__main__":
    logger.info("Waiting for services to start...")
    time.sleep(10)

    # Start processing recordings
    process_recordings()
