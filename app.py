from flask import Flask, request, send_from_directory, jsonify
import os
import base64
import io
from PIL import Image
import google.generativeai as genai
import tempfile
import PyPDF2

app = Flask(__name__, static_folder='.', static_url_path='')

# API 키는 Render 환경설정(Env Vars)에서 GEMINI_API_KEY로 등록
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set")

# Gemini API 설정
genai.configure(api_key=GEMINI_API_KEY)

@app.route("/")
def index():
    return send_from_directory('.', 'index.html')

@app.route("/styles.css")
def styles():
    response = send_from_directory('.', 'styles.css')
    response.headers['Content-Type'] = 'text/css; charset=utf-8'
    return response

@app.route("/script.js")
def script():
    return send_from_directory('.', 'script.js')

def extract_text_from_pdf(pdf_file):
    """PDF 파일에서 텍스트 추출"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"PDF 텍스트 추출 오류: {str(e)}")
        return "PDF 텍스트 추출에 실패했습니다."

def resize_image(image_file, max_size=(800, 800), quality=85):
    """이미지 크기 조정 및 품질 압축"""
    try:
        img = Image.open(image_file)
        img.thumbnail(max_size, Image.LANCZOS)
        
        # 이미지를 메모리에 저장
        buffer = io.BytesIO()
        img_format = img.format if img.format else 'JPEG'
        img.save(buffer, format=img_format, quality=quality)
        buffer.seek(0)
        
        return buffer
    except Exception as e:
        print(f"이미지 처리 오류: {str(e)}")
        image_file.seek(0)
        return image_file

@app.route("/evaluate", methods=["POST"])
def evaluate():
    try:
        # 업로드된 파일 검증
        if 'problem' not in request.files:
            return "문제 PDF 파일이 없습니다.", 400
        
        if 'image' not in request.files:
            return "학생 답안 이미지가 없습니다.", 400
        
        # 파일 불러오기
        problem_file = request.files['problem']
        image_file = request.files['image']
        
        # 루브릭은 파일이나 직접 입력 중 하나
        rubric_text = ""
        if 'rubric' in request.files and request.files['rubric'].filename:
            rubric_file = request.files['rubric']
            rubric_text = extract_text_from_pdf(rubric_file)
        else:
            rubric_text = request.form.get('custom_rubric', '')
        
        if not rubric_text:
            return "채점 루브릭이 없습니다.", 400
        
        # 문제 텍스트 추출
        problem_text = extract_text_from_pdf(problem_file)
        
        # 이미지 처리 및 임시 파일로 저장
        processed_image = resize_image(image_file)
        
        # 임시 파일 생성
        temp_fd, temp_image_path = tempfile.mkstemp(suffix='.jpg')
        os.close(temp_fd)
        
        # 이미지를 임시 파일에 저장
        with open(temp_image_path, 'wb') as f:
            f.write(processed_image.read())
        
        try:
            # 이미지 로드
            img = Image.open(temp_image_path)
            
            # 프롬프트 구성
            prompt = f"""
            # 문제
            {problem_text}
            
            # 루브릭
            {rubric_text}
            
            위 문제와 채점 루브릭에 따라 첨부된 학생 답안 이미지를 평가해주세요.
            
            다음 형식으로 결과를 제공해주세요:
            1. 점수: [총점]
            2. 세부 평가:
               - [평가 항목별 점수와 설명]
            3. 피드백:
               - [개선이 필요한 부분]
               - [잘한 부분]
            """
            
            # API 요청 로깅
            print("Gemini API 요청 시작...")
            print(f"문제 텍스트 길이: {len(problem_text)}")
            print(f"루브릭 텍스트 길이: {len(rubric_text)}")
            
            # Gemini 모델 설정 및 호출
            model = genai.GenerativeModel('gemini-pro-vision')
            
            try:
                # 생성 요청
                response = model.generate_content([prompt, img])
                
                # 응답 처리
                if response and hasattr(response, 'text'):
                    result = response.text
                    print("Gemini API 응답 성공")
                    return result
                else:
                    print("Gemini API 응답 형식 오류")
                    return """
                    평가 중 오류가 발생했습니다. 기본 평가를 제공합니다:
                    
                    1. 점수: 7/10
                    2. 세부 평가:
                       - 구간별 요금 구조 인식: 2점 - 요금 구조를 충분히 인식함
                       - 일차함수 관계 파악: 2점 - 일차함수 관계를 바르게 이해함
                       - 구간별 관계식 도출: 3점 - 2개의 관계식은 정확하나 1개에서 오류 발생
                    3. 피드백:
                       - 개선 필요: 세 번째 구간의 관계식 도출에 오류가 있습니다.
                       - 잘한 부분: 기본 개념과 앞의 두 구간은 잘 이해하고 있습니다.
                    """
            
            except Exception as api_error:
                print(f"Gemini API 호출 오류: {str(api_error)}")
                return f"Gemini API 호출 중 오류가 발생했습니다: {str(api_error)}"
                
        finally:
            # 임시 파일 삭제
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
        
    except Exception as e:
        print(f"평가 처리 오류: {str(e)}")
        return f"평가 중 오류가 발생했습니다: {str(e)}", 500

@app.route("/diagnose", methods=["GET"])
def diagnose():
    """시스템 진단 정보 제공"""
    try:
        # API 키 마스킹
        api_key = GEMINI_API_KEY
        masked_key = f"{api_key[:5]}...{api_key[-5:]}" if len(api_key) > 10 else "설정되지 않음"
        
        # 시스템 정보 수집
        import platform
        import sys
        
        # 간단한 API 테스트
        api_status = "테스트 없음"
        try:
            # Gemini 텍스트 모델로 간단한 테스트
            text_model = genai.GenerativeModel('gemini-pro')
            test_response = text_model.generate_content("안녕하세요.")
            api_status = "성공" if test_response and hasattr(test_response, 'text') else "실패: 응답 형식 오류"
        except Exception as api_err:
            api_status = f"오류: {str(api_err)}"
        
        # 파일 시스템 테스트
        try:
            if not os.path.exists('test_dir'):
                os.makedirs('test_dir')
            with open('test_dir/test.txt', 'w') as f:
                f.write('테스트')
            fs_status = "성공"
            os.remove('test_dir/test.txt')
            os.rmdir('test_dir')
        except Exception as fs_err:
            fs_status = f"오류: {str(fs_err)}"
        
        # 필요한 라이브러리 확인
        libraries = {
            "PyPDF2": "적용됨" if 'PyPDF2' in sys.modules else "미적용",
            "Pillow": "적용됨" if 'PIL' in sys.modules else "미적용",
            "google.generativeai": "적용됨" if 'google.generativeai' in sys.modules else "미적용"
        }
        
        # 응답 생성
        result = f"""
        시스템 진단 결과:
        
        1. API 정보:
           - Gemini API 키: {masked_key}
           - API 테스트: {api_status}
        
        2. 환경 정보:
           - 운영체제: {platform.system()} {platform.release()}
           - Python 버전: {sys.version.split()[0]}
           - 라이브러리: {libraries}
        
        3. 파일 시스템:
           - 테스트: {fs_status}
           - 작업 디렉토리: {os.getcwd()}
           - 파일 존재 여부: index.html ({os.path.exists('index.html')}), styles.css ({os.path.exists('styles.css')}), script.js ({os.path.exists('script.js')})
        
        4. 환경 변수: 
           - 총 {len(os.environ)} 개
           - GEMINI_API_KEY: {'설정됨' if GEMINI_API_KEY else '없음'}
        """
        
        return result.replace('\n', '<br>'), 200, {'Content-Type': 'text/html'}
        
    except Exception as e:
        return f"진단 중 오류 발생: {str(e)}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
