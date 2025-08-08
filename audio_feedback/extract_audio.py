# audio_feedback/extract_audio.py
import os
import ffmpeg

def extract_audio_from_video(video_path, output_audio_path):
    try:
        (
            ffmpeg
            .input(video_path)
            .output(output_audio_path, format='wav', acodec='pcm_s16le', ac=1, ar='16000')
            .overwrite_output()
            .run(quiet=True)
        )
        return output_audio_path
    except ffmpeg.Error as e:
        print("FFmpeg error:", e)
        return None