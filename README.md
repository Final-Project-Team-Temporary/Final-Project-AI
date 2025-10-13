# EconoEasy API

경제 기사 요약 및 관련 YouTube 영상 추천 서비스

## 설치

```bash
cd econoeasy
pip install -r requirements.txt
```

## 환경 변수 설정

루트 디렉토리에 `.env` 파일 생성:

```bash
cp .env.example .env
```

`.env` 파일에 API 키 입력:

```
GEMINI_API_KEY=your_gemini_api_key
YOUTUBE_API_KEY=your_youtube_api_key
```

## 실행

```bash
cd econoeasy
python -m app.main
```

또는

```bash
cd econoeasy
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

서버 실행 후 http://localhost:8000/docs 에서 API 문서 확인

## API

- `POST /summarize/` - 기사 요약 (3단계 난이도)
- `POST /recommend/videos` - YouTube 영상 추천

## 기술 스택

- FastAPI, Uvicorn
- LangChain, Google Gemini
- Pydantic, pydantic-settings
