from langchain.prompts import PromptTemplate
from models.ollama_models import load_exaone_model
from langchain.output_parsers import PydanticOutputParser
from langchain_core.runnables import Runnable

from pydantic import BaseModel, Field
from typing import List

from prompts.keyword_extraction_prompt import KEYWORD_EXTRACTION_PROMPT

# 1. 파싱을 위한 Pydantic 구조 선언
class Keywords(BaseModel):
    keywords: List[str] = Field(description="list of 기사 내의 중요 키워드")
   
parser = PydanticOutputParser(pydantic_object=Keywords)

# 2. PromptTemplate 정의
prompt = PromptTemplate(
    template=KEYWORD_EXTRACTION_PROMPT,
    input_variables=["title","content"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)

# 3. llm 모델 로드
llm = load_exaone_model("exaone-small")

# 4. keyword 추출 체인 정의
keyword_extraction_chain: Runnable = prompt | llm | parser
