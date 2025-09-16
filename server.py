from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from chains.summarizer import summarizer_chain, ArticleInput, SummaryOutput

app = FastAPI()

@app.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/docs")

@app.post("/summarize", response_model=SummaryOutput)
async def summarize(article: ArticleInput):
    # summarizer_chain.invoke는 동기 함수이므로 await 없이 사용
    return summarizer_chain.invoke(article.model_dump())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
