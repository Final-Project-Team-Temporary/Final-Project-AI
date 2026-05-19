"""
[구현 의도]
RAG 프롬프트는 LLM이 검색된 기사 외 자체 지식을 사용하지 않도록
강제하는 것이 핵심이다.

"모른다면 모른다고 말하라"는 지시를 명시해야
LLM이 기사에 없는 내용을 지어내는 할루시네이션을 방지할 수 있다.
"""


class RAGPromptTemplates:

    SYSTEM_PROMPT = """당신은 경제 뉴스 전문 Q&A 어시스턴트입니다.
반드시 아래 [참고 기사] 내용만을 근거로 답변하세요.
참고 기사에 없는 내용은 절대 추측하거나 지어내지 마세요.
답변할 수 없는 경우 "제공된 기사에서 해당 정보를 찾을 수 없습니다"라고 명확히 말하세요."""

    ASK_PROMPT = """{system}

[참고 기사]
{context}

[질문]
{question}

[답변 형식]
- 핵심 답변을 먼저 제시하세요
- 각 문장 끝에 근거 기사 번호를 [출처N] 형식으로 표기하세요
- 참고한 기사만 출처로 포함하세요"""

    @classmethod
    def build_context(cls, retrieved_docs: list[dict]) -> str:
        """검색된 기사 목록을 LLM 컨텍스트 문자열로 조립한다."""
        lines = []
        for i, doc in enumerate(retrieved_docs, 1):
            meta = doc.get("metadata", {})
            title = meta.get("title", "제목 없음")
            published = meta.get("publishedAt", "날짜 미상")
            text = doc.get("text", "")
            lines.append(f"[기사{i}] {title} ({published})\n{text}")
        return "\n\n".join(lines)

    @classmethod
    def build_ask_prompt(cls, question: str, retrieved_docs: list[dict]) -> str:
        context = cls.build_context(retrieved_docs)
        return cls.ASK_PROMPT.format(
            system=cls.SYSTEM_PROMPT,
            context=context,
            question=question,
        )
