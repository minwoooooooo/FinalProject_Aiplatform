import os

if os.environ.get('DISPLAY') is None:
    os.environ['DISPLAY'] = ':99'
    print("🖥️ 가상 디스플레이 환경변수 설정 완료 (:99)")
    
import shutil
import requests
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Form
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware 
from fastapi.middleware.cors import CORSMiddleware 
from pydantic import BaseModel
from app.services.crawl_service import run_safety_report # ★ 크롤러 함수 임포트

# 기존 라우터 임포트
from app.routers import traffic, auth 

# 서비스 모듈 안전하게 임포트
try:
    from app.services.s3_service import s3_manager
    from app.services.ai_service import ai_manager
    from app.services.llm_service import get_llm_manager # ★ 추가됨: AI 초안 생성기
except ImportError:
    s3_manager = None
    ai_manager = None
    get_llm_manager = None
    print("❌ [오류] 서비스 모듈(s3_service, ai_service, llm_service)을 찾을 수 없습니다.")

app = FastAPI(title="AI 교통관제 시스템")

# 1. 세션 미들웨어 (카카오 로그인용)
app.add_middleware(SessionMiddleware, secret_key="your-secret-key-here")

# 2. CORS 설정 (프론트엔드 및 자바 서버 연동용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080", 
        "http://127.0.0.1:8080",
        "http://localhost:3000",   
        "http://127.0.0.1:3000",
        "http://localhost"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 라우터 등록
app.include_router(traffic.router) 
app.include_router(auth.router)     

# 임시 파일 저장소
TEMP_DIR = "temp_videos"
os.makedirs(TEMP_DIR, exist_ok=True)

# 자바 서버 주소
JAVA_SERVER_URL = "http://backend-service:8080/api/violations"

@app.get("/")
def read_root():
    ocr_status = "✅ 로드됨" if (ai_manager and ai_manager.lpr_system) else "❌ 로드 안됨"
    return {
        "status": "running", 
        "message": "AI 관제 시스템 가동 중", 
        "ocr_module": ocr_status
    }

# ★ 백그라운드 작업 함수 (통합됨)
def background_s3_upload(local_path: str, s3_key: str):
    """파일을 S3에 업로드하고 로컬 파일을 삭제하는 백그라운드 작업"""
    if s3_manager:
        try:
            print(f"☁️ [Background] S3 업로드 시작: {s3_key}")
            s3_manager.upload_file(local_path, s3_key)
            print(f"✅ [Background] S3 업로드 완료")
        except Exception as e:
            print(f"❌ [Background] S3 업로드 실패: {e}")
    
    # 업로드 후 로컬 파일 삭제 (서버 용량 관리)
    if os.path.exists(local_path):
        try:
            os.remove(local_path)
            print(f"🗑️ [Background] 임시 파일 삭제 완료")
        except:
            pass

