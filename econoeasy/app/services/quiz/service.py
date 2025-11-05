"""퀴즈 서비스 (AI 생성 전용)"""

import logging
from ...models.schemas import (
    QuizByKeywordRequest,
    QuizByArticleRequest,
    QuizResponse,
    QuizItem,
)
from ..summarizer.client import LLMClient
from .prompts import QuizPromptTemplates
from .parser import QuizResponseParser
from ..queue.mongodb_client import mongodb_client

logger = logging.getLogger(__name__)


class QuizService:

    def __init__(self):
        self.llm_client = LLMClient()
        self.prompt_templates = QuizPromptTemplates()
        self.response_parser = QuizResponseParser()
        self.db_client = mongodb_client

    async def get_or_create_by_keyword(self, req: QuizByKeywordRequest) -> QuizResponse:
        """
        키워드 기반 퀴즈 생성/조회
        1. MongoDB에서 저장된 퀴즈 확인
        2. 없으면 AI에 요청 후 저장
        
        Args:
            req: 키워드와 문항 수를 포함한 요청
            
        Returns:
            생성된 퀴즈 응답
            
        Raises:
            ValueError: 퀴즈 생성 실패 시
        """
        try:
            # [1단계] MongoDB에서 기존 퀴즈 확인
            logger.info(f"키워드 퀴즈 조회 시작: keyword={req.keyword}")
            existing_quiz = await self.db_client.get_quiz_by_keyword(req.keyword)
            
            if existing_quiz:
                logger.info(f"✅ 저장된 퀴즈 발견: {req.keyword}")
                quizzes = existing_quiz.get("quizzes", [])
                # 요청된 개수만큼 반환
                limited_quizzes = quizzes[:req.count]
                return QuizResponse(
                    quizzes=[QuizItem(**q) for q in limited_quizzes]
                )
            
            # [2단계] AI에 새 퀴즈 생성 요청
            logger.info(f"🤖 AI 퀴즈 생성 요청: keyword={req.keyword}, count={req.count}")
            prompt = self.prompt_templates.get_quiz_from_keyword_prompt(req.keyword, req.count)
            response = await self.llm_client.ainvoke(prompt)
            
            # LangChain의 BaseMessage 객체에서 content 추출
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)
            
            parsed = self.response_parser.parse_quiz_response(response_text)
            logger.info(f"✅ AI 퀴즈 생성 성공: {len(parsed.quizzes)}개")
            
            # [3단계] MongoDB에 저장
            logger.info(f"💾 퀴즈 저장 시작: keyword={req.keyword}")
            await self.db_client.save_quiz(
                source_type="KEYWORD",
                quizzes_data=parsed.quizzes,
                keyword=req.keyword
            )
            
            return parsed
            
        except Exception as e:
            logger.error(f"❌ 키워드 퀴즈 생성 실패: {str(e)}")
            raise

    async def get_or_create_by_article(self, req: QuizByArticleRequest) -> QuizResponse:
        """
        기사 기반 퀴즈 생성/조회
        1. 기사 정보를 MongoDB에서 조회
        2. 저장된 퀴즈 확인
        3. 없으면 AI에 요청 후 저장
        
        Args:
            req: 기사 ID와 문항 수를 포함한 요청
            
        Returns:
            생성된 퀴즈 응답
            
        Raises:
            ValueError: 기사 미존재 또는 퀴즈 생성 실패 시
        """
        try:
            # [1단계] 기사 조회
            logger.info(f"기사 조회 시작: article_id={req.article_id}")
            article = await self.db_client.get_article_by_id(req.article_id)
            
            if not article:
                raise ValueError(f"기사를 찾을 수 없습니다: {req.article_id}")
            
            logger.info(f"✅ 기사 조회 완료: {article.title}")
            
            # [2단계] MongoDB에서 기존 퀴즈 확인
            logger.info(f"기사 퀴즈 조회 시작: article_id={req.article_id}")
            existing_quiz = await self.db_client.get_quiz_by_article(req.article_id)
            
            if existing_quiz:
                logger.info(f"✅ 저장된 퀴즈 발견: {req.article_id}")
                quizzes = existing_quiz.get("quizzes", [])
                # 요청된 개수만큼 반환
                limited_quizzes = quizzes[:req.count]
                return QuizResponse(
                    quizzes=[QuizItem(**q) for q in limited_quizzes]
                )
            
            # [3단계] AI에 새 퀴즈 생성 요청
            logger.info(f"🤖 AI 퀴즈 생성 요청: article_id={req.article_id}, count={req.count}")
            prompt = self.prompt_templates.get_quiz_from_article_prompt(
                article.title, article.content, req.count
            )
            response = await self.llm_client.ainvoke(prompt)
            
            # LangChain의 BaseMessage 객체에서 content 추출
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)
            
            parsed = self.response_parser.parse_quiz_response(response_text)
            logger.info(f"✅ AI 퀴즈 생성 성공: {len(parsed.quizzes)}개")
            
            # [4단계] MongoDB에 저장
            logger.info(f"💾 퀴즈 저장 시작: article_id={req.article_id}")
            await self.db_client.save_quiz(
                source_type="ARTICLE",
                quizzes_data=parsed.quizzes,
                article_id=req.article_id,
                article_title=article.title
            )
            
            return parsed
            
        except ValueError as e:
            logger.error(f"❌ 기사 퀴즈 생성 실패 (입력 오류): {str(e)}")
            raise
        except Exception as e:
            logger.error(f"❌ 기사 퀴즈 생성 실패: {str(e)}")
            raise


# 전역 서비스 인스턴스
quiz_service = QuizService()


