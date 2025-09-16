from fastapi import APIRouter, HTTPException
from ..models.schemas import ArticleInput, SummaryOutput, ErrorResponse
from ..services.summarizer import summarizer_service

router = APIRouter(
    prefix="/summarize",
    tags=["summarize"],
    responses={
        400: {"model": ErrorResponse, "description": "잘못된 요청"},
        500: {"model": ErrorResponse, "description": "서버 오류"}
    }
)

@router.post("/", response_model=SummaryOutput)
async def summarize_article(article: ArticleInput):
    """
    기사를 3가지 난이도로 요약합니다.
    
    - **easy**: 초등학생도 이해할 수 있는 간단한 요약
    - **medium**: 일반인이 이해할 수 있는 요약  
    - **advanced**: 전문적인 수준의 상세한 요약
    
    **요청 예시:**
    ```json
    {
        "title": "AI 기술 발전 현황",
        "content": "인공지능 기술이 빠르게 발전하고 있습니다..."
    }
    ```
    
    **응답 예시:**
    ```json
    {
        "easy": "AI가 우리 생활을 더 편리하게 만들어주고 있어요.",
        "medium": "인공지능 기술의 발전으로 다양한 분야에서 혁신이 일어나고 있습니다.",
        "advanced": "머신러닝과 딥러닝 기술의 발전으로 자연어 처리, 컴퓨터 비전 등 다양한 AI 분야에서 혁신적인 성과가 나타나고 있습니다."
    }
    ```
    """
    try:
        result = await summarizer_service.summarize_article(article)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"요약 처리 중 오류가 발생했습니다: {str(e)}"
        )
