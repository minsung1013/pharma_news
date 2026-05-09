import os
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system: str, user: str, json_mode: bool = True) -> str: ...


class OpenAIProvider(LLMProvider):
    def __init__(self, model: str | None = None):
        self._model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def complete(self, system: str, user: str, json_mode: bool = True) -> str:
        from openai import OpenAI
        client = OpenAI()
        kwargs: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        return client.chat.completions.create(**kwargs).choices[0].message.content


class OllamaProvider(LLMProvider):
    def complete(self, system: str, user: str, json_mode: bool = True) -> str:
        import requests
        payload: dict = {
            "model": os.getenv("OLLAMA_MODEL", "llama3"),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        }
        if json_mode:
            payload["format"] = "json"
        res = requests.post(
            f"{os.getenv('OLLAMA_BASE_URL')}/api/chat",
            json=payload,
            timeout=120,
        )
        res.raise_for_status()
        return res.json()["message"]["content"]


class InternalAPIProvider(LLMProvider):
    def complete(self, system: str, user: str, json_mode: bool = True) -> str:
        import requests
        headers = {"Authorization": f"Bearer {os.getenv('INTERNAL_API_KEY')}"}
        payload = {"system": system, "user": user, "json_mode": json_mode}
        res = requests.post(
            os.getenv("INTERNAL_API_URL"),
            json=payload,
            headers=headers,
            timeout=120,
        )
        res.raise_for_status()
        return res.json()["content"]


def get_provider() -> LLMProvider:
    name = os.getenv("LLM_PROVIDER", "openai").lower()
    if name == "openai":
        return OpenAIProvider()
    if name == "ollama":
        return OllamaProvider()
    if name == "internal":
        return InternalAPIProvider()
    raise ValueError(f"Unknown LLM_PROVIDER: {name!r}. Choose from openai, ollama, internal")


def get_bd_provider() -> LLMProvider:
    """BD 시사점 생성용 고성능 provider. OPENAI_MODEL_BD 환경변수로 모델 지정."""
    name = os.getenv("LLM_PROVIDER", "openai").lower()
    if name == "openai":
        model = os.getenv("OPENAI_MODEL_BD", "gpt-4.1")
        return OpenAIProvider(model=model)
    # OpenAI 외 provider는 단일 모델이므로 기본 provider 그대로 사용
    return get_provider()
