# web-app/test_app.py
import unittest
import json
import io
from unittest.mock import patch, MagicMock
from bson.objectid import ObjectId
import pytest
from app import app


class TestApp(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    @patch("app.get_db")
    def test_index_route(self, mock_get_db):
        # Test index route
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<!DOCTYPE html>", response.data)
        self.assertIn(b"Meeting Minutes Recorder", response.data)

    @patch("app.get_db")
    def test_recordings_route_with_data(self, mock_get_db):
        # Mock database response with sample recording data
        mock_recordings = [
            {
                "_id": ObjectId("6071b3b9c36d2a144cfe0372"),
                "meeting_name": "Test Meeting",
                "audio_data": "base64audiodata",
                "transcription": "Test transcription",
                "created_at": "20240101",
            }
        ]
        mock_db = MagicMock()
        mock_db.recordings.find.return_value = mock_recordings
        mock_get_db.return_value = mock_db

        # Test recordings route
        response = self.client.get("/recordings")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Meeting", response.data)
        self.assertIn(b"Test transcription", response.data)

    @patch("app.get_db")
    def test_recordings_route_empty(self, mock_get_db):
        # Mock empty database response
        mock_db = MagicMock()
        mock_db.recordings.find.return_value = []
        mock_get_db.return_value = mock_db

        # Test recordings route with no data
        response = self.client.get("/recordings")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No recordings found", response.data)

    @patch("app.get_db")
    def test_get_transcription_not_found(self, mock_get_db):
        # Mock database response for non-existent recording
        mock_db = MagicMock()
        mock_db.recordings.find_one.return_value = None
        mock_get_db.return_value = mock_db

        # Test get_transcription route for non-existent recording
        response = self.client.get("/get_transcription/6071b3b9c36d2a144cfe0372")

        self.assertEqual(response.status_code, 404)
        json_data = json.loads(response.data)
        self.assertIn("error", json_data)


if __name__ == "__main__":
    unittest.main()
