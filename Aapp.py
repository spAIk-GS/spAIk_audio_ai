##############################################################

from flask import Flask, request, jsonify
import uuid
import os
import requests
import audiomain
import threading
import time
from tqdm import tqdm
import tempfile
import traceback


app = Flask(__name__)

# 메모리 기반 상태 저장소 (+ 락)
analysis_status_map = {}
status_lock = threading.Lock()


def set_status(analysis_id, status):
    with status_lock:
        analysis_status_map[analysis_id] = status


def get_status(analysis_id):
    with status_lock:
        return analysis_status_map.get(analysis_id)


def notify_status(callback_url, payload, retries=3):
    """
    콜백 POST (payload는 이미 완성된 dict)
    """
    delay = 1.0
    for attempt in range(1, retries + 1):
        try:
            res = requests.post(callback_url, json=payload, timeout=10)
            print(f"[POST] to {callback_url} -> {res.status_code}")
            if 200 <= res.status_code < 300:
                return True
        except Exception as e:
            print(f"[실패] POST (attempt {attempt}/{retries}) -> {e}")
        if attempt < retries:
            time.sleep(delay)
            delay *= 2
    return False



def download_video(s3_url, output_path):
    """presigned S3 URL 또는 file:// 로 영상 다운로드 (tqdm로 진행률 표시)"""
    try:
        chunk_size = 1024 * 256  # 256KB

        if s3_url.startswith("file://"):
            # 로컬 파일 복사도 진행률 표시
            local_path = s3_url.replace("file://", "")
            if os.name == "nt" and local_path.startswith("/") and ":" in local_path:
                local_path = local_path[1:]

            total_size = os.path.getsize(local_path)
            print(f"[복사] {local_path} -> {output_path}")
            with open(local_path, "rb") as src, open(output_path, "wb") as dst, tqdm(
                total=total_size,
                unit="B",
                unit_scale=True,
                desc="다운로드(로컬 복사)",
                leave=True,
            ) as pbar:
                while True:
                    buf = src.read(chunk_size)
                    if not buf:
                        break
                    dst.write(buf)
                    pbar.update(len(buf))
            print("[다운로드 완료] (로컬 복사)")
            return True

        # 원격 다운로드
        with requests.get(s3_url, stream=True, timeout=10) as response:
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))
            with open(output_path, 'wb') as f, tqdm(
                total=total_size if total_size > 0 else None,
                unit="B",
                unit_scale=True,
                desc="다운로드",
                leave=True,
            ) as pbar:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if not chunk:
                        continue
                    f.write(chunk)
                    pbar.update(len(chunk))
        print("[다운로드 완료]")
        return True

    except requests.exceptions.RequestException as e:
        print(f"[다운로드 실패] {e}")
        return False
    except Exception as e:
        print(f"[다운로드 예외] {e}")
        return False

def process_audio(s3_url, analysis_id, presentation_id, callback_url):
    """Download video from s3_url, run audio analysis, and send result or failure callback."""

    set_status(analysis_id, "IN_PROGRESS")

    with tempfile.TemporaryDirectory(prefix="dl_") as tmpdir:
        video_path = os.path.join(tmpdir, f"{analysis_id}.mp4")

        # 1) 다운로드
        if not download_video(s3_url, video_path):
            set_status(analysis_id, "FAILED")
            fail_payload = {
                "analysisId": analysis_id,
                "videoId": presentation_id,
                "status": "FAILED",
                "message": "Download failed"
            }
            notify_status(callback_url, fail_payload)
            return

        try:
            # 2) 분석 실행
            result_data = audiomain.amain(video_path, analysis_id, presentation_id)
            if not isinstance(result_data, dict):
                raise ValueError("amain() 결과 형식이 dict가 아닙니다.")

            # 3) 완료 통지
            final_payload = {
                "analysisId": analysis_id,
                "videoId": presentation_id,
                "status": "COMPLETED",
                "result": result_data
            }

            set_status(analysis_id, "COMPLETED")
            notify_status(callback_url, final_payload)

        except Exception as e:
            # 예외 전체 스택 추적과 메시지를 함께 출력
            err_trace = traceback.format_exc()
            print(f"[분석 실패] {e}")
            print(err_trace)

            set_status(analysis_id, "FAILED")

            fail_payload = {
                "analysisId": analysis_id,
                "videoId": presentation_id,
                "status": "FAILED",
                "message": f"{str(e)}\n\n{err_trace}"[:4000]  # 콜백에도 원인 포함
            }
            notify_status(callback_url, fail_payload)
            return

@app.route('/analysis/audio', methods=['POST'])
def analyze_video():
    data = request.get_json()
    presentation_id = data.get("presentationId")
    s3_url = data.get("s3Url")

    # 클라이언트 IP 기반 콜백 URL 생성
    client_ip = request.remote_addr
    callback_url = f"http://{client_ip}:8080/analysis/callback/audio"

    if not all([presentation_id, s3_url]):
        return jsonify({"error": "presentationId, s3Url은 필수입니다."}), 400

    analysis_id = f"audio-analysis-uuid-{uuid.uuid4()}"

    # 초기 상태: PENDING
    set_status(analysis_id, "PENDING")

    # 백그라운드 작업 시작 
    thread = threading.Thread(
        target=process_audio,
        args=(s3_url, analysis_id, presentation_id, callback_url),
        daemon=False
    )
    thread.start()

    # 즉시 PENDING 응답
    return jsonify({
        "analysisId": analysis_id,
        "status": "PENDING"
    })
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
