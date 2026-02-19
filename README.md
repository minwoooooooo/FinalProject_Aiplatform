# AI Traffic Violation Auto-Reporting System
### Deep Learning Based Automated Traffic Law Enforcement Solution

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.x-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-Detectron2-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Selenium](https://img.shields.io/badge/Selenium-Automation-43B02A?style=for-the-badge&logo=selenium&logoColor=white)

</div>


---

## 1. Project Overview

**AI Traffic Violation Auto-Reporting System**
- 차량 블랙박스/CCTV 영상을 분석하여 교통 법규 위반 차량을 자동으로 탐지 및 식별
- 딥러닝 기반 객체 인식 및 위반 여부 판독 후, 생성형 AI(RAG)를 통해 신고서 자동 작성 및 관공서(안전신문고) 자동 접수 수행
- 영상 분석부터 신고 접수까지의 전 과정을 무인 자동화하여 신고 프로세스의 효율성 극대화

<br>

<br>

![20260213_RPA](https://github.com/user-attachments/assets/8fbe100e-f64a-4295-9080-cb0971c650e3)


<br>

## 2. Key Features

### AI Analysis & Recognition
* **Hybrid Detection Model:** `Detectron2` 및 `YOLO`를 활용한 차량, 차선, 신호등 객체 정밀 탐지
* **Violation Classification:** TensorFlow/Keras 기반 분류기를 통해 신호 위반(적색 신호 시 주행 등) 및 차선 위반 여부 판독
* **License Plate OCR:** 이미지 전처리(CLAHE, Denoising) 및 EasyOCR/YOLO 파이프라인을 통한 차량 번호판 텍스트 추출

### Generative AI (RAG)
* **Report Drafting:** LangChain 및 Groq(LLM)을 활용, 위반 상황에 맞는 법률적 근거 및 신고 상세 내용을 자동 생성
* **Legal Advisory:** 교통 법규 관련 질의응답이 가능한 RAG(Retrieval-Augmented Generation) 시스템 구축

### Process Automation
* **Auto-Submission Crawler:** Selenium WebDriver를 활용하여 '안전신문고' 포털 로그인, 파일 업로드, 주소 검색, 폼 작성 및 접수 과정 자동화
* **Infrastructure:** FastAPI 기반의 비동기 API 서버 구축 및 AWS S3를 연동한 대용량 영상 데이터 처리
* **Network Tunneling:** Ngrok 및 AWS Lambda 연동을 통한 로컬 서버의 외부 퍼블릭 액세스 환경 구성

<br>

## 3. Technology Stack

| Category | Technologies |
| :--- | :--- |
| **Language** | ![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) |
| **AI / ML** | ![TensorFlow](https://img.shields.io/badge/TensorFlow-FF6F00?style=flat-square&logo=tensorflow&logoColor=white) ![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=flat-square&logo=pytorch&logoColor=white) ![YOLO](https://img.shields.io/badge/YOLO-00FFFF?style=flat-square&logo=yolo&logoColor=black) ![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=flat-square&logo=langchain&logoColor=white) |
| **Backend** | ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white) ![Uvicorn](https://img.shields.io/badge/Uvicorn-499848?style=flat-square&logo=gunicorn&logoColor=white) |
| **Automation** | ![Selenium](https://img.shields.io/badge/Selenium-43B02A?style=flat-square&logo=selenium&logoColor=white) |
| **Infra / Cloud** | ![AWS S3](https://img.shields.io/badge/AWS_S3-569A31?style=flat-square&logo=amazons3&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white) |

<br>

## 4. Project Structure

```bash
traffic-violation-system/          # [Root] 프로젝트 최상위 루트
│
├── ai-engine/                     # [Research] AI 모델 학습 및 실험 전용 디렉토리
│   ├── notebooks/
│   │   ├── classifier.ipynb       # [Train] 위반 분류 모델 학습 노트
│   │   └── detectron2.ipynb       # [Train] 객체 탐지 모델 실험 노트
│
├── backend-ai/                    # [Production] FastAPI 서비스 구동 디렉토리
│   ├── app/
│   │   ├── main.py                # [Entry] FastAPI 앱 초기화 및 미들웨어 설정
│   │   ├── core/                  # [Config] 설정 관리
│   │   │   ├── config.py          # 환경변수, 경로 상수 정의
│   │   │   └── global_state.py    # 전역 변수 관리
│   │   │
│   │   ├── routers/               # [API] 엔드포인트 라우팅
│   │   │   ├── __init__.py
│   │   │   ├── auth.py            # 인증 관련 라우터
│   │   │   └── traffic.py         # 영상 분석 요청 라우터
│   │   │ 
│   │   ├── services/              # [Logic] 핵심 비즈니스 로직 모듈
│   │   │   ├── ai_service.py      # 영상 분석 및 위반 판독 파이프라인
│   │   │   ├── crawl_service.py   # 안전신문고 자동 신고 봇 (Selenium)
│   │   │   ├── llm_service.py     # RAG 기반 신고서 작성 및 법률 자문
│   │   │   ├── plate_ocr.py       # 번호판 인식 및 텍스트 추출
│   │   │   └── s3_service.py      # AWS S3 연동 (업로드/다운로드)
│   │   │ 
│   │   └── models/                # [Model] 학습 완료된 모델 파일 (ai-engine에서 복사됨)
│   │       ├── best.pt            # YOLO 가중치 파일
│   │       ├── classifier_model.h5# TensorFlow 분류 모델
│   │       └── chroma_db_combined10/ # RAG용 Vector DB 폴더
│   │
│   ├── templates/                 # [Frontend] 테스트용 클라이언트 리소스
│   │   └── index.html             # API 테스트 페이지
│   │
│   ├── temp_videos/               # [Cache] 런타임 영상 처리 임시 디렉토리
│   ├── .env                       # [Secret] API Key 및 AWS 자격 증명
│   ├── .gitignore                 # Git 관리 제외 설정
│   ├── requirements.txt           # [Dep] 서비스 구동 의존성 목록
│   └── run.py                     # [Exec] Uvicorn 서버 실행 및 Ngrok 터널링
│
└── README.md                      # 프로젝트 통합 문서
