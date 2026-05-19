"""
[구현 의도]
EmbeddingService는 텍스트를 숫자 벡터로 변환하는 단일 책임을 가진다.
Google text-embedding-004 모델을 사용하며, RAG 파이프라인에서
"검색 가능한 형태로 문서를 변환"하는 첫 번째 단계다.

[이 서비스가 없으면 생기는 문제]
- 기사 본문을 그냥 저장하면 키워드 매칭만 가능 → 의미 기반 검색 불가
- "금리 인상" 기사가 "기준금리 올려" 라고 써있으면 못 찾음
- 임베딩이 있어야 "의미적으로 유사한" 기사를 찾을 수 있음

[엣지 케이스]
1. 빈 문자열 입력 → ValueError
2. None 입력 → ValueError
3. 매우 긴 텍스트 (토큰 한도 초과) → 자동으로 잘라서 처리
4. API 장애 → EmbeddingServiceError (래핑된 예외)
5. 반환 벡터의 차원이 예상(768)과 다를 때 → 검증 통과 (모델이 보장)
6. 한국어/영어 혼합 텍스트 → 정상 처리
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── 아직 구현체가 없으므로 import는 실패한다 (Red 상태) ──────────────────


class TestEmbeddingServiceInit:
    """EmbeddingService 초기화 검증"""

    def test_초기화시_gemini_api_키가_없으면_에러(self):
        """GEMINI_API_KEY 없이 초기화하면 즉시 실패해야 한다."""
        with patch("app.services.rag.embedding_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = ""
            mock_settings.EMBEDDING_MODEL = "models/text-embedding-004"

            from app.services.rag.embedding_service import EmbeddingService
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                EmbeddingService()

    def test_초기화시_임베딩_모델명이_설정된다(self):
        """초기화 후 모델명이 settings에서 주입된 값으로 설정되어야 한다."""
        with patch("app.services.rag.embedding_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = "test-key"
            mock_settings.EMBEDDING_MODEL = "models/text-embedding-004"

            from app.services.rag.embedding_service import EmbeddingService
            service = EmbeddingService()
            assert service.model_name == "models/text-embedding-004"


class TestEmbedText:
    """단일 텍스트 임베딩 생성"""

    @pytest.fixture
    def service(self):
        with patch("app.services.rag.embedding_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = "test-key"
            mock_settings.EMBEDDING_MODEL = "models/text-embedding-004"
            from app.services.rag.embedding_service import EmbeddingService
            return EmbeddingService()

    async def test_정상_텍스트_임베딩_반환(self, service):
        """일반 텍스트 입력 시 768차원 float 리스트를 반환해야 한다."""
        fake_vector = [0.1] * 768
        with patch.object(service, "_call_embedding_api", return_value=fake_vector):
            result = await service.embed_text("금리 인상이 부동산 시장에 미치는 영향")

        assert isinstance(result, list)
        assert len(result) == 768
        assert all(isinstance(v, float) for v in result)

    async def test_빈_문자열_입력시_ValueError(self, service):
        """빈 문자열은 임베딩 의미가 없으므로 즉시 거부해야 한다."""
        with pytest.raises(ValueError, match="비어있는 텍스트"):
            await service.embed_text("")

    async def test_None_입력시_ValueError(self, service):
        """None 입력은 타입 오류를 명확하게 알려야 한다."""
        with pytest.raises(ValueError, match="비어있는 텍스트"):
            await service.embed_text(None)

    async def test_공백만_있는_문자열_입력시_ValueError(self, service):
        """공백만 있는 문자열도 의미 없는 입력으로 거부해야 한다."""
        with pytest.raises(ValueError, match="비어있는 텍스트"):
            await service.embed_text("   ")

    async def test_API_장애시_EmbeddingServiceError(self, service):
        """외부 API 오류는 EmbeddingServiceError로 래핑해야 한다.

        이유: 호출자가 일반 Exception을 catch하지 않고
        명시적인 EmbeddingServiceError만 처리할 수 있도록.
        """
        from app.services.rag.embedding_service import EmbeddingServiceError
        with patch.object(service, "_call_embedding_api", side_effect=Exception("API timeout")):
            with pytest.raises(EmbeddingServiceError, match="임베딩 생성 실패"):
                await service.embed_text("금리 인상")

    async def test_매우_긴_텍스트는_잘라서_처리(self, service):
        """토큰 한도(2048 토큰 ≈ 8000자)를 넘는 텍스트는 잘라서 처리해야 한다.

        에러 대신 잘라서 처리하는 이유: 기사 본문이 길어도
        앞부분 내용만으로 충분히 의미 있는 벡터를 생성할 수 있음.
        """
        very_long_text = "경제 기사 내용 " * 2000  # ~14000자
        fake_vector = [0.1] * 768
        with patch.object(service, "_call_embedding_api", return_value=fake_vector) as mock_api:
            await service.embed_text(very_long_text)

        # API에 전달된 텍스트가 잘려있는지 확인
        actual_text = mock_api.call_args[0][0]
        assert len(actual_text) <= 8000


class TestEmbedBatch:
    """배치 임베딩 (여러 텍스트 동시 처리)"""

    @pytest.fixture
    def service(self):
        with patch("app.services.rag.embedding_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = "test-key"
            mock_settings.EMBEDDING_MODEL = "models/text-embedding-004"
            from app.services.rag.embedding_service import EmbeddingService
            return EmbeddingService()

    async def test_여러_텍스트_배치_임베딩(self, service):
        """N개 텍스트 입력 시 N개 벡터를 같은 순서로 반환해야 한다."""
        texts = ["금리 인상", "주식 시장 하락", "부동산 규제"]
        fake_vectors = [[float(i)] * 768 for i in range(len(texts))]

        with patch.object(service, "_call_embedding_api", side_effect=fake_vectors):
            results = await service.embed_batch(texts)

        assert len(results) == 3
        # 순서 보장: 첫 번째 텍스트의 벡터가 첫 번째로 와야 함
        assert results[0][0] == 0.0
        assert results[1][0] == 1.0
        assert results[2][0] == 2.0

    async def test_빈_리스트_입력시_빈_리스트_반환(self, service):
        """빈 리스트는 에러 없이 빈 리스트를 반환해야 한다."""
        results = await service.embed_batch([])
        assert results == []

    async def test_배치_중_일부_실패시_EmbeddingServiceError(self, service):
        """배치 처리 중 하나라도 실패하면 전체를 실패로 처리해야 한다.

        이유: 부분 성공한 벡터는 인덱싱이 어긋나 더 큰 버그를 유발함.
        """
        from app.services.rag.embedding_service import EmbeddingServiceError

        def fail_on_second(text):
            if "주식" in text:
                raise Exception("API error")
            return [0.1] * 768

        with patch.object(service, "_call_embedding_api", side_effect=fail_on_second):
            with pytest.raises(EmbeddingServiceError):
                await service.embed_batch(["금리 인상", "주식 시장"])
