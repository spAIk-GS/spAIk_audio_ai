import requests
import os
import json

# ==========================================================
#                         설정
# ==========================================================

# Flask 서버의 주소와 포트를 지정합니다.
SERVER_URL = "http://127.0.0.1:5000"

# 업로드할 동영상 파일의 경로를 지정합니다.
VIDEO_FILE_PATH = "C:/Users/SUNWOO/Desktop/spAIk/sample_input/123.mp4"

# ==========================================================
#                         함수
# ==========================================================

def upload_video_and_get_feedback(file_path):
    if not os.path.exists(file_path):
        print(f"오류: '{file_path}' 파일을 찾을 수 없습니다.")
        return

    upload_url = f"{SERVER_URL}/analyze_video"

    try:
        with open(file_path, 'rb') as video_file:
            files = {'video': (os.path.basename(file_path), video_file, 'video/mp4')}
            
            print(f"서버에 동영상 파일 '{os.path.basename(file_path)}'을 업로드하는 중...")
            
            # 요청 타임아웃을 5분으로 설정합니다. 동영상 분석은 시간이 오래 걸릴 수 있습니다.
            response = requests.post(upload_url, files=files, timeout=300)
            
            print(f"서버 응답 상태 코드: {response.status_code}")


    except requests.exceptions.ConnectionError as e:
        print(f"서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요. 오류: {e}")
    except requests.exceptions.Timeout:
        print("요청 시간이 초과되었습니다. 서버의 응답이 너무 오래 걸립니다.")
    except Exception as e:
        print(f"예상치 못한 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    upload_video_and_get_feedback(VIDEO_FILE_PATH)