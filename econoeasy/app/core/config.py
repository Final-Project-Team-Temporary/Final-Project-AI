import os
from typing import Optional

class Settings:
    """애플리케이션 설정"""
    
    # API 키 설정
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "AIzaSyASBqvSr2chx82bMen9r9Fqdd6yKd5L7sY")
    YOUTUBE_API_KEY: Optional[str] = os.getenv("YOUTUBE_API_KEY")
    
    # 서버 설정
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # API 설정
    API_TITLE: str = "EconoEasy API"
    API_DESCRIPTION: str = "기사 요약 및 YouTube 영상 추천 서비스"
    API_VERSION: str = "1.0.0"
    
    # Gemini 설정
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_TEMPERATURE: float = 0.0
    
    # YouTube 설정
    YOUTUBE_MAX_RESULTS: int = 10
    YOUTUBE_DEFAULT_TOP_N: int = 3

# 전역 설정 인스턴스
settings = Settings()
