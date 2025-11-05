from fastapi import APIRouter, HTTPException
import logging
from ..models.schemas import (
    QuizByKeywordRequest,
    QuizByArticleRequest,
    QuizResponse,
    ErrorResponse,
)
from ..services.quiz import quiz_service

logger = logging.getLogger(__name__)

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
        logger.info(f"퀴즈 요청: keyword={request.keyword}, count={request.count}")
        result = await quiz_service.get_or_create_by_keyword(request)
        return result
    except ValueError as e:
        logger.error(f"퀴즈 생성 실패 (ValueError): {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"퀴즈 생성 실패: {str(e)}"
        )
    except Exception as e:
        logger.error(f"퀴즈 처리 중 오류: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"퀴즈 처리 중 오류: {str(e)}"
        )


@router.post("/by-article", response_model=QuizResponse)
async def quiz_by_article(request: QuizByArticleRequest):
    """
    기사 ID 기반 객관식 퀴즈 {count}개 생성/조회
    - MongoDB에서 기사 정보 조회
    - 저장된 퀴즈가 있으면 반환
    - 없으면 AI 생성 후 저장
    """
    try:
        logger.info(f"기사 퀴즈 요청: article_id={request.article_id}, count={request.count}")
        result = await quiz_service.get_or_create_by_article(request)
        return result
    except ValueError as e:
        logger.error(f"퀴즈 생성 실패 (ValueError): {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"퀴즈 생성 실패: {str(e)}"
        )
    except Exception as e:
        logger.error(f"퀴즈 처리 중 오류: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"퀴즈 처리 중 오류: {str(e)}"
        )


