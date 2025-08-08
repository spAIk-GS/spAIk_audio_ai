import os
import time
import math
import datetime
import json
import torch
from flask import Flask, request, jsonify, Response
from werkzeug.datastructures import FileStorage

# 오디오 추출 및 분석 관련 모듈 임포트 (가상 모듈)
# 실제 프로젝트에서는 이 파일들이 같은 경로에 있거나 PYTHONPATH에 추가되어 있어야 합니다.
from audio_feedback.extract_audio import extract_audio_from_video
from audio_feedback.analyze_audio import analyze_audio_features
from audio_feedback.stuttering_detector import detect_stuttering
from audio_feedback.feedback_generator import generate_audio_feedback

# Gemini 텍스트 피드백 생성 모듈 임포트 (가상 모듈)
from answer_feedback.ai_feedback import generate_feedback_no_question

# -- 서버 및 분석 관련 설정 --
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
TEMP_AUDIO_FOLDER = 'temp_audio'
ANALYSIS_RESULTS_FOLDER = 'analysis_results' # ❗❗❗ 분석 결과를 저장할 새 폴더를 정의합니다.

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMP_AUDIO_FOLDER, exist_ok=True)
os.makedirs(ANALYSIS_RESULTS_FOLDER, exist_ok=True) # ❗❗❗ 분석 결과 폴더가 없으면 생성합니다.

def generate_analysis_id(video_id: str, analysis_type: str) -> str:
    """영상 ID, 분석 타입, 현재 타임스탬프를 조합하여 고유한 분석 ID를 생성합니다."""
    current_timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    analysis_id = f"{video_id}_{analysis_type}_{current_timestamp}"
    return analysis_id

def convert_rms_to_db(rms_value):
    """RMS 값을 데시벨(dB)로 변환합니다."""
    if rms_value <= 0:
        return -120.0
    return 20 * math.log10(rms_value)

def process_video_for_feedback(video_file_path: str, video_id: str) -> dict:
    """
    영상 파일 경로를 받아 오디오를 추출하고 분석하여 최종 피드백 딕셔너리를 반환합니다.
    이 함수는 서버 요청과 관계없이 독립적으로 호출될 수 있습니다.
    """
    audio_filename = f"{video_id}_{int(time.time())}.wav"
    extracted_audio_path = os.path.join(TEMP_AUDIO_FOLDER, audio_filename)

    try:
        # 오디오를 추출하고 임시 파일로 저장합니다.
        extract_audio_from_video(video_file_path, extracted_audio_path)
        print("오디오 추출 완료")

        # 오디오 분석 (말 속도, 음의 높낮이, 음량) 및 STT를 수행합니다.
        features = analyze_audio_features(extracted_audio_path)
        transcript = features.get("transcript", "")
        print("오디오 분석 완료")

        # 말더듬(멈칫거림) 횟수를 감지합니다.
        stuttering_analysis_results = detect_stuttering(extracted_audio_path)
        print("말더듬 분석 완료")

        # 오디오 특성들을 종합한 피드백 메시지를 생성합니다.
        avg_rms_value = features.get('avg_rms')
        avg_rms_db = 'N/A'
        if avg_rms_value is not None:
            try:
                avg_rms_float = float(avg_rms_value)
                avg_rms_db = convert_rms_to_db(avg_rms_float)
            except (ValueError, TypeError):
                print("경고: 'avg_rms' 값을 float로 변환하는 데 실패했습니다.")
        
        audio_feedback_results = generate_audio_feedback(features, avg_rms_db)
        
        # Gemini 모델을 사용하여 텍스트 답변 내용에 대한 피드백을 생성합니다.
        if transcript.strip():
            text_feedback = generate_feedback_no_question(transcript)
        else:
            text_feedback = "답변 텍스트가 없어 Gemini 피드백을 생성하지 않습니다."
        
        # 최종 분석 결과를 JSON 형식에 맞춰 재구성합니다.
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
                "content_summary": text_feedback
            }
        }
        return final_feedback

    except Exception as e:
        print(f"분석 중 오류 발생: {e}")
        return {"error": f"분석 중 오류가 발생했습니다: {e}"}
    finally:
        if os.path.exists(extracted_audio_path):
            os.remove(extracted_audio_path)
            print("임시 오디오 파일 삭제 완료")

# -- 웹 서버 엔드포인트 (기존 app.py의 역할) --
@app.route('/analyze_video', methods=['POST'])
def analyze_video_api():
    """웹 서버를 통해 요청을 받을 때 동작하는 API 엔드포인트입니다."""
    if 'video' not in request.files:
        return jsonify({"error": "No video file provided"}), 400

    video_file = request.files['video']
    if video_file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    timestamp = int(time.time())
    original_filename, file_extension = os.path.splitext(video_file.filename)
    unique_filename = f"{original_filename}_{timestamp}{file_extension}"
    video_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    
    try:
        video_file.save(video_path)
        print(f"영상 파일 저장 완료: {video_path}")
        
        final_feedback = process_video_for_feedback(video_path, original_filename)
        
        response_json = json.dumps(final_feedback, ensure_ascii=False)
        return Response(response_json, mimetype='application/json')
    except Exception as e:
        print(f"분석 중 오류 발생: {e}")
        return jsonify({"error": f"분석 중 오류가 발생했습니다: {e}"}), 500
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
            print("임시 영상 파일 삭제 완료")

# -- 메인 실행 블록 (클라이언트의 역할을 대신 수행) --
def main():
    """
    이 스크립트를 독립적으로 실행할 때 동작하는 함수.
    로컬에 저장된 동영상 파일을 분석하고 JSON 파일을 생성합니다.
    """
    # 📌 여기에 분석할 동영상 파일의 경로를 지정해주세요.
    # 예: "my_interview_video.mp4"
    video_to_analyze = "C:/Users/SUNWOO/Desktop/spAIk/sample_input/123.mp4"

    if not os.path.exists(video_to_analyze):
        print(f"오류: 지정된 파일 '{video_to_analyze}'을(를) 찾을 수 없습니다.")
        print("스크립트 실행 전에 분석할 파일을 해당 경로에 두거나, 경로를 수정해주세요.")
        return

    print(f"'{video_to_analyze}' 파일 분석을 시작합니다...")
    video_id = os.path.splitext(os.path.basename(video_to_analyze))[0]
    
    # 분리된 분석 함수를 직접 호출합니다.
    feedback_data = process_video_for_feedback(video_to_analyze, video_id)
    
    # 결과를 JSON 파일로 저장합니다.
    output_filename = f"feedback_report_{video_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    output_path = os.path.join(ANALYSIS_RESULTS_FOLDER, output_filename) # ❗❗❗ 출력 경로를 수정합니다.
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(feedback_data, f, ensure_ascii=False, indent=4)
        
    print(f"\n✅ 분석이 완료되었습니다. 결과가 '{output_path}' 파일에 저장되었습니다.")
    
if __name__ == '__main__':
    # Flask 서버를 실행하려면 아래 주석을 해제하고 main() 함수 호출을 주석 처리하세요.
    # app.run(debug=True, host='0.0.0.0', port=5000)
    
    # 하나의 스크립트 실행으로 JSON 파일을 얻으려면 아래 main() 함수를 호출합니다.
    main()