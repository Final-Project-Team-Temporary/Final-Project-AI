import os
from typing import Optional

class Settings:
    
    # API 키 설정
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "AIzaSyA_N_f8KmzGpRuptN8HRdYpR22D7V62E8o")
    YOUTUBE_API_KEY: Optional[str] = os.getenv("YOUTUBE_API_KEY")
    
    # 서버 설정
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # API 설정
    API_TITLE: str = "EconoEasy API"
    API_DESCRIPTION: str = "기사 요약 및 YouTube 영상 추천 서비스"
    API_VERSION: str = "1.0.0"
    
    # Gemini 설정
    GEMINI_MODEL: str = "gemini-2.5-flash"  # 최신 안정 버전
    GEMINI_TEMPERATURE: float = 0.0
    
    # YouTube 설정
    YOUTUBE_MAX_RESULTS: int = 10
    YOUTUBE_DEFAULT_TOP_N: int = 3

# 전역 설정 인스턴스
settings = Settings()
