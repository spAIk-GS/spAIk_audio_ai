# audio_feedback/speaking_rate.py
import librosa
import os

def calculate_speaking_rate(asr_text: str, duration_sec: float) -> float:
    """
    ASR 텍스트와 음성 길이(초)를 받아 말속도(분당 단어 수)를 계산
    """
    word_count = len(asr_text.strip().split())
    if duration_sec <= 0:
        return 0.0
    wpm = (word_count / duration_sec) * 60
    return wpm