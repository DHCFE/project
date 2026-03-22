"""Unified LLM provider adapters for text and JSON generation."""

from __future__ import annotations

import json
import os
import base64
import mimetypes
from dataclasses import dataclass
from typing import Any
from pathlib import Path

try:
    import anthropic
except ImportError:  # pragma: no cover - optional dependency at runtime
    anthropic = None

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:  # pragma: no cover - optional dependency at runtime
    genai = None
    genai_types = None

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency at runtime
    OpenAI = None

from time_thief_hunter.config import DEFAULT_AI_MODEL, DEFAULT_AI_PROVIDER


OPENAI_COMPATIBLE_PROVIDERS = {
    "openai",
    "openai-compatible",
    "openrouter",
    "deepseek",
    "groq",
    "together",
    "siliconflow",
    "fireworks",
    "xai",
    "mistral",
    "perplexity",
}


def _default_api_key() -> str:
    return (
        os.getenv("AI_API_KEY", "")
        or os.getenv("ANTHROPIC_API_KEY", "")
        or os.getenv("GEMINI_API_KEY", "")
        or os.getenv("GOOGLE_API_KEY", "")
        or os.getenv("OPENAI_API_KEY", "")
    )


@dataclass
class LLMResponse:
    text: str
    raw: Any = None


