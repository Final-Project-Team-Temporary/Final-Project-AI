"""LLM 응답 파싱"""

import json
import re
from typing import Dict, Any
from ...models.schemas import SummaryOutput

class ResponseParser:
    
    @staticmethod
    def parse_summary_response(response_text: str) -> SummaryOutput:
        """요약 응답을 파싱하여 SummaryOutput 객체를 반환합니다."""
        try:
            # JSON 파싱
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                json_content = response_text[json_start:json_end].strip()
                parsed_data = json.loads(json_content)
            else:
                # 일반 텍스트에서 JSON 추출
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_content = json_match.group()
                    parsed_data = json.loads(json_content)
                else:
                    raise ValueError("JSON 형식을 찾을 수 없습니다")
            
            return SummaryOutput(**parsed_data)
            
        except Exception as e:
            raise ValueError(f"응답 파싱 실패: {str(e)}")
    
    @staticmethod
    def create_fallback_summary(content: str) -> SummaryOutput:
        """API 실패 시 기본 요약을 생성합니다."""
        return SummaryOutput(
            easy=content[:100] + "..." if len(content) > 100 else content,
            medium=content[:200] + "..." if len(content) > 200 else content,
            advanced=content[:300] + "..." if len(content) > 300 else content
        )
