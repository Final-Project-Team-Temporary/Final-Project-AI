#!/bin/bash

# ====================================================
# EconoEasy All Workers 실행 스크립트
# (Article Worker + Recommend Worker 동시 실행)
# ====================================================

echo "==================================="
echo "EconoEasy All Workers 시작"
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
echo "두 워커를 시작합니다..."
echo "  - Article Worker (기사 요약)"
echo "  - Recommend Worker (영상 추천)"
echo "종료하려면 Ctrl+C를 누르세요."
echo ""

# 4️⃣ 워커 실행 (백그라운드)
# Signal 핸들러 설정
cleanup() {
    echo ""
    echo "워커 종료 중..."
    kill $ARTICLE_WORKER_PID $RECOMMEND_WORKER_PID 2>/dev/null
    wait $ARTICLE_WORKER_PID $RECOMMEND_WORKER_PID 2>/dev/null
    echo "모든 워커가 종료되었습니다."
    exit 0
}

trap cleanup SIGINT SIGTERM

# Article Worker 백그라운드 실행
echo "📄 Article Worker 시작 중..."
python -m app.services.queue.worker &
ARTICLE_WORKER_PID=$!

# Recommend Worker 백그라운드 실행
echo "🎬 Recommend Worker 시작 중..."
python -m app.services.recommend_queue.worker &
RECOMMEND_WORKER_PID=$!

echo ""
echo "✓ 두 워커가 모두 실행되었습니다."
echo "  - Article Worker PID: $ARTICLE_WORKER_PID"
echo "  - Recommend Worker PID: $RECOMMEND_WORKER_PID"
echo ""

# 워커들이 종료될 때까지 대기
wait $ARTICLE_WORKER_PID $RECOMMEND_WORKER_PID

