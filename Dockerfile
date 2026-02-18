FROM python:3.10-slim

# 1. 시스템 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    fonts-nanum \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    git \
    curl \
    wget \
    unzip \
    xvfb \
    x11vnc \
    fluxbox \
    xclip \
    xsel \
    scrot \
    python3-tk \
    python3-dev \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# 폰트 캐시 경신
RUN fc-cache -fv

# 2. 크롬 설치
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | tee /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# 3. [중요] 작업 폴더를 /app으로 잡습니다 (최상위)
WORKDIR /app

# 4. 환경변수
ENV DISPLAY=:99
ENV PYTHONUNBUFFERED=1

# 5. [핵심] 같은 폴더에 있는 라이브러리 파일 복사 및 설치
COPY requirements-base.txt .
RUN pip install --no-cache-dir -r requirements-base.txt

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. 소스 코드 전체 복사 
# (FinalProject_Aiplatform 안의 내용물이 /app으로 들어옵니다)
# 결과: /app/backend-ai 폴더가 생깁니다.
COPY . .

# 7. [이동] 설치 다 했으니 이제 run.py가 있는 방으로 들어갑니다.
WORKDIR /app/backend-ai

# [기존 CMD 지우고 아래 내용으로 교체]
# touch /root/.Xauthority 명령어를 추가하여 빈 권한 파일을 강제로 생성합니다.
# CMD ["sh", "-c", "rm -f /tmp/.X99-lock && rm -f /tmp/.X11-unix/X99-lock && mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix && touch /root/.Xauthority && Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset & sleep 5 && python run.py"]
CMD ["sh", "-c", "rm -f /tmp/.X99-lock && rm -f /tmp/.X11-unix/X99-lock && mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix && touch /root/.Xauthority && Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset & sleep 2 && fluxbox & sleep 2 && x11vnc -display :99 -forever -nopw -rfbport 5900 & sleep 5 && python run.py"]