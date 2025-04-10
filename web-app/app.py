# web-app/app.py
import os
import base64
from flask import Flask, render_template, request, jsonify, redirect, url_for
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


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/recordings")
def recordings():
    db = get_db()
    # Get all recordings that have transcriptions
    recordings = list(db.recordings.find({"transcription": {"$exists": True}}))
    for recording in recordings:
        recording["_id"] = str(recording["_id"])
    return render_template("recordings.html", recordings=recordings)


@app.route("/save_recording", methods=["POST"])
def save_recording():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    meeting_name = request.form.get("meeting_name", "Unnamed Meeting")

    # Save audio to MongoDB
    db = get_db()
    recording_id = db.recordings.insert_one(
        {
            "meeting_name": meeting_name,
            "audio_data": base64.b64encode(audio_file.read()).decode("utf-8"),
            "status": "pending",  # pending, processing, completed
            "created_at": str(ObjectId())[
                :8
            ],  # Use first 8 chars of ObjectId as timestamp
        }
    ).inserted_id

    return jsonify({"success": True, "recording_id": str(recording_id)})


@app.route("/get_transcription/<recording_id>")
def get_transcription(recording_id):
    db = get_db()
    recording = db.recordings.find_one({"_id": ObjectId(recording_id)})

    if not recording:
        return jsonify({"error": "Recording not found"}), 404

    # Check if transcription exists
    if "transcription" in recording:
        return jsonify(
            {
                "success": True,
                "status": "completed",
                "transcription": recording["transcription"],
            }
        )
    else:
        return jsonify({"success": True, "status": recording.get("status", "pending")})

@app.route("/delete_recording/<recording_id>", methods=["POST"])
def delete_recording(recording_id):
    """delete a recording"""
    db = get_db()
    result = db.recordings.delete_one({"_id": ObjectId(recording_id)})
    
    # 这里可以根据前端的需求决定返回什么：
    # 1. 返回 JSON
    # 2. 或者跳转到 /recordings
    if result.deleted_count == 1:
        # 如果删除成功，重定向回录音列表
        return redirect(url_for("recordings"))
    else:
        # 如果没找到或删除失败，返回 404
        return jsonify({"error": "Recording not found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
