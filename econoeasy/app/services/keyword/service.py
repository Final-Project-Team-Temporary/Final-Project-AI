# econoeasy/app/services/keyword/service.py

import json
import os
from typing import List
from .client import LLMClient
from .prompts import KeywordPromptTemplates
from .parser import KeywordResponseParser
from ...models.schemas import (
    ArticleInput, TermSummary, KeywordTermsResponse,
    StockMatch, KeywordStockResponse, TermDefineResponse
)

# 파일 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STOCK_LIST_PATH = os.path.join(BASE_DIR, "stock_list.json")


class KeywordService:

    def __init__(self):
        self.llm_client = LLMClient()
        self.prompt_templates = KeywordPromptTemplates()
        self.response_parser = KeywordResponseParser()

    async def extract_related_terms(self, article: ArticleInput) -> KeywordTermsResponse:
        """기사에서 주요 경제 용어 및 설명을 추출"""
        try:
            # 프롬프트 생성
            prompt = self.prompt_templates.get_terms_prompt(article.content)

            # Gemini API 호출
            response = await self.llm_client.ainvoke(prompt)
            response_text = response.content if hasattr(response, "content") else str(response)

            # 응답 파싱
            return self.response_parser.parse_terms_response(response_text)

        except Exception:
            # 실패 시 fallback 결과 반환
            return self.response_parser.create_fallback_terms(article.content)


    #/keyword/stock_id 서비스 로직
    
    async def match_stock_in_article(self, article: ArticleInput) -> KeywordStockResponse:
        with open(STOCK_LIST_PATH, "r", encoding="utf-8") as f:
            stock_list = json.load(f)
    
        matches = []
        for stock in stock_list:
            if stock["종목명"] in article.content:
                matches.append(
                    StockMatch(
                        stock_name=stock["종목명"],
                        stock_code=stock["종목코드"],
                        market=stock.get("시장구분"),
                        sector=stock.get("업종명"),
                    )
                )
    
        filtered_matches = []
        stock_names = [m.stock_name for m in matches]
    
        for m in matches:
            if any(
                (m.stock_name != other) and (m.stock_name in other)
                for other in stock_names
            ):
                continue
            filtered_matches.append(m)
    
        return KeywordStockResponse(matched_stocks=filtered_matches)


    
    async def define_term(self, term: str) -> TermDefineResponse:
        """특정 용어를 LLM으로 설명하도록 요청"""
        try:
            prompt = self.prompt_templates.get_define_prompt(term)
            response = await self.llm_client.ainvoke(prompt)
            text = response.content if hasattr(response, "content") else str(response)

            return self.response_parser.parse_define_response(text)

        except Exception:
            return TermDefineResponse(
                term=term,
                definition="해당 용어 설명을 생성할 수 없습니다."
            )


keyword_service = KeywordService()
