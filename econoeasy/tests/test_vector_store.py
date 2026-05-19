"""
[구현 의도]
VectorStore는 ChromaDB와의 모든 통신을 캡슐화한다.
"어떤 벡터 DB를 쓰는가"를 RAGService가 알 필요 없도록
저장(upsert) / 검색(search) / 삭제(delete) 인터페이스만 노출한다.

[이 레이어가 필요한 이유]
- ChromaDB SDK가 바뀌어도 이 파일만 수정하면 됨
- 테스트에서 ChromaDB 서버 없이 mock으로 대체 가능
- 나중에 MongoDB Atlas Vector Search로 교체할 때도 인터페이스 유지

[엣지 케이스]
1. ChromaDB 서버가 꺼져있을 때 → VectorStoreError
2. 동일 article_id를 두 번 저장 → upsert (덮어쓰기, 에러 아님)
3. 존재하지 않는 article_id 삭제 → 에러 없이 무시
4. 검색 결과가 0개일 때 → 빈 리스트 반환 (에러 아님)
5. top_k보다 저장된 문서가 적을 때 → 있는 것만 반환
6. min_score 임계값보다 낮은 결과 → 필터링해서 제외
7. 컬렉션이 아직 없을 때 → 자동 생성
"""

import pytest
from unittest.mock import MagicMock, patch


class TestVectorStoreInit:
    """VectorStore 초기화 및 연결 검증"""

    def test_ChromaDB_연결_실패시_첫_사용에서_VectorStoreError(self):
        """ChromaDB 서버가 없으면 첫 작업(upsert/search) 시 VectorStoreError를 내야 한다.

        lazy 연결 방식: __init__에서 연결하지 않고 첫 사용 시 연결.
        덕분에 ChromaDB가 잠깐 내려가도 서버 기동 자체는 성공함.
        """
        from app.services.rag.vector_store import VectorStore, VectorStoreError
        store = VectorStore()
        # _ensure_connected를 통해 실제 연결 시도 → 실패
        with patch("app.services.rag.vector_store.chromadb.HttpClient") as mock_client:
            mock_client.side_effect = Exception("Connection refused")
            with pytest.raises(VectorStoreError, match="ChromaDB 연결 실패"):
                store.upsert("a1", [0.1] * 3, "text", {})

    def test_컬렉션이_없으면_자동_생성(self):
        """지정한 컬렉션이 없어도 get_or_create로 자동 생성해야 한다."""
        mock_chroma = MagicMock()
        mock_collection = MagicMock()
        mock_chroma.get_or_create_collection.return_value = mock_collection

        with patch("app.services.rag.vector_store.chromadb.HttpClient", return_value=mock_chroma):
            from app.services.rag.vector_store import VectorStore
            store = VectorStore()
            store._ensure_connected()

        mock_chroma.get_or_create_collection.assert_called_once()


class TestVectorStoreUpsert:
    """문서 저장 (upsert)"""

    @pytest.fixture
    def store(self):
        mock_chroma = MagicMock()
        mock_collection = MagicMock()
        mock_chroma.get_or_create_collection.return_value = mock_collection

        with patch("app.services.rag.vector_store.chromadb.HttpClient", return_value=mock_chroma):
            with patch("app.services.rag.vector_store.settings") as mock_settings:
                mock_settings.CHROMA_HOST = "localhost"
                mock_settings.CHROMA_PORT = 8001
                mock_settings.CHROMA_COLLECTION_NAME = "test_col"

                from app.services.rag.vector_store import VectorStore
                store = VectorStore()
                store._collection = mock_collection
                return store

    def test_정상_문서_저장(self, store):
        """article_id, 벡터, 텍스트, 메타데이터를 받아 ChromaDB에 저장해야 한다."""
        store.upsert(
            article_id="article_001",
            vector=[0.1] * 768,
            text="금리 인상 기사 본문",
            metadata={"title": "금리 인상", "publishedAt": "2024-01-01"}
        )
        store._collection.upsert.assert_called_once()

    def test_동일_id_재저장시_덮어쓰기(self, store):
        """같은 article_id로 두 번 저장하면 에러 없이 업데이트되어야 한다."""
        store.upsert("article_001", [0.1] * 768, "첫 번째 내용", {})
        store.upsert("article_001", [0.2] * 768, "업데이트된 내용", {})
        # upsert가 두 번 호출되어야 한다 (에러 없음)
        assert store._collection.upsert.call_count == 2

    def test_벡터_차원이_0이면_VectorStoreError(self, store):
        """빈 벡터는 저장할 수 없다."""
        from app.services.rag.vector_store import VectorStoreError
        with pytest.raises(VectorStoreError, match="벡터가 비어있음"):
            store.upsert("article_001", [], "내용", {})


