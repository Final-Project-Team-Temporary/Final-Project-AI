"""기사 요약 서비스"""

from typing import Dict, Any
from ...models.schemas import ArticleInput, SummaryOutput, QuizByKeywordRequest, QuizByArticleRequest, QuizResponse, QuizDocument, QuizSourceType
from .client import LLMClient
from .prompts import PromptTemplates
from .parser import ResponseParser
from ..queue.mongodb_client import mongodb_client
from datetime import datetime
import hashlib


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

    # =====================
    # Quiz 서비스 메서드
    # =====================
    async def get_or_create_quizzes_by_keyword(self, req: QuizByKeywordRequest) -> QuizResponse:
        """키워드 기반 퀴즈: 저장된 게 있으면 조회, 없으면 생성 후 저장"""
        # 1) 조회
        await mongodb_client.connect()
        existing = await mongodb_client.get_quizzes_by_keyword(req.keyword, req.count)
        if len(existing) >= req.count:
            quizzes = [
                {
                    "question": q.question,
                    "options": q.options,
                    "answer_index": q.answerIndex,
                    "explanation": q.explanation,
                }
                for q in existing[: req.count]
            ]
            return QuizResponse(quizzes=quizzes)

        # 2) 생성
        prompt = self.prompt_templates.get_quiz_from_keyword_prompt(req.keyword, req.count)
        response = self.llm_client.invoke(prompt)
        response_text = response.content
        parsed = self.response_parser.parse_quiz_response(response_text)

        # 3) 저장
        now = datetime.utcnow()
        to_save: list[QuizDocument] = []
        for item in parsed.quizzes:
            to_save.append(
                QuizDocument(
                    sourceType=QuizSourceType.KEYWORD,
                    keyword=req.keyword,
                    articleHash=None,
                    title=None,
                    question=item.question,
                    options=item.options,
                    answerIndex=item.answer_index,
                    explanation=item.explanation,
                    createdAt=now,
                )
            )
        if to_save:
            await mongodb_client.save_quizzes(to_save)
        return parsed

    async def get_or_create_quizzes_by_article(self, req: QuizByArticleRequest) -> QuizResponse:
        """기사 본문 기반 퀴즈: 저장된 게 있으면 조회, 없으면 생성 후 저장"""
        # 기사 고유 식별을 위해 본문 해시 사용
        article_hash = hashlib.sha256((req.title + "\n" + req.content).encode("utf-8")).hexdigest()

        # 1) 조회
        await mongodb_client.connect()
        existing = await mongodb_client.get_quizzes_by_article_hash(article_hash, req.count)
        if len(existing) >= req.count:
            quizzes = [
                {
                    "question": q.question,
                    "options": q.options,
                    "answer_index": q.answerIndex,
                    "explanation": q.explanation,
                }
                for q in existing[: req.count]
            ]
            return QuizResponse(quizzes=quizzes)

        # 2) 생성
        prompt = self.prompt_templates.get_quiz_from_article_prompt(req.title, req.content, req.count)
        response = self.llm_client.invoke(prompt)
        response_text = response.content
        parsed = self.response_parser.parse_quiz_response(response_text)

        # 3) 저장
        now = datetime.utcnow()
        to_save: list[QuizDocument] = []
        for item in parsed.quizzes:
            to_save.append(
                QuizDocument(
                    sourceType=QuizSourceType.ARTICLE,
                    keyword=None,
                    articleHash=article_hash,
                    title=req.title,
                    question=item.question,
                    options=item.options,
                    answerIndex=item.answer_index,
                    explanation=item.explanation,
                    createdAt=now,
                )
            )
        if to_save:
            await mongodb_client.save_quizzes(to_save)
        return parsed


# 전역 서비스 인스턴스
summarizer_service = SummarizerService()
