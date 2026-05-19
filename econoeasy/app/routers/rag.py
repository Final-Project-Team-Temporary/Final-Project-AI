"""
[구현 의도]
HTTP 요청/응답 변환만 담당한다.
비즈니스 로직은 전부 RAGService에 위임.
ValueError → 400, RAGServiceError → 500으로 매핑.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..services.rag.rag_service import rag_service, RAGServiceError

router = APIRouter(prefix="/rag", tags=["rag"])


class AskRequest(BaseModel):
    question: str


class IndexRequest(BaseModel):
    article_id: str
    title: str
    content: str
    published_at: str
    url: str


@router.post("/ask")
async def ask(request: AskRequest):
    """경제 뉴스 기사를 근거로 질문에 답변한다."""
    try:
        return await rag_service.ask(request.question)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RAGServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"처리 중 오류: {str(e)}")


@router.post("/index")
async def index_article(request: IndexRequest):
    """단일 기사를 RAG 검색 인덱스에 추가한다."""
    try:
        await rag_service.index_article(
            article_id=request.article_id,
            title=request.title,
            content=request.content,
            published_at=request.published_at,
            url=request.url,
        )
        return {"status": "ok", "article_id": request.article_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"인덱싱 오류: {str(e)}")
