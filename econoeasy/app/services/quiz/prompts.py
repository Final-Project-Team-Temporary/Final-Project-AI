"""퀴즈 프롬프트 템플릿"""


class QuizPromptTemplates:

    QUIZ_FROM_KEYWORD_PROMPT = """
당신은 국내 경제 기사 학습을 돕는 객관식 퀴즈 출제자입니다.
다음 키워드에 대해 학습용 객관식 퀴즈를 {count}문항 생성하세요.

반드시 아래 JSON 스키마 형식으로만 응답하세요:
{{
  "quizzes": [
    {{
      "question": "질문 내용",
      "options": ["보기1", "보기2", "보기3", "보기4"],
      "answer_index": 0,
      "explanation": "왜 정답인지 간단 설명"
    }}
  ]
}}

키워드: {keyword}
"""

    QUIZ_FROM_ARTICLE_PROMPT = """
당신은 국내 경제 기사 학습을 돕는 객관식 퀴즈 출제자입니다.
다음 기사 본문을 바탕으로 핵심 개념을 점검하는 객관식 퀴즈를 {count}문항 생성하세요.

반드시 아래 JSON 스키마 형식으로만 응답하세요:
{{
  "quizzes": [
    {{
      "question": "질문 내용",
      "options": ["보기1", "보기2", "보기3", "보기4"],
      "answer_index": 0,
      "explanation": "왜 정답인지 간단 설명"
    }}
  ]
}}

기사 제목: {title}
기사 본문:
{content}
"""

    @classmethod
    def get_quiz_from_keyword_prompt(cls, keyword: str, count: int) -> str:
        return cls.QUIZ_FROM_KEYWORD_PROMPT.format(keyword=keyword, count=count)

    @classmethod
    def get_quiz_from_article_prompt(cls, title: str, content: str, count: int) -> str:
        return cls.QUIZ_FROM_ARTICLE_PROMPT.format(title=title, content=content, count=count)