# ★ 분석 엔드포인트 (AI 초안 생성 기능 통합 완료)
@app.post("/api/analyze-video")
async def analyze_video_endpoint(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    serial_no: str = Form(...) # 프론트에서 보낸 serial_no 받기
):
    if ai_manager is None:
        return JSONResponse(content={"result": "AI 모듈 로드 실패", "plate": "Error"}, status_code=500)

    # 1. 파일 저장
    filename = file.filename
    file_path = os.path.join(TEMP_DIR, filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 폴더명 결정 (없으면 WEB_UPLOAD)
        folder_name = serial_no if serial_no else "WEB_UPLOAD"
        print(f"📥 [Main] 영상 수신: {filename} (저장 폴더: {folder_name})")

        # 2. AI 분석 실행
        print("🔄 AI 분석 엔진 가동 (YOLO + TF)...")
        result = ai_manager.analyze_local_video(file_path)
        
        # 3. S3 경로(Key) 생성
        s3_key = f"raspberrypi_video/{folder_name}/{filename}"
        
        if s3_manager:
            # 미리보기 URL 생성
            result["video_url"] = s3_manager.get_presigned_url(s3_key)
        
        print(f"✅ [Main] 분석 완료: {result['result']}")

        # =========================================================
        # 4. AI 신고 초안 생성 및 데이터 정제
        # =========================================================
        llm_manager = get_llm_manager()
        ai_draft_text = ""
        violation_type = result.get("result", "")
        
        # 위반 사항이 있을 때만 초안 생성
        if "정상" not in violation_type and "에러" not in violation_type and llm_manager:
            print(f"📝 [Main] 신고 초안 생성 요청 중... ({violation_type})")
            
            draft_prompt = f"""
            다음 위반 사실을 바탕으로 안전신문고 신고 내용을 "상세 내용" 칸에 들어갈 말투로 작성해줘.
            - 위반 일시: {result.get("time", "")}
            - 위반 장소: {result.get("location", "")}
            - 위반 항목: {violation_type}
            - 차량 번호: {result.get("plate", "")}
            """
            ai_draft_text = llm_manager.get_report_draft(draft_prompt)
            print(f"✅ [Main] 초안 생성 완료: {ai_draft_text[:20]}...")
        else:
            ai_draft_text = "위반 사항 없음" if "정상" in violation_type else "분석 실패"

        # 날짜/시간 분리 (Java DTO 포맷용)
        time_str = result.get("time", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        try:
            dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            incident_date = dt.strftime('%Y-%m-%d')
            incident_time = dt.strftime('%H:%M:%S')
        except:
            incident_date = time_str
            incident_time = ""

        # =========================================================
        # 5. 자바 서버로 결과 전송 (DB 저장용)
        # =========================================================
        try:
            # 자바 DTO(IncidentLogDTO) 필드명에 정확히 맞춘 Payload 생성
            java_payload = {
                "serialNo": folder_name,
                "videoUrl": result.get("video_url", ""),
                "incidentDate": incident_date,
                "incidentTime": incident_time,
                "violationType": violation_type,
                "plateNo": result.get("plate", "-"),
                "location": result.get("location", ""),
                "aiDraft": ai_draft_text  # ★ 핵심: 초안 데이터 포함
            }
            
            print(f"🚀 [Main] 자바 서버로 데이터 전송 시도: {JAVA_SERVER_URL}")
            response = requests.post(JAVA_SERVER_URL, json=java_payload, timeout=5)
            
            if response.status_code == 200:
                print("✅ [Main] 자바 서버 DB 저장 성공!")
            else:
                print(f"⚠️ [Main] 자바 서버 응답 오류: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ [Main] 자바 서버 연결 실패 (DB 저장 안됨): {e}")

        # 6. S3 업로드는 백그라운드로 넘김
        background_tasks.add_task(background_s3_upload, file_path, s3_key)

        # 7. 프론트엔드에 결과 반환 (aiDraft 포함)
        result["aiDraft"] = ai_draft_text
        return JSONResponse(content=result)

    except Exception as e:
        print(f"❌ [Main] 서버 에러: {str(e)}")
        # 에러 나면 파일 지우기
        if os.path.exists(file_path):
            os.remove(file_path)
            
        return JSONResponse(content={
            "result": "서버 오류",
            "plate": "Error",
            "description": str(e)
        }, status_code=500)

# 영상 삭제 요청 모델
class DeleteVideoRequest(BaseModel):
    video_url: str

@app.post("/api/delete-video")
def delete_video_endpoint(req: DeleteVideoRequest):
    if not s3_manager:
        return JSONResponse({"error": "S3 Manager not loaded"}, status_code=500)
    
    try:
        # URL에서 S3 Key 추출 로직
        url = req.video_url
        if "raspberrypi_video" in url:
            # URL 디코딩 및 파싱 로직 (단순화)
            start_idx = url.find("raspberrypi_video")
            end_idx = url.find("?")
            
            if end_idx == -1:
                key = url[start_idx:]
            else:
                key = url[start_idx:end_idx]
            
            print(f"🗑️ [S3 삭제 요청] Key: {key}")
            # s3_service.py에 delete_file 메서드 호출
            s3_manager.delete_file(key) 
            return {"status": "deleted", "key": key}
        else:
            print("⚠️ S3 키를 찾을 수 없는 URL입니다.")
            return {"status": "skipped"}
            
    except Exception as e:
        print(f"❌ S3 삭제 중 에러: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
    

# 안전신문고 자동 신고
# 1. 데이터 받는 틀 (Java의 AutoReportRequestDTO와 짝꿍)
class AutoReportRequest(BaseModel):
    portalId: str
    portalPw: str
    userName: str
    userPhone: str
    title: str
    content: str
    carNum: str
    videoUrl: str
    location: str  # ★ 이 줄이 없어서 그동안 NULL이 떴던 겁니다!
    occurDate: str
    occurTimeHh: str
    occurTimeMm: str

# [수정된 부분 2] 자동 신고 엔드포인트 로직 보강
@app.post("/api/auto-report")
async def auto_report_endpoint(background_tasks: BackgroundTasks, req: AutoReportRequest):
    print(f"🤖 [FastAPI] 자동 신고 요청 수신: {req.carNum} (위치: {req.location})")

    download_url = req.videoUrl
    # 로컬 호스트 주소 변환
    if "localhost:8080" in download_url:
        download_url = download_url.replace("localhost:8080", "backend-service:8080")

    filename = f"report_{req.carNum}_{int(datetime.now().timestamp())}.mp4"
    temp_file_path = os.path.join(TEMP_DIR, filename)

    try:
        # ★ [403 에러 해결] S3 보안 접근을 위해 브라우저인 척 헤더 추가
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        print(f"📥 영상 다운로드 시작: {download_url}")
        res = requests.get(download_url, headers=headers, stream=True, timeout=10)
        
        if res.status_code == 200:
            with open(temp_file_path, 'wb') as f:
                shutil.copyfileobj(res.raw, f)
            print("✅ 영상 다운로드 완료")
        else:
            print(f"⚠️ 영상 다운로드 실패 (상태코드: {res.status_code})")
    except Exception as e:
        print(f"❌ 영상 다운로드 중 에러: {e}")

    # (2) 크롤링 데이터 준비 (파이썬 봇이 쓰는 키 이름으로 정확히 매핑)
    report_data = {
        "portal_id": req.portalId,
        "portal_pw": req.portalPw,
        "user_name": req.userName,
        "user_phone": req.userPhone,
        "file_path": os.path.abspath(temp_file_path),
        "title": req.title,
        "content": req.content,
        "car_num": req.carNum,
        "location": req.location,      # ★ 이제 NULL 안 뜨고 정상 전달됩니다!
        "occur_date": req.occurDate,
        "occur_time_hh": req.occurTimeHh,
        "occur_time_mm": req.occurTimeMm
    }

    # (3) 백그라운드 실행
    background_tasks.add_task(run_safety_report, report_data)

    return {"status": "started", "message": "자동 신고 작업이 시작되었습니다."}