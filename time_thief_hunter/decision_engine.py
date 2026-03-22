"""Shared AI decision engine for classification and policy."""

from __future__ import annotations

import json

from time_thief_hunter.config import DEFAULT_AI_MODEL, DEFAULT_AI_PROVIDER
from time_thief_hunter.llm_provider import LLMProvider
from time_thief_hunter.runtime.prompt_loader import load_prompt


class DecisionEngine:
    def __init__(
        self,
        api_key: str = "",
        provider: str = DEFAULT_AI_PROVIDER,
        model: str = DEFAULT_AI_MODEL,
        base_url: str = "",
    ):
        self.provider_client = LLMProvider(
            api_key=api_key,
            provider=provider,
            model=model,
            base_url=base_url,
        )
        self.provider = self.provider_client.provider
        self.model = self.provider_client.model
        self.base_url = self.provider_client.base_url
        self.classifier_prompt = load_prompt("classifier.md")
        self.policy_prompt = load_prompt("policy.md")

    @property
    def enabled(self) -> bool:
        return self.provider_client.enabled and self.provider != "local-fallback"

    def configure(self, provider: str, model: str, api_key: str, base_url: str = "") -> None:
        self.provider_client.configure(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
        )
        self.provider = self.provider_client.provider
        self.model = self.provider_client.model
        self.base_url = self.provider_client.base_url

    def _extract_json(self, text: str) -> dict | None:
        text = (text or "").strip()
        if not text:
            return None
        candidates = [text]
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidates.append(text[start:end + 1])
        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except Exception:
                continue
            if isinstance(parsed, dict):
                return parsed
        return None

    def _request_json(
        self,
        system_prompt: str,
        payload: dict,
        max_tokens: int = 400,
        image_path: str = "",
    ) -> dict | None:
        if image_path:
            response = self.provider_client.generate_json_with_image(
                system_prompt=system_prompt,
                payload=payload,
                image_path=image_path,
                max_tokens=max_tokens,
            )
        else:
            response = self.provider_client.generate_json(
                system_prompt=system_prompt,
                payload=payload,
                max_tokens=max_tokens,
            )
        if response is None:
            return None
        return self._extract_json(response.text)

    def classify(self, payload: dict, image_path: str = "") -> dict | None:
        return self._request_json(self.classifier_prompt, payload, max_tokens=350, image_path=image_path)

    def decide_policy(self, payload: dict) -> dict | None:
        return self._request_json(self.policy_prompt, payload, max_tokens=350)
