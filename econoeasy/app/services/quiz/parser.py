"""퀴즈 응답 파싱"""

import json
import re
from ...models.schemas import QuizResponse, QuizItem


class QuizResponseParser:

    @staticmethod
    def parse_quiz_response(response_text: str) -> QuizResponse:
        try:
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                json_content = response_text[json_start:json_end].strip()
                parsed_data = json.loads(json_content)
            else:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_content = json_match.group()
                    parsed_data = json.loads(json_content)
                else:
                    raise ValueError("JSON 형식을 찾을 수 없습니다")

            quizzes = parsed_data.get("quizzes", [])
            normalized_quizzes = []
            for q in quizzes:
                normalized_quizzes.append(
                    QuizItem(
                        question=q.get("question", "").strip(),
                        options=q.get("options", []),
                        answer_index=q.get("answer_index", q.get("answerIndex", 0)),
                        explanation=q.get("explanation"),
                    )
                )

            return QuizResponse(quizzes=normalized_quizzes)
        except Exception as e:
            raise ValueError(f"퀴즈 응답 파싱 실패: {str(e)}")






