"""경제 용어 추출 프롬프트 템플릿"""

class KeywordPromptTemplates:

    TERMS_PROMPT = """
당신은 경제 뉴스 분석 전문가입니다.

아래 기사 내용을 읽고, 독자가 이해해야 할 **주요 경제 용어 3개**를 선택하세요.
각 용어(`term`)와 해당 개념(`term_summary`)을 1~2문장으로 간결히 설명하세요.

반드시 다음 JSON 형식으로만 응답하세요:
[
  {{"term": "인플레이션", "term_summary": "물가가 지속적으로 상승하는 현상입니다."}},
  {{"term": "금리 인상", "term_summary": "중앙은행이 기준금리를 높여 시중 자금 유동성을 줄이는 조치입니다."}},
  {{"term": "무역수지", "term_summary": "수출과 수입의 차이로 국가의 대외거래 상황을 나타냅니다."}}
]

기사 내용:
{article}
"""

    @classmethod
    def get_terms_prompt(cls, article_content: str) -> str:
        """기사 내용을 받아 프롬프트를 생성합니다."""
        return cls.TERMS_PROMPT.format(article=article_content)
