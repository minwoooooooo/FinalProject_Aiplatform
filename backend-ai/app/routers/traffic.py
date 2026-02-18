from fastapi import APIRouter, Request, BackgroundTasks, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os
import requests 

from app.core.config import TEMP_VIDEO_DIR, BUCKET_NAME
from app.core.global_state import detection_logs
from app.services.s3_service import s3_manager
from app.services.ai_service import ai_manager
from app.services.llm_service import get_llm_manager

# AI가 만든 답변을 Java 서버에도 실시간으로 복사(동기화)
USE_JAVA_SYNC = True 

# 챗봇 답변을 보낼 자바 서버의 주소
JAVA_TARGET_URL = "http://backend-service:8080/api/chatbot-response"

# AI가 감지한 교통 위반 데이터를 보낼 자바 서버 주소
JAVA_VIOLATION_URL = "http://backend-service:8080/api/violations"

# LLM을 조절하는 관리자 객체를 변수에 담기: 프롬포트(법률 전문가, 신고서 작성 등)와 API키 관리가 세팅된 프로그램 가져오기
llm_manager = get_llm_manager()

# FastAPI()객체에 모든 기능을 전부 넣으면 코드가 길어지기 때문에 Traffic 관련 기능은 전부 라우터가 담당하도록 만들기
router = APIRouter()

# Jinja2 템플릿을 통한 HTML 파일 렌더링
templates = Jinja2Templates(directory="app/templates")

# @router: 위에서 만든 router 객체를 사용하기 위한 선언
# .get("/") : localhost:8000/을 치고 들어오는 GET 요청잡기
# response_class = 함수가 끝날때 보내주는 결과물은 Json이 아닌 웹화면(HTML)임을 안내
@router.get("/", response_class=HTMLResponse)
async def index(request: Request):  # 비동기 처리 및 브라우저가 보낸 ip, 헤더 등을 request  변수에 담아 쓰기 
    """관제 시스템 메인 페이지 렌더링"""
    # 설정한 템플릿 도구로 HTML 그리기. app/templates안의 index.html 화면 띄우기
    # HTML 파일 안에서 파이썬의 접속 정보를 쓸수 있게 넘겨주기
    return templates.TemplateResponse("index.html", {"request": request})  

@router.post("/upload-video")
# uploadFile = File(...): 사용자가 브라우저에서 선택한 영상 파일 객체
# background_tasks : 비동기식 후행 처리로 요청 -> 작업 예약 -> 응답 -> 작업 수행 순서로 http 통신을 유지하지 않아도 별도의 스레드에서 이벤트 실행
async def upload_video(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """로컬 영상을 S3에 업로드하고 분석을 시작하는 엔드포인트"""
    try:
        # 폴더 경로와 파일 이름을 합쳐 C:/temp/video.mp4 의 전체 경로가 temp_file에 할당
        temp_file = os.path.join(TEMP_VIDEO_DIR, file.filename)
        # wb(white binary)모드로 열어 이진 데이터로 변환 후 작업이 끝나면 파일 자동 닫기
        with open(temp_file, "wb") as buffer:
            buffer.write(await file.read()) # 비동기 방식으로 브라우저가 전송한 데이터를 끝까지 읽은 후 하드디스크에 기록
        
        # S3 업로드
        s3_key = f"raspberrypi_video/{file.filename}"   # S3 버킷 안에서 파일이 저장될 폴더 경로
        s3_manager.upload_file(temp_file, s3_key)       # 로컬에 저장한 temp_file을 AWS S3로 전송
        
        # 백그라운드에서 AI 분석 시작
        if background_tasks:        #
            background_tasks.add_task(ai_manager.process_video_task, s3_key)
        
        # 임시 파일 삭제
        if os.path.exists(temp_file):  # temp_file이 남아있는지 확인 후 임시 파일 삭제.
            os.remove(temp_file)       # AWS S3에 이미 업로드 되어 상관 없음
        
        # React용 JSON 응답 반환
        return JSONResponse(content={
            "success": True,
            "message": "영상 업로드 및 분석이 시작되었습니다.",
            "filename": file.filename,
            "s3_key": s3_key
        }, status_code=200)
    except Exception as e:
        print(f"❌ 업로드 에러: {e}")
        return JSONResponse(content={
            "success": False,
            "error": str(e)
        }, status_code=500)

@router.get("/api/logs")
async def get_logs():
    """AI 분석 로그 데이터를 브라우저 및 자바 서버에 반환"""
    updated_logs = []
    for log in detection_logs:
        video_key = f"raspberrypi_video/{log['info']}"
        # S3에서 영상 재생을 위한 미리보기 URL 생성
        updated_logs.append({**log, "video_url": s3_manager.get_presigned_url(video_key)})
    return updated_logs

@router.post("/s3-webhook")
async def s3_webhook(request: Request, background_tasks: BackgroundTasks):
    """S3 업로드 신호를 감지하여 AI 분석 작업 시작"""
    data = await request.json()
    
    # 신호(data) 내용 중에 'WEB_UPLOAD'라는 글자가 있으면 이미 분석된 것이므로 무시합니다.
    if "WEB_UPLOAD" in str(data):
        print(f"🚫 [Bypass] 웹 업로드 파일은 이미 분석되었으므로 건너뜁니다.")
        return {"status": "skipped", "reason": "already_analyzed_in_web"}

    for record in data.get('Records', []):
        video_key = record['s3']['object']['key']
        if video_key.lower().endswith('.mp4'):
            print(f"🔔 S3 신호 수신: {video_key}")
            # 비동기 방식으로 영상 분석 실행
            background_tasks.add_task(ai_manager.process_video_task, video_key)
            
    return {"status": "ok"}

# --- [LLM 채팅 연동 핵심 구간] ---

@router.post("/api/ask")
async def ask_traffic_llm(request: Request):
    """자바 서버와 연동하여 챗봇 질문 답변 처리 및 동기화 (분기 로직 추가)"""
    try:
        data = await request.json()
        question = data.get("question")
        
        if not question:
            return {"answer": "질문이 없습니다."}
        
        # ---------------------------------------------------------
        # 1. AI 답변 생성 (질문 내용에 따른 프롬프트 분기 처리)
        # ---------------------------------------------------------
        # 질문에 '신고' 또는 '초안'이라는 단어가 포함되어 있는지 확인합니다.
        if "신고" in question or "초안" in question:
            print(f"📝 신고 초안 모드 가동: {question[:15]}...")
            answer = llm_manager.get_report_draft(question)  # 초안 전용 프롬프트 사용
        else:
            print(f"⚖️ 법률 상담 모드 가동: {question[:15]}...")
            answer = llm_manager.get_law_answer(question)   # 법률 전문가 프롬프트 사용
        # ---------------------------------------------------------
        
        # 2. 자바 서버로 답변 내용 전송 (데이터 동기화)
        if USE_JAVA_SYNC:
            try:
                chatbot_payload = {"answer": answer, "question": question}
                # 로컬 자바 서버(8080)로 데이터 전송
                requests.post(JAVA_TARGET_URL, json=chatbot_payload, timeout=3)
                print(f"🚀 자바 서버(Local)로 챗봇 데이터 전송 성공!")
            except Exception as e:
                print(f"⚠️ 자바 서버 전송 실패: {e}")

        return {"answer": answer}
        
    except Exception as e:
        print(f"LLM 에러: {e}")
        return {"answer": f"서버 오류 발생: {str(e)}"}

@router.get("/api/ask")
def ask_simple(question: str):
    """테스트용 단순 GET 방식 질문 엔드포인트"""
    answer = llm_manager.get_law_answer(question)
    return {"answer": answer}
