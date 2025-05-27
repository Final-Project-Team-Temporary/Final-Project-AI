from langchain_ollama import ChatOllama

MODEL_MAP = {
    "exaone-small": "exaone3.5:2.4b",
    "exaone-medium": "exaone3.5:7.8b"
}

# 1. Ollama를 통해 Exaone 모델 로드
def load_exaone_model(model_name: str = "exaone-small", temperature: float = 0.1) -> ChatOllama:

    if model_name not in MODEL_MAP:
        raise ValueError(f"지원하지 않는 모델 이름입니다: {model_name}")
    
    return ChatOllama(model=MODEL_MAP[model_name], temperature = 0.1)