class TestVectorStoreSearch:
    """유사 문서 검색"""

    @pytest.fixture
    def store(self):
        mock_chroma = MagicMock()
        mock_collection = MagicMock()
        mock_chroma.get_or_create_collection.return_value = mock_collection

        with patch("app.services.rag.vector_store.chromadb.HttpClient", return_value=mock_chroma):
            with patch("app.services.rag.vector_store.settings") as mock_settings:
                mock_settings.CHROMA_HOST = "localhost"
                mock_settings.CHROMA_PORT = 8001
                mock_settings.CHROMA_COLLECTION_NAME = "test_col"

                from app.services.rag.vector_store import VectorStore
                store = VectorStore()
                store._collection = mock_collection
                return store

    def test_검색결과_top_k개_반환(self, store):
        """top_k=3 요청 시 최대 3개의 결과를 반환해야 한다."""
        store._collection.query.return_value = {
            "ids": [["a1", "a2", "a3"]],
            "documents": [["내용1", "내용2", "내용3"]],
            "metadatas": [[{"title": "t1"}, {"title": "t2"}, {"title": "t3"}]],
            "distances": [[0.1, 0.2, 0.3]],
        }
        results = store.search(query_vector=[0.1] * 768, top_k=3, min_score=0.0)
        assert len(results) == 3

    def test_min_score_미만_결과_필터링(self, store):
        """distance가 min_score(유사도 임계값)보다 낮은 결과는 제거해야 한다.

        ChromaDB는 distance(거리, 낮을수록 유사)를 반환하므로
        score = 1 - distance 변환 후 min_score와 비교한다.
        """
        store._collection.query.return_value = {
            "ids": [["a1", "a2"]],
            "documents": [["관련 기사", "관련없는 기사"]],
            "metadatas": [[{"title": "관련"}, {"title": "무관"}]],
            # distance 0.4 → score 0.6 (통과), distance 0.8 → score 0.2 (필터링)
            "distances": [[0.4, 0.8]],
        }
        results = store.search(query_vector=[0.1] * 768, top_k=5, min_score=0.5)
        assert len(results) == 1
        assert results[0]["article_id"] == "a1"

    def test_검색결과_없을때_빈_리스트(self, store):
        """매칭되는 문서가 없으면 빈 리스트를 반환해야 한다 (에러 아님)."""
        store._collection.query.return_value = {
            "ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]
        }
        results = store.search(query_vector=[0.1] * 768, top_k=5, min_score=0.4)
        assert results == []

    def test_저장된_문서가_top_k보다_적을때(self, store):
        """top_k=5인데 문서가 2개뿐이면 2개만 반환해야 한다."""
        store._collection.query.return_value = {
            "ids": [["a1", "a2"]],
            "documents": [["내용1", "내용2"]],
            "metadatas": [[{"title": "t1"}, {"title": "t2"}]],
            "distances": [[0.1, 0.2]],
        }
        results = store.search(query_vector=[0.1] * 768, top_k=5, min_score=0.0)
        assert len(results) == 2

    def test_검색결과에_score_필드_포함(self, store):
        """반환된 각 결과에 score(유사도 0~1) 필드가 있어야 한다."""
        store._collection.query.return_value = {
            "ids": [["a1"]],
            "documents": [["내용"]],
            "metadatas": [[{"title": "제목"}]],
            "distances": [[0.3]],
        }
        results = store.search(query_vector=[0.1] * 768, top_k=1, min_score=0.0)
        assert "score" in results[0]
        assert abs(results[0]["score"] - 0.7) < 0.001  # 1 - 0.3


class TestVectorStoreDelete:
    """문서 삭제"""

    @pytest.fixture
    def store(self):
        mock_chroma = MagicMock()
        mock_collection = MagicMock()
        mock_chroma.get_or_create_collection.return_value = mock_collection

        with patch("app.services.rag.vector_store.chromadb.HttpClient", return_value=mock_chroma):
            with patch("app.services.rag.vector_store.settings") as mock_settings:
                mock_settings.CHROMA_HOST = "localhost"
                mock_settings.CHROMA_PORT = 8001
                mock_settings.CHROMA_COLLECTION_NAME = "test_col"

                from app.services.rag.vector_store import VectorStore
                store = VectorStore()
                store._collection = mock_collection
                return store

    def test_존재하는_문서_삭제(self, store):
        """정상적인 article_id로 삭제 호출 시 ChromaDB delete가 실행되어야 한다."""
        store.delete("article_001")
        store._collection.delete.assert_called_once_with(ids=["article_001"])

    def test_존재하지않는_id_삭제시_에러없음(self, store):
        """없는 ID를 삭제해도 에러 없이 무시해야 한다.

        이유: 삭제 시점에 이미 다른 워커가 지웠을 수 있는 경쟁 조건 처리.
        """
        store._collection.delete.side_effect = Exception("ID not found")
        # 에러가 발생하지 않아야 함
        store.delete("nonexistent_id")
