from flask import Flask, request, jsonify, Response
from werkzeug.utils import secure_filename
import os
import time
import math
import datetime
import json
import torch

# 오디오 추출 및 분석 관련 모듈 임포트 (예상 경로)
from audio_feedback.extract_audio import extract_audio_from_video
from audio_feedback.analyze_audio import analyze_audio_features
from audio_feedback.stuttering_detector import detect_stuttering
from audio_feedback.feedback_generator import generate_audio_feedback


app = Flask(__name__)

# 업로드된 영상 파일을 저장할 폴더와 임시 오디오 파일을 저장할 폴더를 설정합니다.
UPLOAD_FOLDER = 'uploads'
TEMP_AUDIO_FOLDER = 'temp_audio'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMP_AUDIO_FOLDER, exist_ok=True)

def generate_analysis_id(video_id: str, analysis_type: str) -> str:
    """
    영상 ID, 분석 타입, 현재 타임스탬프를 조합하여 고유한 분석 ID를 생성합니다.
    """
    current_timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    analysis_id = f"{video_id}_{analysis_type}_{current_timestamp}"
    return analysis_id

def convert_rms_to_db(rms_value):
    """
    RMS 값을 데시벨(dB)로 변환합니다.
    0 이하의 RMS 값은 로그 오류를 방지하기 위해 매우 낮은 값으로 처리합니다.
    """
    if rms_value <= 0:
        return -120.0
    return 20 * math.log10(rms_value)

@app.route('/analysis/audio', methods=['POST'])
def analyze_video_api():
    """
    POST 요청으로 비디오 파일을 받아 AI 면접 피드백을 생성하는 API 엔드포인트입니다.
    """
    if 'video' not in request.files:
        return jsonify({"error": "No video file provided"}), 400

    video_file = request.files['video']
    if video_file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    timestamp = int(time.time())
    original_filename, file_extension = os.path.splitext(video_file.filename)
    unique_filename = f"{original_filename}_{timestamp}{file_extension}"
    video_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    
    video_id = original_filename
    audio_filename = f"{original_filename}_{timestamp}.wav"
    extracted_audio_path = os.path.join(TEMP_AUDIO_FOLDER, audio_filename)
    
    try:
        video_file.save(video_path)
        print(f"영상 파일 저장 완료: {video_path}")

        # 3. 오디오를 추출하고 임시 파일로 저장합니다.
        extract_audio_from_video(video_path, extracted_audio_path)
        print("오디오 추출 완료")

        # 4. 오디오 분석 (말 속도, 음의 높낮이, 음량) 및 STT를 수행합니다.
        features = analyze_audio_features(extracted_audio_path)
        transcript = features.get("transcript", "")
        print("오디오 분석 완료")

        # 5. 말더듬(멈칫거림) 횟수를 감지합니다.
        stuttering_analysis_results = detect_stuttering(extracted_audio_path)
        print("말더듬 분석 완료")
        
        # 6. 오디오 특성들을 종합한 피드백 메시지를 생성합니다.
        avg_rms_value = features.get('avg_rms')
        avg_rms_db = 'N/A'
        if avg_rms_value is not None:
            try:
                avg_rms_float = float(avg_rms_value)
                if avg_rms_float > 0.0:
                    avg_rms_db = convert_rms_to_db(avg_rms_float)
                else:
                    avg_rms_db = -120.0
            except (ValueError, TypeError):
                print("경고: 'avg_rms' 값을 float로 변환하는 데 실패했습니다.")
                avg_rms_db = 'N/A'
        
        audio_feedback_results = generate_audio_feedback(features, avg_rms_db)
        
        # 7. 최종 분석 결과를 JSON 형식에 맞춰 재구성합니다.
        final_feedback = {
            "analysisId": generate_analysis_id(video_id, "full_report"),
            "videoId": video_id,
            "results": {
                "speed": {
                    "feedback": audio_feedback_results.get("speed_feedback", ""),
                    "value": round(float(features.get("speaking_rate_wpm", 0.0)), 2)
                },
                "pitch": {
                    "feedback": audio_feedback_results.get("pitch_feedback", ""),
                    "value": round(float(features.get("avg_pitch_hz", 0.0)), 2)
                },
                "volume": {
                    "feedback": audio_feedback_results.get("volume_feedback", ""),
                    "decibels": round(float(avg_rms_db) if isinstance(avg_rms_db, (float, int)) else 0.0, 2)
                },
                "stutter": {
                    "feedback": stuttering_analysis_results.get('stuttering_feedback', 'N/A'),
                    "stutter_count": stuttering_analysis_results.get('stutter_count', 0)
                },
            }
        }

        # JSON 응답을 명시적으로 생성하여 반환. 한글 깨짐을 방지합니다.
        response_json = json.dumps(final_feedback, ensure_ascii=False)
        return Response(response_json, mimetype='application/json')

    except Exception as e:
        print(f"분석 중 오류 발생: {e}")
        return jsonify({"error": f"분석 중 오류가 발생했습니다: {e}"}), 500
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(extracted_audio_path):
            os.remove(extracted_audio_path)
        print("임시 파일 삭제 완료")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
