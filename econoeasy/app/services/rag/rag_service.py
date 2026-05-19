"""
[구현 의도]
Retrieve → Augment → Generate 파이프라인 전체를 조율한다.
EmbeddingService, VectorStore, LLM 각각을 직접 생성하지 않고
생성자 주입(DI)으로 받아 테스트 시 mock으로 교체 가능하게 한다.
"""

import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from .embedding_service import EmbeddingService
from .vector_store import VectorStore
from .prompts import RAGPromptTemplates
from ...core.config import settings

logger = logging.getLogger(__name__)

MAX_QUESTION_LENGTH = 10000


class RAGServiceError(Exception):
    """RAG 파이프라인 내부 오류를 래핑하는 예외."""
    pass


class RAGService:

    def __init__(
        self,
        embedding_service: EmbeddingService = None,
        vector_store: VectorStore = None,
    ):
        self._embedding_service = embedding_service or EmbeddingService()
        self._vector_store = vector_store or VectorStore()
        self._llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=settings.GEMINI_TEMPERATURE,
        )

    async def ask(self, question: str) -> dict:
        """질문에 대해 관련 기사를 검색하고 근거 기반 답변을 생성한다.

        Returns:
            {"answer": str, "sources": list[dict]}
        """
        if not question or not question.strip():
            raise ValueError("질문이 비어있습니다")
        if len(question) > MAX_QUESTION_LENGTH:
            raise ValueError(f"질문이 너무 깁니다 (최대 {MAX_QUESTION_LENGTH}자)")

        # 1. 질문 임베딩
        query_vector = await self._embedding_service.embed_text(question)

        # 2. 유사 기사 검색
        retrieved = self._vector_store.search(
            query_vector=query_vector,
            top_k=settings.RAG_TOP_K,
            min_score=settings.RAG_MIN_SCORE,
        )

        # 3. 빈 content 기사 제거
        valid_docs = [doc for doc in retrieved if doc.get("text", "").strip()]

        # 4. 관련 기사가 없으면 LLM 호출 없이 안내 메시지 반환
        if not valid_docs:
            return {
                "answer": "관련 기사를 찾을 수 없습니다. 다른 키워드로 질문해보세요.",
                "sources": [],
            }

        # 5. 프롬프트 조립 후 Gemini 호출
        prompt = RAGPromptTemplates.build_ask_prompt(question, valid_docs)
        response = await self._llm.ainvoke(prompt)

        if not response.content or not response.content.strip():
            raise RAGServiceError("LLM이 빈 응답을 반환했습니다")

        # 6. 출처 목록 구성 (빈 text 기사 제외)
        sources = [
            {
                "article_id": doc["article_id"],
                "title": doc["metadata"].get("title", ""),
                "url": doc["metadata"].get("url", ""),
                "publishedAt": doc["metadata"].get("publishedAt", ""),
                "score": doc["score"],
            }
            for doc in valid_docs
        ]

        return {"answer": response.content, "sources": sources}

    async def index_article(
        self,
        article_id: str,
        title: str,
        content: str,
        published_at: str,
        url: str,
    ) -> None:
        """기사를 임베딩해 벡터 스토어에 저장한다.

        제목 + 본문을 합쳐 임베딩하면 의미적 검색 품질이 향상된다.
        """
        if not content or not content.strip():
            raise ValueError("기사 본문이 비어있습니다")

        # 제목 + 본문 합산 임베딩
        combined_text = f"{title}\n{content}"
        vector = await self._embedding_service.embed_text(combined_text)

        self._vector_store.upsert(
            article_id=article_id,
            vector=vector,
            text=content,
            metadata={
                "title": title,
                "publishedAt": published_at,
                "url": url,
            },
        )
        logger.info(f"기사 인덱싱 완료: {article_id}")


rag_service = RAGService()
