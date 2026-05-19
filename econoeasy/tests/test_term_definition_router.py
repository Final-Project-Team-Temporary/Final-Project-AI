"""
[TDD - Red Phase]
POST /keyword/define 라우터 테스트.

- article_content 없는 기본 요청
- article_content 포함 요청
- 빈 용어 → 400
- 서비스 오류 → 500
- 응답 스키마 검증
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


@pytest.fixture
def mock_result():
    from app.models.schemas import EnrichedTermDefineResponse
    return EnrichedTermDefineResponse(
        term="금리",
        definition="금리는 돈의 가격입니다.",
        article_context=None,
        recent_trend=None,
        sources=[],
    )


@pytest.fixture
def mock_result_full():
    from app.models.schemas import EnrichedTermDefineResponse
    return EnrichedTermDefineResponse(
        term="금리",
        definition="금리는 돈의 가격입니다.",
        article_context="이 기사에서 금리는 가계부채 위험 맥락으로 쓰였습니다.",
        recent_trend="최근 한국은행은 금리를 동결하고 있습니다.",
        sources=[
            {
                "article_id": "art_001",
                "title": "금리 인상 여파",
                "url": "https://example.com/1",
                "score": 0.75,
            }
        ],
    )


# ── 기본 요청 ─────────────────────────────────────────────────────────────────

def test_POST_define_용어만_요청_200(client, mock_result):
    with patch(
        "app.routers.keyword.term_definition_service.define_term",
        new=AsyncMock(return_value=mock_result),
    ):
        resp = client.post("/keyword/define", json={"term": "금리"})

    assert resp.status_code == 200


def test_POST_define_용어만_요청_응답_필드_존재(client, mock_result):
    with patch(
        "app.routers.keyword.term_definition_service.define_term",
        new=AsyncMock(return_value=mock_result),
    ):
        body = client.post("/keyword/define", json={"term": "금리"}).json()

    assert "term" in body
    assert "definition" in body
    assert "article_context" in body
    assert "recent_trend" in body
    assert "sources" in body


# ── article_content 포함 요청 ─────────────────────────────────────────────────

def test_POST_define_기사내용_포함_요청_200(client, mock_result_full):
    with patch(
        "app.routers.keyword.term_definition_service.define_term",
        new=AsyncMock(return_value=mock_result_full),
    ):
        resp = client.post(
            "/keyword/define",
            json={"term": "금리", "article_content": "금리 인상으로 가계부채가 늘었다."},
        )

    assert resp.status_code == 200


def test_POST_define_기사내용_포함_article_context_반환(client, mock_result_full):
    with patch(
        "app.routers.keyword.term_definition_service.define_term",
        new=AsyncMock(return_value=mock_result_full),
    ):
        body = client.post(
            "/keyword/define",
            json={"term": "금리", "article_content": "금리 인상으로 가계부채가 늘었다."},
        ).json()

    assert body["article_context"] is not None
    assert body["recent_trend"] is not None
    assert len(body["sources"]) == 1


# ── 입력 오류 ─────────────────────────────────────────────────────────────────

def test_POST_define_빈_용어_400(client):
    with patch(
        "app.routers.keyword.term_definition_service.define_term",
        new=AsyncMock(side_effect=ValueError("용어가 비어있습니다")),
    ):
        resp = client.post("/keyword/define", json={"term": ""})

    assert resp.status_code == 400


def test_POST_define_term_필드_없으면_422(client):
    resp = client.post("/keyword/define", json={})
    assert resp.status_code == 422


# ── 서비스 오류 ───────────────────────────────────────────────────────────────

def test_POST_define_서비스_오류_500(client):
    with patch(
        "app.routers.keyword.term_definition_service.define_term",
        new=AsyncMock(side_effect=Exception("LLM 호출 실패")),
    ):
        resp = client.post("/keyword/define", json={"term": "금리"})

    assert resp.status_code == 500
