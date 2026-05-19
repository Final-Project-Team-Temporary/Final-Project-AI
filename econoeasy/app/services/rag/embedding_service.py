"""
[구현 의도]
텍스트 → 768차원 float 벡터 변환 단일 책임.
langchain-google-genai의 GoogleGenerativeAIEmbeddings 사용.
(기존 Gemini LLM과 동일한 패키지, API 키 재사용)
호출자는 벡터 DB가 뭔지, 모델이 뭔지 몰라도 된다.
"""

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from ...core.config import settings


class EmbeddingServiceError(Exception):
    """외부 임베딩 API 오류를 래핑하는 예외."""
    pass


class EmbeddingService:

    MAX_TEXT_LENGTH = 8000  # 토큰 한도 초과 방지용 문자 수 기준

    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다")
        self.model_name = settings.EMBEDDING_MODEL
        self._embeddings = GoogleGenerativeAIEmbeddings(
            model=self.model_name,
            google_api_key=settings.GEMINI_API_KEY,
        )

    async def embed_text(self, text: str) -> list[float]:
        """단일 텍스트를 임베딩 벡터로 변환한다.

        긴 텍스트는 MAX_TEXT_LENGTH 기준으로 잘라 처리한다.
        """
        if not text or not text.strip():
            raise ValueError("비어있는 텍스트는 임베딩할 수 없습니다")

        truncated = text[:self.MAX_TEXT_LENGTH]
        try:
            return await self._call_embedding_api(truncated)
        except EmbeddingServiceError:
            raise
        except Exception as e:
            raise EmbeddingServiceError(f"임베딩 생성 실패: {e}") from e

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """여러 텍스트를 순서 보장하며 임베딩한다.

        하나라도 실패하면 전체를 EmbeddingServiceError로 처리한다.
        부분 성공 허용 시 인덱스가 어긋나는 버그가 생기기 때문.
        """
        if not texts:
            return []

        results = []
        try:
            for text in texts:
                vector = await self._call_embedding_api(text)
                results.append(vector)
        except Exception as e:
            raise EmbeddingServiceError(f"배치 임베딩 실패: {e}") from e

        return results

    async def _call_embedding_api(self, text: str) -> list[float]:
        """LangChain GoogleGenerativeAIEmbeddings 비동기 호출."""
        result = await self._embeddings.aembed_query(text)
        return result


embedding_service = EmbeddingService()
