"""
[구현 의도]
ChromaDB와의 통신을 캡슐화한다.
저장(upsert) / 검색(search) / 삭제(delete) 세 가지 인터페이스만 노출.

[Lazy 연결 방식 선택 이유]
__init__에서 바로 ChromaDB에 연결하면:
- 테스트 환경에서 ChromaDB가 없어도 모듈 임포트 자체가 실패함
- 서버 시작 시 ChromaDB가 잠깐 꺼져있으면 전체 앱이 기동 불가
따라서 첫 실제 작업 시(_ensure_connected) 연결한다.
"""

import chromadb
import logging
from ...core.config import settings

logger = logging.getLogger(__name__)


class VectorStoreError(Exception):
    """ChromaDB 연동 오류를 래핑하는 예외."""
    pass


class VectorStore:

    def __init__(self):
        # 연결 파라미터만 저장, 실제 연결은 첫 사용 시(_ensure_connected)
        self._host = settings.CHROMA_HOST
        self._port = settings.CHROMA_PORT
        self._collection_name = settings.CHROMA_COLLECTION_NAME
        self._client = None
        self._collection = None

    def _ensure_connected(self):
        """첫 사용 시 ChromaDB에 연결한다."""
        if self._collection is not None:
            return
        try:
            self._client = chromadb.HttpClient(
                host=self._host,
                port=self._port,
            )
            self._collection = self._client.get_or_create_collection(
                self._collection_name
            )
        except Exception as e:
            raise VectorStoreError(f"ChromaDB 연결 실패: {e}") from e

    def upsert(
        self,
        article_id: str,
        vector: list[float],
        text: str,
        metadata: dict,
    ) -> None:
        """기사를 벡터 스토어에 저장한다. 같은 ID면 덮어쓴다."""
        if not vector:
            raise VectorStoreError("벡터가 비어있음: 임베딩을 먼저 생성해야 합니다")

        self._ensure_connected()
        self._collection.upsert(
            ids=[article_id],
            embeddings=[vector],
            documents=[text],
            metadatas=[metadata],
        )

    def search(
        self,
        query_vector: list[float],
        top_k: int,
        min_score: float,
    ) -> list[dict]:
        """유사 기사를 검색한다.

        ChromaDB는 distance(낮을수록 유사)를 반환하므로
        score = 1 - distance 변환 후 min_score 미만은 필터링한다.
        """
        self._ensure_connected()
        results = self._collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
        )

        ids = results["ids"][0]
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        output = []
        for article_id, text, meta, distance in zip(ids, documents, metadatas, distances):
            score = 1.0 - distance
            if score < min_score:
                continue
            output.append({
                "article_id": article_id,
                "text": text,
                "score": round(score, 4),
                "metadata": meta,
            })

        return output

    def delete(self, article_id: str) -> None:
        """기사를 벡터 스토어에서 삭제한다. 없는 ID는 무시한다."""
        try:
            self._ensure_connected()
            self._collection.delete(ids=[article_id])
        except VectorStoreError:
            raise
        except Exception as e:
            # 없는 ID 삭제 시 발생하는 오류는 경고만 남기고 무시
            logger.warning(f"벡터 삭제 실패 (무시됨): {article_id} - {e}")


vector_store = VectorStore()
