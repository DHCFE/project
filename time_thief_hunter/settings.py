"""用户设置持久化。"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json

from time_thief_hunter.config import (
    DEFAULT_AI_MODEL,
    DEFAULT_AI_PROVIDER,
    SCREENPIPE_URL,
    SETTINGS_FILE,
)


@dataclass
class AppSettings:
    screenpipe_url: str = SCREENPIPE_URL
    ai_provider: str = DEFAULT_AI_PROVIDER
    ai_model: str = DEFAULT_AI_MODEL
    ai_api_key: str = ""
    ai_base_url: str = ""
    use_vendored_screenpipe: bool = True
    auto_start_screenpipe: bool = True
    screenpipe_command: str = "screenpipe"
    onboarding_completed: bool = False

    def to_public_dict(self) -> dict:
        return {
            "ai_provider": self.ai_provider,
            "ai_model": self.ai_model,
            "ai_api_key_present": bool(self.ai_api_key),
            "ai_base_url": self.ai_base_url,
            "onboarding_completed": self.onboarding_completed,
        }


class SettingsStore:
    def __init__(self, path=SETTINGS_FILE):
        self.path = path

    def load(self) -> AppSettings:
        if not self.path.exists():
            return AppSettings()

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if "ai_api_key" not in payload and payload.get("anthropic_api_key"):
                payload["ai_api_key"] = payload["anthropic_api_key"]
            payload.pop("anthropic_api_key", None)
            if "openai_base_url" in payload and "ai_base_url" not in payload:
                payload["ai_base_url"] = payload["openai_base_url"]
            payload.pop("openai_base_url", None)
            return AppSettings(**payload)
        except Exception:
            return AppSettings()

    def save(self, settings: AppSettings) -> AppSettings:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(asdict(settings), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return settings

    def update(self, payload: dict) -> AppSettings:
        current = self.load()
        current.screenpipe_url = (payload.get("screenpipe_url") or current.screenpipe_url).strip()
        if payload.get("ai_provider"):
            current.ai_provider = payload["ai_provider"].strip()
        if payload.get("ai_model"):
            current.ai_model = payload["ai_model"].strip()
        if "ai_base_url" in payload:
            current.ai_base_url = (payload.get("ai_base_url") or "").strip()
        elif "openai_base_url" in payload:
            current.ai_base_url = (payload.get("openai_base_url") or "").strip()
        api_key = payload.get("ai_api_key")
        if api_key is None:
            api_key = payload.get("anthropic_api_key")
        if payload.get("clear_ai_api_key") or payload.get("clear_anthropic_api_key"):
            current.ai_api_key = ""
        elif api_key is not None and str(api_key).strip():
            current.ai_api_key = api_key.strip()
        if "use_vendored_screenpipe" in payload:
            current.use_vendored_screenpipe = bool(payload["use_vendored_screenpipe"])
        if "auto_start_screenpipe" in payload:
            current.auto_start_screenpipe = bool(payload["auto_start_screenpipe"])
        if payload.get("screenpipe_command"):
            current.screenpipe_command = payload["screenpipe_command"].strip()
        if "onboarding_completed" in payload:
            current.onboarding_completed = bool(payload["onboarding_completed"])
        return self.save(current)
