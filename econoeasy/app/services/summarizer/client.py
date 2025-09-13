"""Gemini API 클라이언트"""

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from ...core.config import settings

class LLMClient:
    
    def __init__(self):
        # API 키 설정
        os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY
        
        # Gemini LLM 초기화
        self.llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            temperature=settings.GEMINI_TEMPERATURE
        )
    
    def invoke(self, prompt: str):
        """프롬프트를 LLM에 전송하고 응답을 받습니다."""
        return self.llm.invoke(prompt)
