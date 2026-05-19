"""
[TDD - Red Phase]
TermDefinitionService 단위 테스트.

세 가지 값을 한 번에 반환한다:
  1. definition      : LLM 사전 지식 기반 일반 정의
  2. article_context : 사용자가 읽고 있는 기사에서 이 용어가 쓰인 맥락
  3. recent_trend    : ChromaDB에서 검색한 최근 기사들로부터 도출한 동향

article_content 없으면 article_context = None
ChromaDB 결과 없으면 recent_trend = None, sources = []
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── 픽스처 ────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_embedding_service():
    svc = MagicMock()
    svc.embed_text = AsyncMock(return_value=[0.1] * 3072)
    return svc


@pytest.fixture
def mock_vector_store():
    store = MagicMock()
    store.search = MagicMock(return_value=[])
    return store


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.ainvoke = AsyncMock()
    return llm


@pytest.fixture
def sample_search_results():
    return [
        {
            "article_id": "art_001",
            "text": "금리 인상으로 가계 대출 이자 부담이 증가하고 있다.",
            "score": 0.75,
            "metadata": {
                "title": "금리 인상 여파, 가계부채 급증",
                "url": "https://example.com/article1",
                "publishedAt": "2024-12-01",
            },
        },
        {
            "article_id": "art_002",
            "text": "한국은행 기준금리 동결 결정으로 시장 변동성이 줄어들었다.",
            "score": 0.61,
            "metadata": {
                "title": "한은, 기준금리 3.5% 동결",
                "url": "https://example.com/article2",
                "publishedAt": "2024-11-15",
            },
        },
    ]


def _make_llm_response(content: str):
    response = MagicMock()
    response.content = content
    return response


def _make_service(mock_embedding_service, mock_vector_store, mock_llm):
    """TermDefinitionService를 mock 의존성으로 생성."""
    with patch("app.services.keyword.term_definition_service.settings") as mock_settings:
        mock_settings.GEMINI_API_KEY = "test-key"
        mock_settings.GEMINI_MODEL = "gemini-2.5-flash"
        mock_settings.GEMINI_TEMPERATURE = 0.2
        mock_settings.RAG_TOP_K = 5
        mock_settings.RAG_MIN_SCORE = 0.4

        from app.services.keyword.term_definition_service import TermDefinitionService
        svc = TermDefinitionService(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
        )
        svc._llm = mock_llm
        return svc


# ── 입력 검증 ─────────────────────────────────────────────────────────────────

async def test_빈_용어_ValueError_발생(mock_embedding_service, mock_vector_store, mock_llm):
    svc = _make_service(mock_embedding_service, mock_vector_store, mock_llm)
    with pytest.raises(ValueError, match="용어"):
        await svc.define_term(term="")


async def test_공백만_있는_용어_ValueError_발생(mock_embedding_service, mock_vector_store, mock_llm):
    svc = _make_service(mock_embedding_service, mock_vector_store, mock_llm)
    with pytest.raises(ValueError, match="용어"):
        await svc.define_term(term="   ")


# ── 기사 없음 + ChromaDB 결과 없음 ─────────────────────────────────────────────

async def test_기사없음_크롬DB없음_definition만_반환(
    mock_embedding_service, mock_vector_store, mock_llm
):
    """article_content 없고 ChromaDB 결과도 없으면 definition만 채운다."""
    svc = _make_service(mock_embedding_service, mock_vector_store, mock_llm)
    llm_json = '{"definition": "금리는 돈의 가격입니다.", "article_context": null, "recent_trend": null}'
    mock_llm.ainvoke = AsyncMock(return_value=_make_llm_response(llm_json))

    result = await svc.define_term(term="금리")

    assert result.term == "금리"
    assert result.definition == "금리는 돈의 가격입니다."
    assert result.article_context is None
    assert result.recent_trend is None
    assert result.sources == []


async def test_기사없음_크롬DB없음_임베딩_호출됨(
    mock_embedding_service, mock_vector_store, mock_llm
):
    """결과가 없더라도 ChromaDB 검색을 시도하므로 embed_text는 반드시 호출된다."""
    svc = _make_service(mock_embedding_service, mock_vector_store, mock_llm)
    llm_json = '{"definition": "정의.", "article_context": null, "recent_trend": null}'
    mock_llm.ainvoke = AsyncMock(return_value=_make_llm_response(llm_json))

    await svc.define_term(term="금리")

    mock_embedding_service.embed_text.assert_called_once_with("금리")


# ── 기사 있음 (article_context) ────────────────────────────────────────────────

async def test_기사있음_article_context_채워짐(
    mock_embedding_service, mock_vector_store, mock_llm
):
    svc = _make_service(mock_embedding_service, mock_vector_store, mock_llm)
    llm_json = (
        '{"definition": "금리는 돈의 가격입니다.",'
        ' "article_context": "이 기사에서 금리는 가계부채 위험 맥락으로 쓰였습니다.",'
        ' "recent_trend": null}'
    )
    mock_llm.ainvoke = AsyncMock(return_value=_make_llm_response(llm_json))

    result = await svc.define_term(term="금리", article_content="금리 인상으로 가계부채가 늘었다.")

    assert result.article_context == "이 기사에서 금리는 가계부채 위험 맥락으로 쓰였습니다."
    assert result.sources == []


async def test_기사있음_임베딩_호출됨(mock_embedding_service, mock_vector_store, mock_llm):
    """article_content가 있어도 ChromaDB 검색을 시도하므로 embed_text는 호출된다."""
    svc = _make_service(mock_embedding_service, mock_vector_store, mock_llm)
    llm_json = '{"definition": "정의.", "article_context": "맥락.", "recent_trend": null}'
    mock_llm.ainvoke = AsyncMock(return_value=_make_llm_response(llm_json))

    await svc.define_term(term="금리", article_content="금리 관련 기사 내용")

    mock_embedding_service.embed_text.assert_called_once_with("금리")


# ── ChromaDB 결과 있음 (recent_trend) ─────────────────────────────────────────

async def test_크롬DB결과있음_recent_trend_채워짐(
    mock_embedding_service, mock_vector_store, mock_llm, sample_search_results
):
    mock_vector_store.search.return_value = sample_search_results
    svc = _make_service(mock_embedding_service, mock_vector_store, mock_llm)
    llm_json = (
        '{"definition": "금리는 돈의 가격입니다.",'
        ' "article_context": null,'
        ' "recent_trend": "최근 금리는 동결 기조입니다."}'
    )
    mock_llm.ainvoke = AsyncMock(return_value=_make_llm_response(llm_json))

    result = await svc.define_term(term="금리")

    assert result.recent_trend == "최근 금리는 동결 기조입니다."
    assert len(result.sources) == 2


async def test_크롬DB결과있음_sources_구조_올바름(
    mock_embedding_service, mock_vector_store, mock_llm, sample_search_results
):
    mock_vector_store.search.return_value = sample_search_results
    svc = _make_service(mock_embedding_service, mock_vector_store, mock_llm)
    llm_json = '{"definition": "정의.", "article_context": null, "recent_trend": "동향."}'
    mock_llm.ainvoke = AsyncMock(return_value=_make_llm_response(llm_json))

    result = await svc.define_term(term="금리")

    first = result.sources[0]
    assert first["article_id"] == "art_001"
    assert first["title"] == "금리 인상 여파, 가계부채 급증"
    assert first["url"] == "https://example.com/article1"
    assert first["score"] == 0.75


async def test_크롬DB결과있음_임베딩_호출됨(
    mock_embedding_service, mock_vector_store, mock_llm, sample_search_results
):
    """ChromaDB 검색을 위해 embed_text가 반드시 호출되어야 한다."""
    mock_vector_store.search.return_value = sample_search_results
    svc = _make_service(mock_embedding_service, mock_vector_store, mock_llm)
    llm_json = '{"definition": "정의.", "article_context": null, "recent_trend": "동향."}'
    mock_llm.ainvoke = AsyncMock(return_value=_make_llm_response(llm_json))

    await svc.define_term(term="금리")

    mock_embedding_service.embed_text.assert_called_once_with("금리")


# ── 기사 있음 + ChromaDB 결과 있음 (전체) ─────────────────────────────────────

async def test_기사있음_크롬DB있음_세_필드_모두_채워짐(
    mock_embedding_service, mock_vector_store, mock_llm, sample_search_results
):
    mock_vector_store.search.return_value = sample_search_results
    svc = _make_service(mock_embedding_service, mock_vector_store, mock_llm)
    llm_json = (
        '{"definition": "금리는 돈의 가격입니다.",'
        ' "article_context": "이 기사에서는 가계부채 위험 맥락으로 쓰였습니다.",'
        ' "recent_trend": "최근 금리는 동결 기조입니다."}'
    )
    mock_llm.ainvoke = AsyncMock(return_value=_make_llm_response(llm_json))

    result = await svc.define_term(
        term="금리",
        article_content="금리 인상으로 가계부채가 늘었다."
    )

    assert result.definition != ""
    assert result.article_context is not None
    assert result.recent_trend is not None
    assert len(result.sources) == 2


# ── LLM 응답 파싱 ──────────────────────────────────────────────────────────────

async def test_LLM_응답에_마크다운_코드블록_포함시_정상_파싱(
    mock_embedding_service, mock_vector_store, mock_llm
):
    """LLM이 ```json ... ``` 형식으로 응답해도 파싱된다."""
    svc = _make_service(mock_embedding_service, mock_vector_store, mock_llm)
    llm_json = '```json\n{"definition": "금리 정의.", "article_context": null, "recent_trend": null}\n```'
    mock_llm.ainvoke = AsyncMock(return_value=_make_llm_response(llm_json))

    result = await svc.define_term(term="금리")

    assert result.definition == "금리 정의."


async def test_LLM_빈_응답시_에러_발생(mock_embedding_service, mock_vector_store, mock_llm):
    svc = _make_service(mock_embedding_service, mock_vector_store, mock_llm)
    mock_llm.ainvoke = AsyncMock(return_value=_make_llm_response(""))

    with pytest.raises(Exception, match="응답"):
        await svc.define_term(term="금리")


async def test_LLM_JSON_파싱_실패시_definition_fallback(
    mock_embedding_service, mock_vector_store, mock_llm
):
    """JSON 파싱 실패해도 서비스가 죽지 않고 fallback 정의를 반환한다."""
    svc = _make_service(mock_embedding_service, mock_vector_store, mock_llm)
    mock_llm.ainvoke = AsyncMock(return_value=_make_llm_response("invalid json"))

    result = await svc.define_term(term="금리")

    assert result.term == "금리"
    assert result.definition != ""


# ── 외부 의존성 장애 ───────────────────────────────────────────────────────────

async def test_임베딩_실패시_ChromaDB_건너뛰고_definition만_반환(
    mock_embedding_service, mock_vector_store, mock_llm
):
    """embed_text 실패해도 서비스가 죽지 않고 definition만 반환한다."""
    mock_embedding_service.embed_text = AsyncMock(side_effect=Exception("임베딩 API 오류"))
    svc = _make_service(mock_embedding_service, mock_vector_store, mock_llm)
    llm_json = '{"definition": "금리 정의.", "article_context": null, "recent_trend": null}'
    mock_llm.ainvoke = AsyncMock(return_value=_make_llm_response(llm_json))

    result = await svc.define_term(term="금리")

    assert result.definition == "금리 정의."
    assert result.recent_trend is None
    assert result.sources == []


async def test_ChromaDB_검색_실패시_graceful_degradation(
    mock_embedding_service, mock_vector_store, mock_llm
):
    """vector_store.search 실패해도 definition은 반환한다."""
    mock_vector_store.search.side_effect = Exception("ChromaDB 연결 오류")
    svc = _make_service(mock_embedding_service, mock_vector_store, mock_llm)
    llm_json = '{"definition": "금리 정의.", "article_context": null, "recent_trend": null}'
    mock_llm.ainvoke = AsyncMock(return_value=_make_llm_response(llm_json))

    result = await svc.define_term(term="금리")

    assert result.definition == "금리 정의."
    assert result.sources == []
