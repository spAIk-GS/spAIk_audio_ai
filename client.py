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
    """
    동영상 파일을 서버에 업로드하고 AI 면접 피드백을 받아 출력하는 함수입니다.
    """
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

            if response.status_code == 200:
                print("\n-------------------- 분석 결과 --------------------")
                
                result_json = response.json()

                # 'results'와 'content_summary' 키가 있는지 안전하게 확인합니다.
                if 'results' in result_json and 'content_summary' in result_json['results']:
                    summary = result_json['results']['content_summary']
                    
                    # 서버 응답에서 발생할 수 있는 백슬래시를 제거합니다.
                    # json.loads()를 통해 처리된 문자열이므로, 이스케이프된 문자는 이미 처리되었을 가능성이 높습니다.
                    # 하지만 혹시 모를 경우를 대비해, 다시 한번 replace를 적용합니다.
                    # json.loads가 정상적으로 작동했다면 불필요하지만 안전장치로 추가합니다.
                    cleaned_summary = summary.replace('\\"', '"').replace('\\n', '\n')
                    result_json['results']['content_summary'] = cleaned_summary
                
                # 결과 JSON을 들여쓰기하여 보기 좋게 출력합니다.
                print(json.dumps(result_json, indent=4, ensure_ascii=False))
            else:
                print("서버에서 오류가 발생했습니다:")
                print(response.text)

    except requests.exceptions.ConnectionError as e:
        print(f"서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요. 오류: {e}")
    except requests.exceptions.Timeout:
        print("요청 시간이 초과되었습니다. 서버의 응답이 너무 오래 걸립니다.")
    except Exception as e:
        print(f"예상치 못한 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    upload_video_and_get_feedback(VIDEO_FILE_PATH)