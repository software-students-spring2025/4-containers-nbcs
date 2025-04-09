# machine-learning-client/tests/test_client.py
import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add the parent directory to the path so we can import the client module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client import AudioTranscriber, MongoDBClient


class TestAudioTranscriber(unittest.TestCase):
    @patch('client.Model')
    @patch('client.KaldiRecognizer')
    @patch('client.sf')
    def test_transcribe_audio(self, mock_sf, mock_recognizer, mock_model):
        # Set up mock for soundfile
        mock_sf.read.return_value = (MagicMock(), 16000)
        
        # Set up mock for KaldiRecognizer
        mock_rec_instance = MagicMock()
        mock_rec_instance.AcceptWaveform.return_value = True
        mock_rec_instance.Result.return_value = json.dumps({"text": "hello world"})
        mock_rec_instance.FinalResult.return_value = json.dumps({"text": "final result"})
        mock_recognizer.return_value = mock_rec_instance
        
        # Create transcriber instance
        transcriber = AudioTranscriber()
        
        # Test transcription
        result = transcriber.transcribe_audio(b'test_audio_data')
        
        # Assertions
        self.assertEqual(result, "hello world final result")
        mock_sf.read.assert_called_once()
        mock_rec_instance.AcceptWaveform.assert_called()
        mock_rec_instance.Result.assert_called()
        mock_rec_instance.FinalResult.assert_called_once()


class TestMongoDBClient(unittest.TestCase):
    @patch('client.MongoClient')
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
    
    @patch('client.MongoClient')
    @patch('client.ObjectId')
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
            {"_id": "test_id"},
            {"$set": {"status": "processing"}}
        )
    
    @patch('client.MongoClient')
    @patch('client.ObjectId')
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
            {"$set": {"transcription": "test transcription", "status": "completed"}}
        )


if __name__ == '__main__':
    unittest.main()