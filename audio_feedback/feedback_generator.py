def generate_audio_feedback(features, avg_rms_db):
    """
    Analyzes various audio metrics and generates detailed feedback.
    
    Args:
        features (dict): A dictionary containing audio analysis results like speaking_rate, avg_pitch, etc.
        avg_rms_db (float or str): The average volume of the audio in decibels (dB), or 'N/A' if not available.

    Returns:
        dict: A dictionary containing feedback for speed, pitch, and volume, along with their values and a summary.
    """
    results = {
        "speed_feedback": "",
        "speaking_rate_wpm": 0.0,
        "pitch_feedback": "",
        "avg_pitch_hz": 0.0,
        "volume_feedback": "",
        "avg_rms_db": 0.0,
        "summary": ""
    }
    feedback_list = []

    # 말속도 피드백
    speaking_rate_wpm = features.get("speaking_rate_wpm", 0.0)
    if speaking_rate_wpm < 110:
        results["speed_feedback"] = "말속도가 조금 느린 편입니다. 더 활기차게 말해보세요."
    elif speaking_rate_wpm > 160:
        results["speed_feedback"] = "말속도가 다소 빠릅니다. 천천히 또박또박 말하면 더 명확해집니다."
    else:
        results["speed_feedback"] = "말속도가 적절합니다. 현재 속도를 유지하세요."
    results["speaking_rate_wpm"] = float(speaking_rate_wpm)
    feedback_list.append(results["speed_feedback"])

    # 피치 피드백
    avg_pitch_hz = features.get("avg_pitch_hz", 0.0)
    if avg_pitch_hz == 0:
        results["pitch_feedback"] = "피치 분석이 불가능합니다."
    elif avg_pitch_hz < 100:
        results["pitch_feedback"] = "목소리가 다소 낮습니다. 좀 더 밝고 자신감 있는 톤을 유지해보세요."
    elif avg_pitch_hz > 250:
        results["pitch_feedback"] = "목소리가 조금 높습니다. 긴장을 줄이고 자연스럽게 말해보세요."
    else:
        results["pitch_feedback"] = "목소리 톤이 안정적입니다."
    results["avg_pitch_hz"] = float(avg_pitch_hz)
    feedback_list.append(results["pitch_feedback"])

    # 볼륨 피드백 (dB 값 기준)
    if isinstance(avg_rms_db, (float, int)):
        if avg_rms_db < -20:
            results["volume_feedback"] = "음량이 너무 작습니다. 좀 더 크게 말하거나 마이크를 가까이 해보세요."
        elif avg_rms_db > -10:
            results["volume_feedback"] = "음량이 다소 큽니다. 조금만 톤을 낮춰도 좋습니다."
        else:
            results["volume_feedback"] = "음량 크기가 적당합니다. 현재 크기를 유지하세요."
        results["avg_rms_db"] = float(avg_rms_db)
        feedback_list.append(results["volume_feedback"])
    else:
        results["volume_feedback"] = "음량 분석이 불가능합니다."
        results["avg_rms_db"] = 0.0
        feedback_list.append(results["volume_feedback"])
    
    # 종합 피드백 요약 생성
    summary_parts = [f for f in feedback_list if "불가능" not in f]
    results["summary"] = "\n".join(summary_parts)
    if not summary_parts:
        results["summary"] = "\n".join(feedback_list)

    return results