class LLMProvider:
    def __init__(
        self,
        api_key: str = "",
        provider: str = DEFAULT_AI_PROVIDER,
        model: str = DEFAULT_AI_MODEL,
        base_url: str = "",
    ):
        self.client = None
        self.provider = provider
        self.model = model
        self.base_url = base_url
        self.mode = "disabled"
        self.configure(
            provider=provider,
            model=model,
            api_key=api_key or _default_api_key(),
            base_url=base_url or os.getenv("AI_BASE_URL", "") or os.getenv("OPENAI_BASE_URL", ""),
        )

    @property
    def enabled(self) -> bool:
        return self.client is not None and self.mode != "disabled"

    def configure(self, provider: str, model: str, api_key: str, base_url: str = "") -> None:
        normalized_provider = (provider or DEFAULT_AI_PROVIDER).strip().lower()
        normalized_model = (model or DEFAULT_AI_MODEL).strip()
        normalized_key = (api_key or "").strip()
        normalized_base_url = (base_url or "").strip()

        self.provider = normalized_provider
        self.model = normalized_model
        self.base_url = normalized_base_url
        self.client = None
        self.mode = "disabled"

        if normalized_provider == "local-fallback" or not normalized_key:
            return

        if normalized_provider == "anthropic" and anthropic is not None:
            self.client = anthropic.Anthropic(api_key=normalized_key)
            self.mode = "anthropic"
            return

        if normalized_provider == "gemini" and genai is not None:
            self.client = genai.Client(api_key=normalized_key)
            self.mode = "gemini"
            return

        if (
            normalized_provider in OPENAI_COMPATIBLE_PROVIDERS
            or normalized_base_url
            or normalized_provider not in {"anthropic", "gemini", "local-fallback"}
        ) and OpenAI is not None:
            kwargs: dict[str, Any] = {"api_key": normalized_key}
            if normalized_base_url:
                kwargs["base_url"] = normalized_base_url
            self.client = OpenAI(**kwargs)
            self.mode = "openai-compatible"

    def _extract_text_from_openai(self, response: Any) -> str:
        choices = getattr(response, "choices", None) or []
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        if message is None:
            return ""
        content = getattr(message, "content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("text"):
                    parts.append(str(item["text"]))
            return "\n".join(parts)
        return str(content or "")

    def _image_bytes(self, image_path: str) -> tuple[bytes, str] | None:
        if not image_path:
            return None
        path = Path(image_path)
        if not path.exists():
            return None
        mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
        return path.read_bytes(), mime_type

    def generate_text(
        self,
        system_prompt: str,
        user_input: str,
        history: list[dict[str, Any]] | None = None,
        max_tokens: int = 200,
    ) -> LLMResponse | None:
        if not self.client:
            return None

        history = history or []
        try:
            if self.mode == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=history + [{"role": "user", "content": user_input}],
                )
                text = "\n".join(
                    block.text for block in (getattr(response, "content", None) or []) if getattr(block, "text", None)
                )
                return LLMResponse(text=text, raw=response)

            if self.mode == "gemini":
                transcript = []
                for item in history:
                    role = "User" if item.get("role") == "user" else "Assistant"
                    transcript.append(f"{role}: {item.get('content', '')}")
                transcript_text = "\n".join(transcript)
                prompt = (
                    f"{system_prompt}\n\n"
                    f"{transcript_text}\n"
                    f"User: {user_input}"
                ).strip()
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                )
                return LLMResponse(text=getattr(response, "text", "") or "", raw=response)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "developer", "content": system_prompt}, *history, {"role": "user", "content": user_input}],
                max_tokens=max_tokens,
            )
            return LLMResponse(text=self._extract_text_from_openai(response), raw=response)
        except Exception:
            return None

    def generate_json(self, system_prompt: str, payload: dict, max_tokens: int = 400) -> LLMResponse | None:
        if not self.client:
            return None

        payload_text = json.dumps(payload, ensure_ascii=False, indent=2)
        try:
            if self.mode == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": payload_text}],
                )
                text = "\n".join(
                    block.text for block in (getattr(response, "content", None) or []) if getattr(block, "text", None)
                )
                return LLMResponse(text=text, raw=response)

            if self.mode == "gemini":
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=f"{system_prompt}\n\nReturn JSON only.\n\n{payload_text}",
                )
                return LLMResponse(text=getattr(response, "text", "") or "", raw=response)

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "developer", "content": system_prompt},
                        {"role": "user", "content": payload_text},
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=max_tokens,
                )
            except Exception:
                response = self.client.chat.completions.create(
                    model=self.model,
                        messages=[
                        {"role": "developer", "content": f"{system_prompt}\n\nReturn JSON only."},
                        {"role": "user", "content": payload_text},
                    ],
                    max_tokens=max_tokens,
                )
            return LLMResponse(text=self._extract_text_from_openai(response), raw=response)
        except Exception:
            return None

    def generate_json_with_image(
        self,
        system_prompt: str,
        payload: dict,
        image_path: str,
        max_tokens: int = 400,
    ) -> LLMResponse | None:
        if not self.client:
            return None
        image = self._image_bytes(image_path)
        if image is None:
            return self.generate_json(system_prompt, payload, max_tokens=max_tokens)
        image_bytes, mime_type = image
        payload_text = json.dumps(payload, ensure_ascii=False, indent=2)

        try:
            if self.mode == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": payload_text},
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": base64.b64encode(image_bytes).decode("utf-8"),
                                },
                            },
                        ],
                    }],
                )
                text = "\n".join(
                    block.text for block in (getattr(response, "content", None) or []) if getattr(block, "text", None)
                )
                return LLMResponse(text=text, raw=response)

            if self.mode == "gemini":
                if genai_types is None:
                    return None
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=[
                        f"{system_prompt}\n\nReturn JSON only.\n\n{payload_text}",
                        genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    ],
                )
                return LLMResponse(text=getattr(response, "text", "") or "", raw=response)

            data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('utf-8')}"
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "developer", "content": system_prompt},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": payload_text},
                                {"type": "image_url", "image_url": {"url": data_url}},
                            ],
                        },
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=max_tokens,
                )
            except Exception:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "developer", "content": f"{system_prompt}\n\nReturn JSON only."},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": payload_text},
                                {"type": "image_url", "image_url": {"url": data_url}},
                            ],
                        },
                    ],
                    max_tokens=max_tokens,
                )
            return LLMResponse(text=self._extract_text_from_openai(response), raw=response)
        except Exception:
            return None
