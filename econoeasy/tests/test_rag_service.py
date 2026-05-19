"""
[구현 의도]
RAGService는 Retrieve → Augment → Generate 전체 파이프라인을 조율한다.
개별 컴포넌트(EmbeddingService, VectorStore, LLM)의 조합만 담당하며
직접 외부 API를 호출하지 않는다.

[파이프라인 흐름]
1. 질문 텍스트를 임베딩 벡터로 변환
2. VectorStore에서 유사 기사 top_k개 검색
3. 검색된 기사를 컨텍스트로 조립
4. "검색된 기사만 근거로 답하라" 프롬프트 + 컨텍스트 + 질문 → Gemini
5. 답변 + 출처 기사 목록 반환

[엣지 케이스]
1. 질문이 비어있을 때 → ValueError
2. 검색 결과가 0개일 때 → "관련 기사 없음" 안내 메시지 반환 (LLM 호출 안 함)
3. LLM이 빈 응답을 줄 때 → RAGServiceError
4. 검색된 기사 중 content가 비어있는 것 → 해당 기사 제외하고 진행
5. 매우 많은 기사가 검색돼 컨텍스트가 너무 길 때 → top_k로 제한
6. LLM 호출 중 타임아웃 → RAGServiceError (재시도 없음, 호출자에게 위임)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestRAGServiceAsk:
    """ask() - 핵심 질의응답 파이프라인"""

    @pytest.fixture
    def mock_embedding_service(self):
        mock = MagicMock()
        mock.embed_text = AsyncMock(return_value=[0.1] * 768)
        return mock

    @pytest.fixture
    def mock_vector_store(self):
        mock = MagicMock()
        mock.search.return_value = [
            {
                "article_id": "a1",
                "text": "한국은행이 기준금리를 0.25% 인상했다.",
                "score": 0.85,
                "metadata": {"title": "기준금리 인상 결정", "publishedAt": "2024-03-01", "url": "http://news.com/1"}
            },
            {
                "article_id": "a2",
                "text": "금리 인상으로 대출 이자 부담이 늘어났다.",
                "score": 0.78,
                "metadata": {"title": "대출 이자 부담 증가", "publishedAt": "2024-03-02", "url": "http://news.com/2"}
            }
        ]
        return mock

    @pytest.fixture
    def mock_llm(self):
        mock = MagicMock()
        mock.ainvoke = AsyncMock(return_value=MagicMock(
            content="한국은행은 2024년 3월 기준금리를 0.25% 인상했으며 [출처1], 이로 인해 대출 이자 부담이 증가했습니다 [출처2]."
        ))
        return mock

    @pytest.fixture
    def service(self, mock_embedding_service, mock_vector_store, mock_llm):
        with patch("app.services.rag.rag_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = "test-key"
            mock_settings.GEMINI_MODEL = "gemini-2.5-flash"
            mock_settings.GEMINI_TEMPERATURE = 0.0
            mock_settings.RAG_TOP_K = 5
            mock_settings.RAG_MIN_SCORE = 0.4

            from app.services.rag.rag_service import RAGService
            service = RAGService(
                embedding_service=mock_embedding_service,
                vector_store=mock_vector_store,
            )
            service._llm = mock_llm
            return service

    async def test_정상_질문_응답_반환(self, service):
        """질문에 대해 answer와 sources가 포함된 응답을 반환해야 한다."""
        result = await service.ask("금리 인상이 경제에 미치는 영향은?")

        assert "answer" in result
        assert "sources" in result
        assert len(result["sources"]) > 0

    async def test_출처_기사_정보_포함(self, service):
        """sources 각 항목에 title, url, publishedAt이 있어야 한다."""
        result = await service.ask("금리 인상 영향")

        for source in result["sources"]:
            assert "title" in source
            assert "url" in source
            assert "publishedAt" in source

    async def test_빈_질문_ValueError(self, service):
        """빈 질문은 임베딩 전에 거부해야 한다."""
        with pytest.raises(ValueError, match="질문이 비어있습니다"):
            await service.ask("")

    async def test_공백_질문_ValueError(self, service):
        """공백만 있는 질문도 거부해야 한다."""
        with pytest.raises(ValueError, match="질문이 비어있습니다"):
            await service.ask("   ")

    async def test_검색결과_없을때_안내메시지_반환(self, service, mock_vector_store, mock_llm):
        """관련 기사가 없으면 LLM 호출 없이 안내 메시지를 반환해야 한다.

        이유: 기사가 없는데 LLM을 호출하면 LLM 자체 지식으로 답변 → RAG 의미 없음.
        """
        mock_vector_store.search.return_value = []

        result = await service.ask("아무도 다루지 않은 주제")

        # LLM은 호출되지 않아야 한다
        mock_llm.ainvoke.assert_not_called()
        assert "관련 기사를 찾을 수 없습니다" in result["answer"]
        assert result["sources"] == []

    async def test_content_빈_기사는_컨텍스트에서_제외(self, service, mock_vector_store):
        """text가 빈 검색 결과는 LLM 컨텍스트에서 제외해야 한다.

        이유: 빈 텍스트를 컨텍스트에 포함하면 LLM이 혼란스러운 응답을 생성할 수 있음.
        """
        mock_vector_store.search.return_value = [
            {"article_id": "a1", "text": "", "score": 0.9,
             "metadata": {"title": "빈 기사", "publishedAt": "2024-01-01", "url": "http://a.com"}},
            {"article_id": "a2", "text": "정상적인 기사 내용", "score": 0.8,
             "metadata": {"title": "정상 기사", "publishedAt": "2024-01-02", "url": "http://b.com"}},
        ]

        result = await service.ask("테스트 질문")

        # 빈 기사(a1)는 sources에 포함되지 않아야 한다
        source_ids = [s.get("article_id") for s in result.get("sources", [])]
        assert "a1" not in source_ids

    async def test_LLM_빈_응답시_RAGServiceError(self, service, mock_llm):
        """LLM이 빈 content를 반환하면 RAGServiceError를 발생시켜야 한다."""
        from app.services.rag.rag_service import RAGServiceError
        mock_llm.ainvoke.return_value = MagicMock(content="")

        with pytest.raises(RAGServiceError, match="LLM이 빈 응답"):
            await service.ask("금리 인상 영향")

    async def test_임베딩_서비스_호출_확인(self, service, mock_embedding_service):
        """파이프라인에서 질문 임베딩이 반드시 호출되어야 한다."""
        await service.ask("금리 인상 영향")
        mock_embedding_service.embed_text.assert_called_once_with("금리 인상 영향")

    async def test_벡터스토어_검색_top_k_전달(self, service, mock_vector_store):
        """VectorStore 검색 시 settings의 top_k값이 전달되어야 한다."""
        await service.ask("금리 인상 영향")
        call_kwargs = mock_vector_store.search.call_args[1]
        assert "top_k" in call_kwargs
        assert call_kwargs["top_k"] == 5  # settings.RAG_TOP_K


class TestRAGServiceIndexArticle:
    """index_article() - 기사 인덱싱 (임베딩 생성 + 저장)"""

    @pytest.fixture
    def service(self):
        mock_embedding = MagicMock()
        mock_embedding.embed_text = AsyncMock(return_value=[0.1] * 768)
        mock_store = MagicMock()

        with patch("app.services.rag.rag_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = "test-key"
            mock_settings.GEMINI_MODEL = "gemini-2.5-flash"
            mock_settings.GEMINI_TEMPERATURE = 0.0
            mock_settings.RAG_TOP_K = 5
            mock_settings.RAG_MIN_SCORE = 0.4

            from app.services.rag.rag_service import RAGService
            service = RAGService(
                embedding_service=mock_embedding,
                vector_store=mock_store,
            )
            return service

    async def test_기사_인덱싱_임베딩_저장_호출(self, service):
        """기사 인덱싱 시 embed_text → vector_store.upsert 순서로 호출되어야 한다."""
        await service.index_article(
            article_id="a1",
            title="금리 인상 결정",
            content="한국은행이 기준금리를 인상했다.",
            published_at="2024-03-01",
            url="http://news.com/1"
        )

        service._embedding_service.embed_text.assert_called_once()
        service._vector_store.upsert.assert_called_once()

    async def test_인덱싱시_제목과_본문을_합쳐서_임베딩(self, service):
        """임베딩 품질 향상을 위해 '제목 + 본문'을 합쳐서 embed_text에 전달해야 한다.

        이유: 제목만 임베딩하면 본문의 의미가 누락되고,
        본문만 임베딩하면 핵심 주제어(제목)가 희석될 수 있음.
        """
        await service.index_article(
            article_id="a1",
            title="금리 인상 결정",
            content="한국은행이 기준금리를 인상했다.",
            published_at="2024-03-01",
            url="http://news.com/1"
        )

        called_text = service._embedding_service.embed_text.call_args[0][0]
        assert "금리 인상 결정" in called_text
        assert "한국은행이 기준금리를 인상했다" in called_text

    async def test_content_없는_기사_인덱싱_거부(self, service):
        """본문이 없는 기사는 인덱싱할 수 없다."""
        with pytest.raises(ValueError, match="기사 본문이 비어있습니다"):
            await service.index_article(
                article_id="a1",
                title="제목만 있는 기사",
                content="",
                published_at="2024-03-01",
                url="http://news.com/1"
            )
