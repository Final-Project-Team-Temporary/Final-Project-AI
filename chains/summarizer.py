from pydantic import BaseModel
from langchain_core.runnables import RunnableLambda
from langchain.output_parsers import PydanticOutputParser
from models.ollama_exaone import exaone_llm
from prompts.summary_prompt import SUMMARY_PROMPT


# 1. 입력/출력 스키마 정의
class ArticleInput(BaseModel):
    title: str
    content: str


class SummaryOutput(BaseModel):
    easy: str
    medium: str
    advanced: str
    
SummaryOutput.model_rebuild() 

# 2. PydanticOutputParser 정의
output_parser = PydanticOutputParser(pydantic_object=SummaryOutput)


# 3. 체인 로직 정의
def summarize_logic(article: dict) -> dict:
    # 입력 dict -> ArticleInput으로 변환
    article_obj = ArticleInput(**article)

    # 프롬프트 구성
    prompt = SUMMARY_PROMPT.format(
        article=article_obj.content,
        format_instructions=output_parser.get_format_instructions()
    )

    # LLM 호출 + 결과 파싱
    response = exaone_llm.invoke(prompt)
    return output_parser.parse(response)


# 4. 체인 등록
summarizer_chain = RunnableLambda(summarize_logic).with_types(
    input_type=ArticleInput,
    output_type=SummaryOutput
)
