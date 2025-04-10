# machine-learning-client/client.py

import os
import time
import json
import base64
import io
import logging
from typing import Optional

import soundfile as sf
import numpy as np
from vosk import Model, KaldiRecognizer

from pydub import AudioSegment  # 用于自动探测并解析音频
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 读取环境变量
load_dotenv()


class AudioTranscriber:
    """Class to handle audio transcription using Vosk."""

    def __init__(self, model_path: str = "/app/models/vosk-model-small-en-us-0.15"):
        """
        Initialize the transcriber with a Vosk model.
        model_path: Vosk 模型所在目录（默认英文 small 模型）
        """
        logger.info(f"Loading Vosk model from {model_path}")
        self.model = Model(model_path)
        logger.info("Vosk model loaded successfully")

    def transcribe_audio(self, audio_data: bytes) -> str:
        """
        Transcribe audio data using Vosk, while saving the final WAV to /tmp/debug.wav.

        Args:
            audio_data: Binary audio data (e.g. WAV, MP3, M4A, OGG, etc.),
                        base64-encoded if it's a string.

        Returns:
            Transcribed text or error message (string)
        """
        try:
            # 1. 如果传入的是 base64 字符串，则先解码
            if isinstance(audio_data, str):
                audio_data = base64.b64decode(audio_data)
                logger.info(f"Decoded base64 audio data: {len(audio_data)} bytes")

            # 2. 用 pydub 自动探测格式并生成 AudioSegment
            audio_segment = AudioSegment.from_file(io.BytesIO(audio_data))

            # 3. 重采样到 16kHz
            audio_segment = audio_segment.set_frame_rate(16000)

            # 4. 导出为 WAV 到内存
            wav_buffer = io.BytesIO()
            audio_segment.export(wav_buffer, format="wav")
            wav_buffer.seek(0)

            # ==== 关键：将内存中的 WAV 落地到容器内 /tmp/debug.wav 供调试 ====
            debug_filepath = "/tmp/debug.wav"
            with open(debug_filepath, "wb") as f:
                f.write(wav_buffer.getbuffer())
            logger.info(f"Saved debug WAV to {debug_filepath}")

            # 5. 现在再把指针重置，读取数据给 soundfile
            wav_buffer.seek(0)
            data, sample_rate = sf.read(wav_buffer)

            # 如果是立体声，取第一个声道
            if data.ndim > 1:
                data = data[:, 0]

            # 转为 float32（Vosk 可以处理）
            if data.dtype != np.float32:
                data = data.astype(np.float32)

            # 初始化 KaldiRecognizer
            rec = KaldiRecognizer(self.model, sample_rate)
            rec.SetWords(True)

            chunk_size = int(sample_rate * 1.0)  # 200ms
            results = []

            for i in range(0, len(data), chunk_size):
                chunk = data[i : i + chunk_size]
                chunk_bytes = chunk.tobytes()

                if rec.AcceptWaveform(chunk_bytes):
                    part_result = json.loads(rec.Result())
                    if "text" in part_result and part_result["text"]:
                        results.append(part_result["text"])
                else:
                    # 打印一下部分识别
                    partial = json.loads(rec.PartialResult())
                    logger.debug(f"Partial: {partial}")

            # 获取最终结果
            final_result = json.loads(rec.FinalResult())
            if "text" in final_result and final_result["text"]:
                results.append(final_result["text"])

            transcript_str = " ".join(results)
            logger.info(f"Transcription result: '{transcript_str}'")
            return transcript_str

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
            # 查找数据库里 status 为 "pending" 的录音
            pending_recordings = mongodb_client.get_pending_recordings()

            for recording in pending_recordings:
                recording_id = str(recording["_id"])
                logger.info(f"Processing recording {recording_id}")

                # 把状态改为 processing
                mongodb_client.update_recording_status(recording_id, "processing")

                # 取出 audio_data
                audio_data = recording.get("audio_data", "")

                # 调用转写（会在 /tmp/debug.wav 保存调试文件）
                transcription = transcriber.transcribe_audio(audio_data)

                # 将结果保存回数据库
                mongodb_client.save_transcription(recording_id, transcription)

                logger.info(f"Completed transcription for recording {recording_id}")

            # 每隔 5 秒查一次
            time.sleep(5)

        except Exception as e:
            logger.error(f"Error processing recordings: {str(e)}")
            time.sleep(10)  # 如果出错就稍微等待再继续


if __name__ == "__main__":
    # 等待 MongoDB 服务起来
    logger.info("Waiting for services to start...")
    time.sleep(10)

    # 启动录音处理
    process_recordings()
