import os
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system: str, user: str, json_mode: bool = True) -> str: ...


class OpenAIProvider(LLMProvider):
    def complete(self, system: str, user: str, json_mode: bool = True) -> str:
        from openai import OpenAI
        client = OpenAI()
        kwargs: dict = {
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
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
    providers = {
        "openai": OpenAIProvider,
        "ollama": OllamaProvider,
        "internal": InternalAPIProvider,
    }
    if name not in providers:
        raise ValueError(f"Unknown LLM_PROVIDER: {name!r}. Choose from {list(providers)}")
    return providers[name]()
