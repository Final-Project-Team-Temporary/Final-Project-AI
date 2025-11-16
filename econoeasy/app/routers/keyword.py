from fastapi import APIRouter, HTTPException
from ..models.schemas import ArticleInput, KeywordTermsResponse, KeywordStockResponse, TermDefineRequest, TermDefineResponse
from ..services.keyword.service import keyword_service

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


@router.post("/define", response_model=TermDefineResponse)
async def define_term(payload: TermDefineRequest):
    try:
        return await keyword_service.define_term(payload.term)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

