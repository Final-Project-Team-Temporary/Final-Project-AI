"""기사 요약 서비스"""

from typing import Dict, Any
from ...models.schemas import ArticleInput, SummaryOutput
from .client import LLMClient
from .prompts import PromptTemplates
from .parser import ResponseParser


class SummarizerService:
    
    def __init__(self):
        self.llm_client = LLMClient()
        self.prompt_templates = PromptTemplates()
        self.response_parser = ResponseParser()
    
    async def summarize_article(self, article: ArticleInput) -> SummaryOutput:
        """기사를 3가지 난이도로 요약"""
        try:
            # 프롬프트 생성
            prompt = self.prompt_templates.get_summary_prompt(article.content)
            
            # Gemini API 호출
            response = self.llm_client.invoke(prompt)
            
            # 응답에서 JSON 추출
            response_text = response.content
            
            # 응답 파싱
            return self.response_parser.parse_summary_response(response_text)
            
        except Exception as e:
            # Fallback: 기본 요약 생성
            return self.response_parser.create_fallback_summary(article.content)


# 전역 서비스 인스턴스
summarizer_service = SummarizerService()
