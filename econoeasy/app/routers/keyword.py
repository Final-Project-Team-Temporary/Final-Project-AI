from fastapi import APIRouter, HTTPException
from ..models.schemas import (
    ArticleInput, KeywordTermsResponse, KeywordStockResponse,
    TermDefineRequest, EnrichedTermDefineResponse,
)
from ..services.keyword.service import keyword_service
from ..services.keyword.term_definition_service import term_definition_service

router = APIRouter(prefix="/keyword", tags=["keyword"])


@router.post("/terms", response_model=KeywordTermsResponse)
async def get_related_terms(article: ArticleInput):
    try:
        return await keyword_service.extract_related_terms(article)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stock_id", response_model=KeywordStockResponse)
async def get_related_stocks(article: ArticleInput):
    try:
        return await keyword_service.match_stock_in_article(article)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/define", response_model=EnrichedTermDefineResponse)
async def define_term(payload: TermDefineRequest):
    """용어 정의 + 기사 맥락 + 최근 뉴스 동향을 한 번에 반환한다."""
    try:
        return await term_definition_service.define_term(
            term=payload.term,
            article_content=payload.article_content,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

