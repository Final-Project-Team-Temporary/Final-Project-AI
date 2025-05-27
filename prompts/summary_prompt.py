SUMMARY_PROMPT = """
다음 기사를 읽고 EASY, MEDIUM, ADVANCED 난이도로 각각 요약해주세요.

- EASY: 뉴스에 익숙하지 않은 사람이 이해할 수 있도록 짧은 문장과 쉬운 단어를 사용. 전문 용어나 숫자는 최대한 생략.
- MEDIUM: 일반 뉴스 요약 수준. 가장 중요한 내용 위주로 구성.
- ADVANCED: 경제 전문 독자를 위한 수준. 수치와 원인 분석 포함.

다음 형식을 그대로 따르세요:
{format_instructions}

기사:
{article}
"""
