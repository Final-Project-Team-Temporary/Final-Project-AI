"""
[구현 의도]
용어 설명의 세 레이어를 단일 LLM 호출로 조합한다.

  ① definition      : 항상 생성 (LLM 사전 지식)
  ② article_context : article_content 있을 때만 → 기사 본문을 프롬프트에 직접 주입
  ③ recent_trend    : ChromaDB 검색 결과 있을 때만 → 검색된 기사를 컨텍스트로 주입

외부 의존성(임베딩, ChromaDB) 실패는 graceful degradation:
  - 임베딩/검색 실패 → recent_trend=None, sources=[]로 처리, 서비스 중단 없음
  - LLM 응답 빈 문자열 → 명시적 에러 발생
  - JSON 파싱 실패 → 전체 응답을 definition에 fallback

EmbeddingService, VectorStore를 생성자 주입(DI)으로 받아 테스트 시 mock 교체 가능.
"""

import json
import logging
import re
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from ...core.config import settings
from ...models.schemas import EnrichedTermDefineResponse
from ..rag.embedding_service import EmbeddingService
from ..rag.vector_store import VectorStore
from .term_definition_prompts import TermDefinitionPrompts

logger = logging.getLogger(__name__)


class TermDefinitionServiceError(Exception):
    pass


class TermDefinitionService:

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
            temperature=0.2,
        )

    async def define_term(
        self,
        term: str,
        article_content: str | None = None,
    ) -> EnrichedTermDefineResponse:
        """용어에 대한 정의·기사 맥락·최근 동향을 한 번에 반환한다."""
        if not term or not term.strip():
            raise ValueError("용어가 비어있습니다")

        # ChromaDB 검색 (실패해도 서비스 계속)
        trend_docs, sources = await self._search_trend(term)

        # 단일 LLM 호출로 세 가지 설명 생성
        prompt = TermDefinitionPrompts.build(
            term=term,
            article_content=article_content,
            trend_docs=trend_docs,
        )
        response = await self._llm.ainvoke([HumanMessage(content=prompt)])

        if not response.content or not response.content.strip():
            raise TermDefinitionServiceError("LLM이 빈 응답을 반환했습니다")

        parsed = self._parse_response(response.content)

        return EnrichedTermDefineResponse(
            term=term,
            definition=parsed.get("definition", response.content),
            article_context=parsed.get("article_context"),
            recent_trend=parsed.get("recent_trend"),
            sources=sources,
        )

    async def _search_trend(self, term: str) -> tuple[list[dict], list[dict]]:
        """용어로 ChromaDB 검색. 실패 시 빈 결과 반환."""
        try:
            query_vector = await self._embedding_service.embed_text(term)
            # 단어 하나로 검색하므로 문장 질문보다 유사도가 낮게 나옴
            # RAG_MIN_SCORE(0.4)보다 낮은 0.3을 사용해 관련 기사를 더 많이 포함
            docs = self._vector_store.search(
                query_vector=query_vector,
                top_k=settings.RAG_TOP_K,
                min_score=0.3,
            )
            sources = [
                {
                    "article_id": doc["article_id"],
                    "title": doc["metadata"].get("title", ""),
                    "url": doc["metadata"].get("url", ""),
                    "score": doc["score"],
                }
                for doc in docs
            ]
            return docs, sources
        except Exception as e:
            logger.warning(f"용어 동향 검색 실패 (무시됨): {term} - {e}")
            return [], []

    def _parse_response(self, content: str) -> dict:
        """LLM 응답에서 JSON을 추출한다. 실패 시 빈 dict 반환."""
        # 마크다운 코드블록 제거
        cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", content).strip()
        try:
            data = json.loads(cleaned)
            # null 값은 None으로 통일
            return {k: (v if v != "null" else None) for k, v in data.items()}
        except (json.JSONDecodeError, Exception):
            logger.warning("LLM JSON 파싱 실패, fallback 처리")
            return {}


term_definition_service = TermDefinitionService()
