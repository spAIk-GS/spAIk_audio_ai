import os
import time
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, GoogleAPIError

# .env 파일에서 환경 변수 로드
load_dotenv()

# Google Gemini API 키 설정
# .env 파일에 GEMINI_API_KEY="YOUR_GEMINI_API_KEY" 형태로 추가해야 합니다.
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# 사용할 Gemini 모델명
# 'gemini-1.5-flash'는 빠른 응답과 큰 컨텍스트 윈도우를 제공합니다.
# 'gemini-pro'도 좋은 선택입니다.
MODEL_NAME = "gemini-1.5-flash" 

def generate_feedback_no_question(text):
    """
    사용자의 면접, 발표 답변 텍스트를 기반으로 Gemini 모델을 사용하여 피드백을 생성합니다.
    Gemini 1.5 Flash는 큰 컨텍스트를 지원하므로 별도의 토큰 분할은 하지 않습니다.
    """
    full_feedback = []
    
    # Gemini 모델 인스턴스 생성
    # system_instruction은 모델의 역할을 정의하는 데 사용됩니다.
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction="당신은 사용자의 면접 답변이나 발표를 피드백해주는 전문가입니다. 장점을 먼저 간략히 알려주고 내용의 논리성, 명확성, 구성, 그리고 청중에게 좋은 인상을 줄 수 있는 방법에 대해 간략하고 건설적인 피드백을 제공해주세요."
    )

    # Gemini API 호출 시 재시도 로직을 포함합니다.
    # ResourceExhausted는 속도 제한 또는 할당량 초과 시 발생할 수 있습니다.
    max_retries = 5
    for attempt in range(max_retries):
        try:
            print(f"Gemini 요청 중... (시도: {attempt + 1}/{max_retries})")
            response = model.generate_content(
                contents=[
                    {
                        "role": "user",
                        "parts": [
                            {"text": f"다음 발표, 면접 답변에 대해 피드백을 해주세요:\n\n{text}"}
                        ]
                    }
                ],
                # temperature 값을 조절하여 모델의 창의성/일관성 조절 (0.0 ~ 1.0)
                # 면접 피드백은 너무 창의적이기보다 일관성 있고 정확한 것이 좋으므로 0.7 유지
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7
                )
            )
            
            # 응답에서 텍스트 추출
            feedback = response.candidates[0].content.parts[0].text
            full_feedback.append(feedback)
            break # 성공했으므로 루프 종료

        except ResourceExhausted as e:
            wait_time = 2 ** attempt # 지수 백오프 (1, 2, 4, 8, 16초)
            print(f"ResourceExhausted 오류 발생 (속도 제한 또는 할당량 초과). {wait_time}초 후 재시도합니다. 오류: {e}")
            time.sleep(wait_time)
            if attempt == max_retries - 1:
                print("최대 재시도 횟수를 초과했습니다. Gemini API 사용량을 확인해주세요.")
                return None
        except GoogleAPIError as e:
            print(f"Google API 오류 발생: {e}")
            return None
        except Exception as e:
            print(f"예상치 못한 오류 발생: {e}")
            return None

    return "\n\n".join(full_feedback)