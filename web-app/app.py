import os
import base64
from flask import Flask, render_template, request, jsonify, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

app = Flask(__name__)


def get_db():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://mongodb:27017/")
    client = MongoClient(mongo_uri)
    db = client.meeting_minutes
    return db


# Function to get current time with timezone offset
def get_local_time():
    """Get the current local time with timezone offset."""
    # Adjust the offset based on your timezone (UTC-4 in this case)
    timezone_offset = -4  # 4 hours behind UTC
    local_time = datetime.now() + timedelta(hours=timezone_offset)
    return local_time.strftime("%Y-%m-%d %H:%M:%S")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/recordings")
def recordings():
    db = get_db()
    recordings = list(db.recordings.find({}))
    for recording in recordings:
        recording["_id"] = str(recording["_id"])
    return render_template("recordings.html", recordings=recordings)


@app.route("/save_recording", methods=["POST"])
def save_recording():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    meeting_name = request.form.get("meeting_name", "Unnamed Meeting")

    db = get_db()
    recording_id = db.recordings.insert_one(
        {
            "meeting_name": meeting_name,
            "audio_data": base64.b64encode(audio_file.read()).decode("utf-8"),
            "status": "pending",
            "created_at": get_local_time(),
        }
    ).inserted_id

    return jsonify({"success": True, "recording_id": str(recording_id)})


@app.route("/get_transcription/<recording_id>")
def get_transcription(recording_id):
    db = get_db()
    recording = db.recordings.find_one({"_id": ObjectId(recording_id)})

    if not recording:
        return jsonify({"error": "Recording not found"}), 404

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

    if result.deleted_count == 1:
        return redirect(url_for("recordings"))
    else:
        return jsonify({"error": "Recording not found"}), 404


@app.route("/update_recording_name/<recording_id>", methods=["POST"])
def update_recording_name(recording_id):
    """update a recording name"""
    new_name = request.form.get("new_meeting_name", "").strip()
    db = get_db()

    result = db.recordings.update_one(
        {"_id": ObjectId(recording_id)}, {"$set": {"meeting_name": new_name}}
    )

    if result.modified_count == 1:
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Recording not found or no change"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
