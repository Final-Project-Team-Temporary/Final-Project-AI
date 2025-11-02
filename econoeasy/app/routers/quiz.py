from fastapi import APIRouter, HTTPException
from ..models.schemas import (
    QuizByKeywordRequest,
    QuizByArticleRequest,
    QuizResponse,
    ErrorResponse,
)
from ..services.quiz import quiz_service


router = APIRouter(
    prefix="/quiz",
    tags=["quiz"],
    responses={
        400: {"model": ErrorResponse, "description": "잘못된 요청"},
        500: {"model": ErrorResponse, "description": "서버 오류"},
    },
)


@router.post("/by-keyword", response_model=QuizResponse)
async def quiz_by_keyword(request: QuizByKeywordRequest):
    """
    키워드 기반 객관식 퀴즈 {count}개 생성/조회
    """
    try:
        result = await quiz_service.get_or_create_by_keyword(request)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"퀴즈 처리 중 오류: {str(e)}")


@router.post("/by-article", response_model=QuizResponse)
async def quiz_by_article(request: QuizByArticleRequest):
    """
    기사 본문 기반 객관식 퀴즈 {count}개 생성/조회
    """
    try:
        result = await quiz_service.get_or_create_by_article(request)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"퀴즈 처리 중 오류: {str(e)}")


