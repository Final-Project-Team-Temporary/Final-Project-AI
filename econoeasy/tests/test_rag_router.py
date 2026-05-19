"""
[구현 의도]
RAG 라우터는 HTTP 요청/응답 변환만 담당한다.
비즈니스 로직은 RAGService에 완전히 위임하며,
HTTP 상태코드와 에러 메시지 형식만 책임진다.

[엔드포인트]
POST /rag/ask        - 질의응답
POST /rag/index      - 단일 기사 인덱싱 (내부용)

[엣지 케이스]
1. 요청 body가 없거나 question 필드가 없음 → 422 Unprocessable Entity
2. question이 빈 문자열 → 400 Bad Request
3. 관련 기사 없음 → 200 + "관련 기사 없음" 메시지
4. RAGService 내부 오류 → 500 Internal Server Error
5. 매우 긴 question (10000자 이상) → 400 Bad Request
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch


@pytest.fixture
def mock_rag_service():
    mock = AsyncMock()
    mock.ask.return_value = {
        "answer": "금리 인상은 대출 이자 부담을 늘립니다.",
        "sources": [
            {"title": "금리 인상 결정", "url": "http://news.com/1",
             "publishedAt": "2024-03-01", "score": 0.85}
        ]
    }
    return mock


@pytest.fixture
async def client(mock_rag_service):
    """RAGService를 mock으로 대체한 테스트 클라이언트.

    app.main을 먼저 임포트해야 app.routers.rag 모듈이 sys.modules에 등록되어
    patch가 올바르게 동작한다.
    """
    from app.main import app  # 모듈 등록 먼저
    with patch("app.routers.rag.rag_service", mock_rag_service):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac


class TestRagAskEndpoint:
    """POST /rag/ask"""

    async def test_정상_질문_200_응답(self, client):
        """정상 질문 시 200 코드와 answer, sources를 반환해야 한다."""
        response = await client.post("/rag/ask", json={"question": "금리 인상 영향은?"})

        assert response.status_code == 200
        body = response.json()
        assert "answer" in body
        assert "sources" in body

    async def test_question_필드_없으면_422(self, client):
        """question 필드가 없는 요청은 422를 반환해야 한다."""
        response = await client.post("/rag/ask", json={"wrong_field": "test"})
        assert response.status_code == 422

    async def test_빈_question_400(self, client, mock_rag_service):
        """빈 question은 400을 반환해야 한다."""
        mock_rag_service.ask.side_effect = ValueError("질문이 비어있습니다")
        response = await client.post("/rag/ask", json={"question": ""})
        assert response.status_code == 400

    async def test_관련기사_없을때_200_안내메시지(self, client, mock_rag_service):
        """검색 결과가 없어도 200으로 안내 메시지를 반환해야 한다."""
        mock_rag_service.ask.return_value = {
            "answer": "관련 기사를 찾을 수 없습니다. 다른 질문을 시도해보세요.",
            "sources": []
        }
        response = await client.post("/rag/ask", json={"question": "알 수 없는 주제"})
        assert response.status_code == 200
        assert response.json()["sources"] == []

    async def test_서비스_내부오류_500(self, client, mock_rag_service):
        """RAGService 예외는 500을 반환해야 한다."""
        from app.services.rag.rag_service import RAGServiceError
        mock_rag_service.ask.side_effect = RAGServiceError("LLM 오류")
        response = await client.post("/rag/ask", json={"question": "금리 인상"})
        assert response.status_code == 500

    async def test_매우_긴_question_400(self, client, mock_rag_service):
        """10000자 이상의 질문은 400을 반환해야 한다.

        이유: 과도하게 긴 입력은 임베딩 비용을 낭비하고
        프롬프트 컨텍스트 초과 가능성이 있음.
        """
        mock_rag_service.ask.side_effect = ValueError("질문이 너무 깁니다")
        long_question = "금리" * 5001  # 10002자
        response = await client.post("/rag/ask", json={"question": long_question})
        assert response.status_code == 400


class TestRagIndexEndpoint:
    """POST /rag/index - 기사 수동 인덱싱"""

    async def test_정상_인덱싱_200(self, client, mock_rag_service):
        """정상 기사 인덱싱 요청 시 200을 반환해야 한다."""
        mock_rag_service.index_article = AsyncMock()
        response = await client.post("/rag/index", json={
            "article_id": "a001",
            "title": "금리 인상 결정",
            "content": "한국은행이 기준금리를 인상했다.",
            "published_at": "2024-03-01",
            "url": "http://news.com/1"
        })
        assert response.status_code == 200

    async def test_content_없는_기사_400(self, client, mock_rag_service):
        """본문 없는 기사 인덱싱 요청은 400을 반환해야 한다."""
        mock_rag_service.index_article = AsyncMock(
            side_effect=ValueError("기사 본문이 비어있습니다")
        )
        response = await client.post("/rag/index", json={
            "article_id": "a001",
            "title": "제목만 있음",
            "content": "",
            "published_at": "2024-03-01",
            "url": "http://news.com/1"
        })
        assert response.status_code == 400
