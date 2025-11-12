"""LLM 응답 파싱"""

import json
import re
from typing import List
from econoeasy.app.models.schemas import (
     TermSummary, KeywordTermsResponse
)

class KeywordResponseParser:

    @staticmethod
    def parse_terms_response(response_text: str) -> KeywordTermsResponse:
        """LLM의 응답에서 term/term_summary 리스트를 파싱"""
        try:
            # 코드 블록(JSON) 포함 시
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                json_content = response_text[json_start:json_end].strip()
                parsed_data = json.loads(json_content)
            else:
                # 일반 JSON 텍스트 검색
                json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                if json_match:
                    json_content = json_match.group()
                    parsed_data = json.loads(json_content)
                else:
                    raise ValueError("JSON 형식을 찾을 수 없습니다.")

            results = [
                TermSummary(term=i["term"], term_summary=i["term_summary"])
                for i in parsed_data if "term" in i
            ]
            return KeywordTermsResponse(results=results)

        except Exception as e:
            raise ValueError(f"응답 파싱 실패: {str(e)}")

    @staticmethod
    def create_fallback_terms(article_content: str) -> KeywordTermsResponse:
        """API 실패 시 간단한 fallback 생성"""
        default_term = TermSummary(
            term="경제 동향",
            term_summary=article_content[:100] + "..." if len(article_content) > 100 else article_content
        )
        return KeywordTermsResponse(results=[default_term])
