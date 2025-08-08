#audio_feedback/asr_whisper.py
import whisper
import torch

def load_model():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = whisper.load_model("base", device=device)  # device 여기서 지정
    return model

model = load_model()

def transcribe_audio(audio_path):
    # device 파라미터 제거
    result = model.transcribe(audio_path)
    text = result["text"]
    duration = result["segments"][-1]["end"] if result["segments"] else 0
    return text, duration