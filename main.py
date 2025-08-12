import os
import time
import json
import datetime
import math

# Import modules for audio extraction and analysis
from audio_feedback.extract_audio import extract_audio_from_video
from audio_feedback.analyze_audio import analyze_audio_features
from audio_feedback.stuttering_detector import detect_stuttering

# Import the updated audio feedback generator.
# It is assumed that generate_audio_feedback now takes `features` and `avg_rms_db` as arguments.
from audio_feedback.feedback_generator import generate_audio_feedback

# === JSON file saving related functions ===

def generate_analysis_id(video_id: str, analysis_type: str) -> str:
    """
    Generates a unique analysis ID by combining the video ID, analysis type, and current timestamp.
    """
    current_timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    analysis_id = f"{video_id}_{analysis_type}_{current_timestamp}"
    return analysis_id


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

def main():
    # === 1. File path configuration ===
    # Input video file path
    input_video_path = "C:/Users/SUNWOO/Desktop/spAIk/sample_input/9min.mkv"
    # Temporary path where the extracted audio file will be saved
    extracted_audio_path = "C:/Users/SUNWOO/Desktop/spAIk/temp_output/sample_audio.wav"
    
    # Generate or define a unique video_id for analysis.
    # For example, using a simple ID based on the file name.
    video_id = os.path.splitext(os.path.basename(input_video_path))[0]

    # === 2. Audio extraction ===
    print("=== 1. 오디오 추출 중 ===")
    start = time.time()
    extract_audio_from_video(input_video_path, extracted_audio_path)
    end = time.time()
    print(f"[✓] 소요 시간: {end - start:.2f}초")

    # === 3. Audio analysis (speaking rate, pitch, volume, etc.) ===
    print("=== 2. 오디오 분석 중 ===")
    start = time.time()
    features = analyze_audio_features(extracted_audio_path)
    end = time.time()
    
    # Get the analyzed text transcript
    transcript = features.get("transcript", "")
    print(f"[✓] 소요 시간: {end - start:.2f}초")

    # === 4. Stuttering analysis and feedback generation ===
    print("=== 3. 말 더듬음 분석 중 ===")
    start = time.time()
    stuttering_analysis_results = detect_stuttering(extracted_audio_path)
    end = time.time()
    print(f"[✓] 소요 시간: {end - start:.2f}초")

    # === 5. Audio feedback generation ( 종합 ) ===
    print("=== 4. 오디오 피드백 생성 중 ===")
    start = time.time()
    
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
    

    end = time.time()
    print(f"[✓] 소요 시간: {end - start:.2f}초")

    # === 6. Final feedback to JSON file ===
    print("\n========== 최종 피드백을 JSON 파일로 저장 중 ==========")
    
    # 말더듬음 피드백을 가져옵니다.
    stutter_count = stuttering_analysis_results.get('stutter_count', 0)
    stutter_feedback = stuttering_analysis_results.get('stuttering_feedback', 'N/A')
    
    # 모든 피드백 결과를 이미지에 제시된 구조로 통합하고 ID를 추가합니다.
    # 점수 항목을 모두 삭제합니다.
    final_feedback_report = {
        "analysisId": generate_analysis_id(video_id, "VoiceFeedback"),
        "videoId": video_id,
        "results": {
            "speed": {
                "feedback": audio_feedback_results.get("speed_feedback", ""),
                "value": round(float(audio_feedback_results.get("speaking_rate_wpm", 0.0)), 2)
            },
            "pitch": {
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
    }

    # Generate a unique ID for the report.
    unique_id = generate_analysis_id(video_id, "full_report")
    
    # Create the JSON filename with the unique ID.
    json_filename = f"{unique_id}.json"

    # Call the save function to write the results to a file.
    save_feedback_to_json(final_feedback_report, json_filename)
    

# Call the main function when the script is executed directly
if __name__ == "__main__":
    start_total = time.time()
    main()
    print(f"\n총 소요 시간: {time.time() - start_total:.2f}초")




