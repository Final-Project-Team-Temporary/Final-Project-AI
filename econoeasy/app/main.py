from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from .core.config import settings
from .routers import summarize, recommend
from .routers import quiz, keyword
from .routers import rag
from .services.queue.mongodb_client import mongodb_client


import logging

logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# 라우터 등록
app.include_router(summarize.router)
app.include_router(recommend.router)
app.include_router(quiz.router)
app.include_router(keyword.router)
app.include_router(rag.router)

# MongoDB 라이프사이클 이벤트
@app.on_event("startup")
async def startup_event():
    """서버 시작 시 MongoDB 연결"""
    try:
        logger.info("🚀 서버 시작: MongoDB 연결 중...")
        await mongodb_client.connect()
        logger.info("✅ MongoDB 연결 성공")
    except Exception as e:
        logger.error(f"❌ MongoDB 연결 실패: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 MongoDB 연결 종료"""
    try:
        logger.info("🛑 서버 종료: MongoDB 연결 해제 중...")
        await mongodb_client.disconnect()
        logger.info("✅ MongoDB 연결 해제 완료")
    except Exception as e:
        logger.error(f"❌ MongoDB 연결 해제 중 오류: {str(e)}")

@app.get("/")
async def root():
    """루트 엔드포인트 - API 문서로 리다이렉트"""
    return RedirectResponse("/docs")

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "message": "EconoEasy API is running",
        "version": settings.API_VERSION
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
