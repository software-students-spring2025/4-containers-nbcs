# machine-learning-client/tests/test_client.py
import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add the parent directory to the path so we can import the client module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client import AudioTranscriber, MongoDBClient, process_recordings


class TestAudioTranscriber(unittest.TestCase):
    @patch("client.subprocess.run")
    @patch("client.wave.open")
    @patch("client.open", create=True)
    @patch("client.Model")
    def test_transcribe_audio(
        self, mock_model_class, mock_open_builtin, mock_wave_open, mock_subprocess_run
    ):
        mock_subprocess_run.return_value.returncode = 0

        mock_wave_file = MagicMock()
        mock_wave_file.getnchannels.return_value = 1
        mock_wave_file.getsampwidth.return_value = 2
        mock_wave_file.getcomptype.return_value = "NONE"
        mock_wave_file.getframerate.return_value = 16000
        mock_wave_file.readframes.side_effect = [b"audio", b""]

        mock_wave_open.return_value = mock_wave_file

        mock_recognizer = MagicMock()
        mock_recognizer.AcceptWaveform.return_value = True
        mock_recognizer.Result.return_value = '{"text": "hello"}'
        mock_recognizer.FinalResult.return_value = '{"text": "world"}'

        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        with patch("client.KaldiRecognizer", return_value=mock_recognizer):
            transcriber = AudioTranscriber(model_path="/fake/model/path")
            result = transcriber.transcribe_audio(b"fake webm data")

        self.assertEqual(result, "hello world")

    # test for ffmpeg conversion
    @patch("client.Model")
    @patch("client.subprocess.run")
    @patch("client.tempfile.NamedTemporaryFile")
    def test_convert_webm_to_wav_ffmpeg_failure(
        self, mock_tempfile, mock_run, mock_model
    ):
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr.decode.return_value = "ffmpeg error"

        fake_temp = MagicMock()
        fake_temp.name = "/tmp/test.webm"
        mock_tempfile.return_value.__enter__.return_value = fake_temp

        transcriber = AudioTranscriber()

        with self.assertRaises(Exception) as context:
            transcriber._convert_webm_to_wav(b"invalid webm")

        self.assertIn("Failed to convert webm to wav", str(context.exception))

    # test for wav file format
    @patch("client.AudioTranscriber._convert_webm_to_wav", return_value="/tmp/fake.wav")
    @patch("client.wave.open")
    @patch("client.open", create=True)
    @patch("client.Model")
    def test_transcribe_audio_invalid_format(
        self, mock_model_class, mock_open_builtin, mock_wave_open, mock_convert
    ):
        mock_wave_file = MagicMock()
        mock_wave_file.getnchannels.return_value = 2
        mock_wave_file.getsampwidth.return_value = 2
        mock_wave_file.getcomptype.return_value = "NONE"
        mock_wave_open.return_value = mock_wave_file

        transcriber = AudioTranscriber()
        result = transcriber.transcribe_audio(b"fake webm")

        self.assertIn("Error: Audio file must be mono PCM", result)


class TestMongoDBClient(unittest.TestCase):
    @patch("client.MongoClient")
    def test_get_pending_recordings(self, mock_mongo_client):
        # Set up mock MongoDB client
        mock_db = MagicMock()
        mock_mongo_client.return_value.meeting_minutes = mock_db

        # Create MongoDB client instance
        mongodb_client = MongoDBClient(uri="mongodb://test:27017/")

        # Test get_pending_recordings
        mongodb_client.get_pending_recordings()

        # Assertions
        mock_db.recordings.find.assert_called_once_with({"status": "pending"})

    @patch("client.MongoClient")
    @patch("client.ObjectId")
    def test_update_recording_status(self, mock_object_id, mock_mongo_client):
        # Set up mock MongoDB client
        mock_db = MagicMock()
        mock_mongo_client.return_value.meeting_minutes = mock_db
        mock_object_id.return_value = "test_id"

        # Create MongoDB client instance
        mongodb_client = MongoDBClient()

        # Test update_recording_status
        mongodb_client.update_recording_status("123", "processing")

        # Assertions
        mock_db.recordings.update_one.assert_called_once_with(
            {"_id": "test_id"}, {"$set": {"status": "processing"}}
        )

    @patch("client.MongoClient")
    @patch("client.ObjectId")
    def test_save_transcription(self, mock_object_id, mock_mongo_client):
        # Set up mock MongoDB client
        mock_db = MagicMock()
        mock_mongo_client.return_value.meeting_minutes = mock_db
        mock_object_id.return_value = "test_id"

        # Create MongoDB client instance
        mongodb_client = MongoDBClient()

        # Test save_transcription
        mongodb_client.save_transcription("123", "test transcription")

        # Assertions
        mock_db.recordings.update_one.assert_called_once_with(
            {"_id": "test_id"},
            {"$set": {"transcription": "test transcription", "status": "completed"}},
        )


class TestProcessRecordings(unittest.TestCase):
    @patch("client.MongoDBClient")
    @patch("client.AudioTranscriber")
    @patch("client.time.sleep", return_value=None)
    def test_process_recordings_single_run(
        self, mock_sleep, mock_transcriber_class, mock_mongo_class
    ):
        fake_recording = {
            "_id": "507f1f77bcf86cd799439011",
            "audio_data": "ZmFrZSBhdWRpbw==",  # base64 of "fake audio"
            "status": "pending",
        }

        # mock MongoDB client
        mock_mongo = MagicMock()
        mock_mongo.get_pending_recordings.side_effect = [
            [fake_recording],
            KeyboardInterrupt(),
        ]
        mock_mongo_class.return_value = mock_mongo

        # mock Transcriber
        mock_transcriber = MagicMock()
        mock_transcriber.transcribe_audio.return_value = "transcribed text"
        mock_transcriber_class.return_value = mock_transcriber

        try:
            process_recordings()
        except KeyboardInterrupt:  # Only Try Once
            pass

        mock_mongo.get_pending_recordings.assert_called()
        mock_mongo.update_recording_status.assert_called_with(
            "507f1f77bcf86cd799439011", "processing"
        )
        mock_transcriber.transcribe_audio.assert_called_once()
        mock_mongo.save_transcription.assert_called_with(
            "507f1f77bcf86cd799439011", "transcribed text"
        )


if __name__ == "__main__":
    unittest.main()
