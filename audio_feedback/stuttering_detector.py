# audio_feedback/stuttering_detector.py
import librosa
import numpy as np
import soundfile as sf # 테스트를 위한 임시 오디오 파일 생성용

def detect_stuttering(audio_path, frame_length=2048, hop_length=512, threshold=0.01):
    """
    오디오 파일에서 더듬거림(stuttering) 또는 짧은 멈칫거림을 감지합니다.
    에너지가 낮은 구간을 기준으로 멈칫거림을 판단합니다.

    Args:
        audio_path (str): 분석할 오디오 파일의 경로.
        frame_length (int): RMS 에너지 계산에 사용할 프레임 길이.
        hop_length (int): 프레임 간의 홉 길이.
        threshold (float): 에너지가 이 값보다 낮으면 멈칫거림으로 간주하는 임계값.

    Returns:
        dict: 멈칫거림 횟수, 초당 멈칫거림 비율, 그리고 멈칫거림에 대한 피드백 메시지를 포함하는 딕셔너리.
    """
    try:
        y, sr = librosa.load(audio_path, sr=16000)
    except FileNotFoundError:
        print(f"오류: '{audio_path}' 파일을 찾을 수 없습니다. 경로를 확인해주세요.")
        return {
            "stutter_count": 0,
            "stutter_rate_per_sec": 0.0,
            "stuttering_feedback": "오디오 파일을 찾을 수 없어 말더듬 분석을 수행할 수 없습니다."
        }
    except Exception as e:
        print(f"오디오 로드 중 오류 발생: {e}")
        return {
            "stutter_count": 0,
            "stutter_rate_per_sec": 0.0,
            "stuttering_feedback": f"오디오 처리 중 오류 발생: {e}"
        }

    # RMS (Root Mean Square) 에너지를 계산하여 오디오 신호의 강도를 측정합니다.
    energy = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    
    # 에너지가 임계값보다 낮은 프레임을 멈칫거림(stutter)으로 간주합니다.
    # 이는 소리가 거의 없거나 아주 작은 구간을 나타냅니다.
    stutter_frames = energy < threshold
    
    count = 0
    # 멈칫거림 프레임 배열을 순회하며 새로운 멈칫거림 구간의 시작점을 찾습니다.
    # 이전 프레임은 멈칫거림이 아니었고 현재 프레임이 멈칫거림이면 새로운 멈칫거림으로 간주합니다.
    # 이렇게 하면 연속된 낮은 에너지 구간은 하나의 멈칫거림으로 처리됩니다.
    for i in range(1, len(stutter_frames)):
        if stutter_frames[i] and not stutter_frames[i-1]:
            count += 1  # 새로운 멈칫거림 구간 시작
    
    # 오디오 파일의 전체 길이를 초 단위로 가져옵니다.
    duration_seconds = librosa.get_duration(y=y, sr=sr)
    
    # 초당 멈칫거림 비율을 계산합니다.
    stutter_rate_per_sec = count / duration_seconds if duration_seconds > 0 else 0

    # 멈칫거림 횟수와 오디오 길이를 기반으로 피드백 메시지를 생성합니다.
    stuttering_feedback_message = get_stuttering_feedback(count, duration_seconds)

    return {
        "stutter_count": count,
        "stutter_rate_per_sec": stutter_rate_per_sec,
        "stuttering_feedback": stuttering_feedback_message
    }

def get_stuttering_feedback(stuttering_counts, total_duration_seconds):
    """
    더듬거림 횟수와 전체 오디오 길이를 바탕으로 피드백 메시지를 생성합니다.
    
    Args:
        stuttering_counts (int): 감지된 더듬거림(멈칫거림)의 총 횟수.
        total_duration_seconds (float): 오디오의 전체 길이 (초 단위).
        
    Returns:
        str: 더듬거림 횟수에 따른 피드백 메시지.
    """
    if total_duration_seconds <= 0: # 0으로 나누는 오류 방지
        return "영상 길이가 짧아 말더듬 횟수를 정확히 평가하기 어렵습니다."

    # 분당 더듬거림 횟수를 계산합니다.
    total_duration_minutes = total_duration_seconds / 60
    
    # 오디오 길이가 매우 짧아 분당 횟수 계산이 의미 없을 경우 처리
    if total_duration_minutes < 0.1: # 6초 미만
        return f"영상 길이가 짧아 (약 {total_duration_seconds:.1f}초) 말더듬 횟수({stuttering_counts}회)를 분당 기준으로 평가하기 어렵습니다."

    stuttering_per_minute = stuttering_counts / total_duration_minutes

    if stuttering_counts == 0:
        return "✅ 말씀하시는 동안 더듬거나 멈칫거림이 전혀 없었습니다. 매우 안정적인 발화였습니다."
    elif stuttering_per_minute < 0.5: # 1분당 0.5회 미만
        return f"💬 말씀하시는 동안 더듬거나 멈칫거림이 거의 없었습니다. 발화가 매우 자연스러웠습니다."
    elif stuttering_per_minute < 2: # 1분당 2회 미만
        return f"⚠️ 말씀하시는 동안 가끔 더듬거나 멈칫거림이 있었습니다. 조금 더 침착하게 발화 속도를 조절해 보세요."
    else:
        return f"❌ 말씀하시는 동안 더듬거나 멈칫거림이 다소 많았습니다. 긴장을 풀고 천천히 말하는 연습이 필요합니다. 답변 내용을 미리 정리하면 도움이 됩니다."