from pydantic import BaseModel, ConfigDict  # ✅ v2로 복귀
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

    model_config = ConfigDict(arbitrary_types_allowed=True)  # ✅ v2 설정


# 2. PydanticOutputParser 정의
output_parser = PydanticOutputParser(pydantic_object=SummaryOutput)

# 3. 체인 로직 정의
def summarize_logic(article: dict) -> dict:
    article_obj = ArticleInput(**article)

    prompt = SUMMARY_PROMPT.format(
        article=article_obj.content,
        format_instructions=output_parser.get_format_instructions()
    )

    response = exaone_llm.invoke(prompt)
    return output_parser.parse(response)

# 4. 체인 등록
summarizer_chain = RunnableLambda(summarize_logic).with_types(
    input_type=ArticleInput,
    output_type=SummaryOutput
)

