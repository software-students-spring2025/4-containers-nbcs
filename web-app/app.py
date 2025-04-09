# web-app/app.py
import os
import base64
from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# MongoDB connection
def get_db():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://mongodb:27017/")
    client = MongoClient(mongo_uri)
    db = client.meeting_minutes
    return db

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recordings')
def recordings():
    db = get_db()
    # Get all recordings that have transcriptions
    recordings = list(db.recordings.find({"transcription": {"$exists": True}}))
    for recording in recordings:
        recording['_id'] = str(recording['_id'])
    return render_template('recordings.html', recordings=recordings)

@app.route('/save_recording', methods=['POST'])
def save_recording():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    audio_file = request.files['audio']
    meeting_name = request.form.get('meeting_name', 'Unnamed Meeting')
    
    # Save audio to MongoDB
    db = get_db()
    recording_id = db.recordings.insert_one({
        "meeting_name": meeting_name,
        "audio_data": base64.b64encode(audio_file.read()).decode('utf-8'),
        "status": "pending",  # pending, processing, completed
        "created_at": str(ObjectId())[:8]  # Use first 8 chars of ObjectId as timestamp
    }).inserted_id
    
    return jsonify({"success": True, "recording_id": str(recording_id)})

@app.route('/get_transcription/<recording_id>')
def get_transcription(recording_id):
    db = get_db()
    recording = db.recordings.find_one({"_id": ObjectId(recording_id)})
    
    if not recording:
        return jsonify({"error": "Recording not found"}), 404
    
    # Check if transcription exists
    if "transcription" in recording:
        return jsonify({
            "success": True,
            "status": "completed",
            "transcription": recording["transcription"]
        })
    else:
        return jsonify({
            "success": True,
            "status": recording.get("status", "pending")
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)