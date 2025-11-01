from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from .core.config import settings
from .routers import summarize, recommend

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
