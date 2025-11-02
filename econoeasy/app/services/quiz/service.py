"""퀴즈 서비스 (AI 생성 전용)"""

from ...models.schemas import (
    QuizByKeywordRequest,
    QuizByArticleRequest,
    QuizResponse,
)
from ..summarizer.client import LLMClient
from .prompts import QuizPromptTemplates
from .parser import QuizResponseParser


class QuizService:

    def __init__(self):
        self.llm_client = LLMClient()
        self.prompt_templates = QuizPromptTemplates()
        self.response_parser = QuizResponseParser()

    async def get_or_create_by_keyword(self, req: QuizByKeywordRequest) -> QuizResponse:
        prompt = self.prompt_templates.get_quiz_from_keyword_prompt(req.keyword, req.count)
        response = self.llm_client.invoke(prompt)
        parsed = self.response_parser.parse_quiz_response(response.content)
        return parsed

    async def get_or_create_by_article(self, req: QuizByArticleRequest) -> QuizResponse:
        prompt = self.prompt_templates.get_quiz_from_article_prompt(req.title, req.content, req.count)
        response = self.llm_client.invoke(prompt)
        parsed = self.response_parser.parse_quiz_response(response.content)
        return parsed


# 전역 서비스 인스턴스
quiz_service = QuizService()


