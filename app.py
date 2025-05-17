from flask import Flask, request, send_from_directory
import os
import requests
import base64
import anthropic
from anthropic import Anthropic

app = Flask(__name__, static_folder='.', static_url_path='')

# API 키는 Render 환경설정(Env Vars)에서 ANTHROPIC_API_KEY로 등록
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

claude_client = Anthropic(api_key=ANTHROPIC_API_KEY)

@app.route("/")
def index():
    return send_from_directory('.', 'index.html')

@app.route("/styles.css")
def styles():
    return send_from_directory('.', 'styles.css')

@app.route("/script.js")
def script():
    return send_from_directory('.', 'script.js')

@app.route("/evaluate", methods=["POST"])
def evaluate():
    try:
        # 이미지 파일 받기
        image_file = request.files.get("image")
        if not image_file:
            return "이미지 파일이 없습니다.", 400

        # 루브릭 텍스트 받기
        rubric = request.form.get("rubric")
        if not rubric:
            return "루브릭이 없습니다.", 400

        # 이미지를 base64로 인코딩
        image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Claude에게 보낼 프롬프트 구성
        prompt = f"""아래는 수학적 모델링 문제의 학생 답안 이미지입니다. 
        다음 루브릭에 따라 답안을 평가해주세요:
        
        {rubric}
        
        이미지: {image_data}
        
        평가 결과를 다음 형식으로 작성해주세요:
        1. 점수: [총점]
        2. 세부 평가:
           - [평가 항목별 점수와 설명]
        3. 피드백:
           - [개선이 필요한 부분]
           - [잘한 부분]
        """

        # Claude API 호출
        message = claude_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        return message.content[0].text

    except Exception as e:
        print(f"Error: {str(e)}")
        return f"평가 중 오류가 발생했습니다: {str(e)}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)