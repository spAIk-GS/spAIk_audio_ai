# audio_feedback/analyze_audio.py
import librosa
import numpy as np
from audio_feedback.speaking_rate import calculate_speaking_rate
from audio_feedback.asr_whisper import transcribe_audio
import os
import subprocess


def analyze_audio_features(audio_path):
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    y, sr = librosa.load(audio_path, sr=16000)

    # 1. 기존: 오디오 길이 계산
    duration = librosa.get_duration(y=y, sr=sr)

    # 2. ASR 수행: 텍스트 및 duration 받기
    transcript, asr_duration = transcribe_audio(audio_path)

    # 3. duration 값 결정 (ASR duration 없으면 librosa duration 사용)
    effective_duration = asr_duration if asr_duration > 0 else duration

    # 4. ASR 텍스트 기반 말속도 계산
    speaking_rate = calculate_speaking_rate(transcript, effective_duration)

    # 5. pitch 평균 측정
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
    pitch_values = pitches[magnitudes > np.median(magnitudes)]
    avg_pitch = np.mean(pitch_values) if len(pitch_values) > 0 else 0

    # 6. 음량 평균 (RMS)
    rms = np.mean(librosa.feature.rms(y=y))

    return {
        "duration_sec": duration,
        "transcript": transcript,
        "speaking_rate_wpm": speaking_rate,
        "avg_pitch_hz": avg_pitch,
        "avg_rms": rms
    }

def extract_audio(video_path, audio_path, sr=16000):
    os.makedirs(os.path.dirname(audio_path), exist_ok=True)

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-ac", "1", "-ar", str(sr),
        "-loglevel", "error", audio_path
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if proc.returncode != 0 or not os.path.exists(audio_path):
        raise RuntimeError(f"FFmpeg failed: {proc.stderr.strip()}")

    return audio_path
