"""
[구현 의도]
세 가지 설명을 단일 LLM 호출로 생성한다.
  1. definition      : 용어의 일반적 정의
  2. article_context : 사용자가 읽는 기사에서 이 용어가 쓰인 맥락 (기사 있을 때만)
  3. recent_trend    : 최근 뉴스 기사들에서 이 용어의 동향 (ChromaDB 결과 있을 때만)

항목이 없을 때 null을 반환하도록 프롬프트에 명시한다.
"""


class TermDefinitionPrompts:

    _BASE = """당신은 경제/금융 전문 설명가입니다.
아래 지시에 따라 용어를 설명하고, 반드시 JSON 형식으로만 응답하세요.

용어: "{term}"

{article_section}{trend_section}
다음 JSON 형식으로 응답하세요:
{{
  "definition": "이 용어의 일반적인 정의 (2-3문장, 비전문가도 이해할 수 있게)",
  "article_context": {article_context_instruction},
  "recent_trend": {recent_trend_instruction}
}}"""

    _ARTICLE_SECTION = """[사용자가 읽고 있는 기사]
{article_content}

"""

    _TREND_SECTION = """[최근 관련 뉴스 기사들]
{trend_context}

"""

    @classmethod
    def build(
        cls,
        term: str,
        article_content: str | None,
        trend_docs: list[dict],
    ) -> str:
        article_section = ""
        article_context_instruction = "null"

        if article_content and article_content.strip():
            article_section = cls._ARTICLE_SECTION.format(
                article_content=article_content[:3000]
            )
            article_context_instruction = (
                '"위 기사에서 이 용어가 어떤 역할/맥락으로 사용되었는지 2문장으로 설명"'
            )

        trend_section = ""
        recent_trend_instruction = "null"

        if trend_docs:
            trend_lines = []
            for i, doc in enumerate(trend_docs, 1):
                meta = doc.get("metadata", {})
                title = meta.get("title", "")
                published = meta.get("publishedAt", "")
                text = doc.get("text", "")[:500]
                trend_lines.append(f"[기사{i}] {title} ({published})\n{text}")
            trend_section = cls._TREND_SECTION.format(
                trend_context="\n\n".join(trend_lines)
            )
            recent_trend_instruction = (
                '"위 최근 기사들을 바탕으로, 현재 이 용어와 관련된 뉴스 동향을 2-3문장으로 설명"'
            )

        return cls._BASE.format(
            term=term,
            article_section=article_section,
            trend_section=trend_section,
            article_context_instruction=article_context_instruction,
            recent_trend_instruction=recent_trend_instruction,
        )
