"""요약 프롬프트 템플릿"""


class PromptTemplates:
    
    SUMMARY_PROMPT = """
다음 텍스트를 3가지 난이도로 요약해주세요.

반드시 다음 JSON 형식으로만 응답하세요:
{{
  "easy": "초등학생도 이해할 수 있는 간단한 요약",
  "medium": "일반인이 이해할 수 있는 요약",  
  "advanced": "전문적인 수준의 상세한 요약"
}}

텍스트:
{article}
"""
    
    @classmethod
    def get_summary_prompt(cls, article_content: str) -> str:
        """기사 내용을 받아 요약 프롬프트를 생성합니다."""
        return cls.SUMMARY_PROMPT.format(article=article_content)
