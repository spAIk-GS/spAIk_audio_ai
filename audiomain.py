import os
import time
import json
import tempfile
import math

# Import modules for audio extraction and analysis
from audio_feedback.extract_audio import extract_audio_from_video
from audio_feedback.analyze_audio import analyze_audio_features
from audio_feedback.stuttering_detector import detect_stuttering

# Import the updated audio feedback generator.
# It is assumed that generate_audio_feedback now takes `features` and `avg_rms_db` as arguments.
from audio_feedback.feedback_generator import generate_audio_feedback

# === JSON file saving related functions ===

def save_feedback_to_json(feedback_data: dict, filename: str):
    """
    Saves the given dictionary feedback data to a JSON file.

    Args:
        feedback_data (dict): The feedback data dictionary to save.
        filename (str): The name of the JSON file to save (including extension).
    """
    # Create the output directory if it doesn't exist
    output_dir = "analysis_results"
    os.makedirs(output_dir, exist_ok=True)
    
    file_path = os.path.join(output_dir, filename)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(feedback_data, f, ensure_ascii=False, indent=4)
        print(f"피드백이 성공적으로 '{file_path}'에 저장되었습니다.")
    except IOError as e:
        print(f"파일 저장 중 오류가 발생했습니다: {e}")

def convert_rms_to_db(rms_value):
    """
    Converts RMS value to decibels (dB).
    Handles log errors by treating RMS values of 0 or less as a very small value.
    """
    if rms_value <= 0:
        return -120.0  # A very low value close to silence
    return 20 * math.log10(rms_value)

def amain(video_path, analysis_id, presentation_id):

    # Temporary path where the extracted audio file will be saved
    with tempfile.TemporaryDirectory(prefix=f"audio_{analysis_id}_") as tmpdir:
        # === Audio extraction ===
        print("=== 1. 오디오 추출 중 ===")
        audio_path = os.path.join(tmpdir, f"{presentation_id}.wav")
        start = time.time()
        # 2) 비디오 → 오디오 추출 (임시파일에 저장)
        print("--추출 시작--")
        extract_audio_from_video(video_path, audio_path)
        end = time.time()
        print(f"[✓] 소요 시간: {end - start:.2f}초")

        # 3) 오디오 분석
        features = analyze_audio_features(audio_path)
        transcript = features.get("transcript", "")
        
        # 4) Stuttering analysis and feedback generation ===
        print("=== 3. 말 더듬음 분석 중 ===")
        stuttering_analysis_results = detect_stuttering(audio_path)
    
        # === 5. Audio feedback generation ( 종합 ) ===
        print("=== 4. 오디오 피드백 생성 중 ===")
    
        # avg_rms_db를 먼저 계산합니다.
        avg_rms_value = features.get('avg_rms')
        avg_rms_db = 'N/A'
        if avg_rms_value is not None:
            try:
                # numpy.float32 타입을 포함한 모든 숫자 타입을 float로 변환합니다.
                avg_rms_float = float(avg_rms_value)
                if avg_rms_float > 0.0:
                   avg_rms_db = convert_rms_to_db(avg_rms_float)
                else:
                   avg_rms_db = -120.0 # 0 이하의 값은 침묵에 가까운 낮은 값으로 설정
            except (ValueError, TypeError):
                # 변환 실패 시 N/A로 처리
                print("경고: 'avg_rms' 값을 float로 변환하는 데 실패했습니다. 'N/A'로 설정합니다.")
                avg_rms_db = 'N/A'
    
        # 수정된 generate_audio_feedback 함수를 호출하고, 점수와 피드백을 한 번에 받습니다.
        audio_feedback_results = generate_audio_feedback(features, avg_rms_db)
        
        # === 7. Final feedback generation ===
        print("\n========== 최종 피드백을 생성 중 ==========")
    
        # 말더듬음 피드백을 가져옵니다.
        stutter_count = stuttering_analysis_results.get('stutter_count', 0)
        stutter_feedback = stuttering_analysis_results.get('stuttering_feedback', 'N/A')
    
        # 모든 피드백 결과를 이미지에 제시된 구조로 통합하고 ID를 추가합니다.
        # 점수 항목을 모두 삭제합니다.
        final_feedback_report = {
            "speed": {
                "feedback": audio_feedback_results.get("speed_feedback", ""),
                "value": round(float(audio_feedback_results.get("speaking_rate_wpm", 0.0)), 2)
            },                "pitch": {
                  "feedback": audio_feedback_results.get("pitch_feedback", ""),
                "value": round(float(audio_feedback_results.get("avg_pitch_hz", 0.0)), 2)
            },
            "volume": {
                "feedback": audio_feedback_results.get("volume_feedback", ""),
                "decibels": round(float(audio_feedback_results.get("avg_rms_db", 0.0)), 2)
            },
            "stutter": {
                "feedback": stutter_feedback,
                "stutter_count": stutter_count
            },
           
        }
        print(final_feedback_report)
        return final_feedback_report
    

# Call the main function when the script is executed directly
if __name__ == "__main__":
    start_total = time.time()
    amain()
    print(f"\n총 소요 시간: {time.time() - start_total:.2f}초")
