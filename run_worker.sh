#!/bin/bash

# ====================================================
# EconoEasy Article Worker 실행 스크립트
# (가상환경 자동 생성 + 의존성 설치 포함)
# ====================================================

echo "==================================="
echo "EconoEasy Article Worker 시작"
echo "==================================="
echo ""

# 현재 스크립트 디렉토리 기준으로 이동
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 1️⃣ .env 파일 확인
if [ ! -f .env ]; then
    echo "❌ 오류: .env 파일이 없습니다."
    echo "   .env.example을 복사하여 .env 파일을 생성하고 설정을 입력하세요."
    echo "   $ cp .env.example .env"
    exit 1
fi
echo "✓ 환경 변수 파일 확인 완료"

# 2️⃣ Python 가상환경 확인 및 생성
if [ ! -d "venv" ]; then
    echo "⚙️  가상환경(venv) 생성 중..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ Python 가상환경 생성 실패. Python3이 설치되어 있는지 확인하세요."
        exit 1
    fi
fi

echo "✓ 가상환경 활성화 중..."
source venv/bin/activate

# 3️⃣ 의존성 확인 및 자동 설치
echo "✓ Python 의존성 확인 중..."
cd econoeasy

python -c "import redis, motor, fastapi, langchain_google_genai" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚙️  필수 패키지 설치 중..."
    pip install --upgrade pip
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ 의존성 설치 실패. requirements.txt를 확인하세요."
        deactivate
        exit 1
    fi
fi

echo "✓ 모든 의존성 확인 완료"
echo ""
echo "워커를 시작합니다..."
echo "종료하려면 Ctrl+C를 누르세요."
echo ""

# 4️⃣ 워커 실행
python -m app.services.queue.worker
