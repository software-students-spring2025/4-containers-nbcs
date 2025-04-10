# machine-learning-client/client.py

import os
import time
import json
import base64
import io
import wave
import logging
from typing import Optional

from vosk import Model, KaldiRecognizer, SetLogLevel
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 禁用 vosk 内部日志（可选）
SetLogLevel(0)

# 读取环境变量
load_dotenv()


class AudioTranscriber:
    """使用 Vosk 来转写 WAV 音频的类。"""

    def __init__(self, model_path: str = "/app/models/vosk-model-small-en-us-0.15"):
        """
        初始化转写器，加载 Vosk 模型。
        model_path: Vosk 模型所在目录
        """
        logger.info(f"Loading Vosk model from {model_path}")
        self.model = Model(model_path)
        logger.info("Vosk model loaded successfully")

    def transcribe_audio(self, audio_data: bytes) -> str:
        """
        转写传入的 audio_data（假设是 WAV 格式，mono, 16-bit PCM）。
        会先将二进制写入 /tmp/debug.wav，然后用 wave 模块按块读取并进行识别。

        如果音频格式不符合要求，将返回错误信息字符串。
        """

        try:
            # 如果传入的是 base64 字符串，则先解码
            if isinstance(audio_data, str):
                audio_data = base64.b64decode(audio_data)
                logger.info(f"Decoded base64 audio data: {len(audio_data)} bytes")

            # 将音频写到 debug WAV（如果不是 WAV 格式 mono PCM，则后面会检查出错）
            debug_filepath = "/tmp/debug.wav"
            with open(debug_filepath, "wb") as f:
                f.write(audio_data)
            logger.info(f"Saved debug WAV to {debug_filepath}")

            # 用 wave.open 打开文件
            wf = wave.open(debug_filepath, "rb")

            # 检查 WAV 是否为单声道、16-bit PCM
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
                err_msg = "Audio file must be WAV format mono PCM (16-bit)."
                logger.error(err_msg)
                wf.close()
                return err_msg

            # 初始化识别器
            rec = KaldiRecognizer(self.model, wf.getframerate())
            rec.SetWords(True)

            partial_transcripts = []
            final_transcript = ""

            # 逐段读取音频并识别
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break

                if rec.AcceptWaveform(data):
                    # 中间输出完整识别结果
                    text = json.loads(rec.Result()).get("text", "")
                    if text:
                        partial_transcripts.append(text)
                        logger.debug(f"✅ Interim result: {text}")
                else:
                    # 仅在调试级别输出 partial
                    partial_text = json.loads(rec.PartialResult()).get("partial", "")
                    logger.debug(f"⏳ Partial: {partial_text}")

            wf.close()

            # 打印并获取最终识别结果
            final_text = json.loads(rec.FinalResult()).get("text", "")
            final_transcript = " ".join([*partial_transcripts, final_text]).strip()
            logger.info(f"🟢 Final transcription: {final_transcript}")

            return final_transcript

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

                # 取出 audio_data（应保证是 WAV 格式 mono PCM）
                audio_data = recording.get("audio_data", b"")

                # 调用转写
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
