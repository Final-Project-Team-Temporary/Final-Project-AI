from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# 프로젝트 루트 디렉토리 찾기
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    """
    애플리케이션 설정 클래스
    환경 변수 또는 .env 파일에서 설정을 로드합니다.
    """
    
    # API 키 설정 (필수)
    GEMINI_API_KEY: str
    YOUTUBE_API_KEY: Optional[str] = None
    
    # 서버 설정
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # API 설정
    API_TITLE: str = "EconoEasy API"
    API_DESCRIPTION: str = "기사 요약 및 YouTube 영상 추천 서비스"
    API_VERSION: str = "1.0.0"
    
    # Gemini 설정
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TEMPERATURE: float = 0.0
    
    # YouTube 설정
    YOUTUBE_MAX_RESULTS: int = 10
    YOUTUBE_DEFAULT_TOP_N: int = 3
    
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# 전역 설정 인스턴스
settings = Settings()
