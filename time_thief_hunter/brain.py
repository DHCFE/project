"""AI negotiation brain."""

from __future__ import annotations

from time_thief_hunter.config import (
    ALLOW_LOCAL_NEGOTIATION_FALLBACK,
    DEFAULT_AI_MODEL,
    DEFAULT_AI_PROVIDER,
)
from time_thief_hunter.llm_provider import LLMProvider
from time_thief_hunter.runtime.prompt_loader import load_prompt


class AgentBrain:
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
        self.history: list[dict[str, str]] = []
        self.system_prompt = ""
        self.base_prompt = load_prompt("negotiator.md")
        self.negotiation_context = {}
        self.using_local_fallback = not self.provider_client.enabled
        self.provider = self.provider_client.provider
        self.model = self.provider_client.model
        self.base_url = self.provider_client.base_url

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
        self.using_local_fallback = not self.provider_client.enabled

    def start_negotiation(self, context):
        """Start a new negotiation round."""
        self.history = []
        self.negotiation_context = dict(context)
        app = context.get("app", "Unknown app")
        duration = context.get("duration", "?")
        app_profile = context.get("app_profile", {})
        memory_snapshot = context.get("memory_snapshot", {})
        active_plan = context.get("active_plan", {})
        warnings = app_profile.get("warnings", 0)
        detections = app_profile.get("detections", 0)
        focus_score = memory_snapshot.get("focus_score", "?")
        plan_title = active_plan.get("title", "Intervention Contract")
        required_commitment = active_plan.get("required_commitment", "The user must give a concrete commitment.")
        context_summary = active_plan.get("context_summary", "No extra context available.")
        contract_terms = active_plan.get("contract_terms", [])
        contract_lines = "\n".join(f"- {term}" for term in contract_terms) or "- None"

        self.system_prompt = f"""{self.base_prompt}

You are "Time Thief Hunter", a strict but negotiable productivity enforcer.

Current situation:
- App detected: {app}
- Approximate slacking duration: {duration} minutes
- Historical detections: {detections}
- Historical warnings: {warnings}
- Current focus score: {focus_score}
- Current plan title: {plan_title}
- Current task context: {context_summary}
- Required commitment: {required_commitment}
- Contract terms:
{contract_lines}

Personality:
- Sharp, sarcastic, but ultimately trying to help the user work
- Persuadable, but not easy to soften
- If the user offers a specific trade, such as "Give me 5 more minutes and I will finish the PR", you may consider it
- Keep replies short and forceful, 2-3 sentences
- Reply in English

Rules:
- Never allow more than 15 extra minutes
- The user must offer a concrete trade
- The trade must be verifiable, not vague
- Repeat offences should make you stricter
- A bad attitude should make you stricter"""

    def _local_fallback_reply(self, user_message):
        active_plan = self.negotiation_context.get("active_plan", {})
        app = self.negotiation_context.get("app", "this app")
        required_commitment = active_plan.get("required_commitment", "Give me one concrete commitment.")
        user_text = user_message.strip()
        normalized = user_text.lower()
        delay_tokens = ("more", "minute", "minutes", "5", "10", "15")
        work_tokens = (
            "write",
            "finish",
            "submit",
            "ship",
            "fix",
            "commit",
            "review",
            "code",
            "push",
            "deliver",
            "complete",
        )

        if any(token in normalized for token in delay_tokens) and any(
            token in normalized for token in work_tokens
        ):
            return (
                f"Fine. You get one short buffer, nothing more. "
                f"State the full trade clearly: what you will finish, when it will be done, and stop treating {app} as your main job."
            )

        if len(user_text) < 8 or not any(token in normalized for token in work_tokens):
            return f"That is too vague. Give me a verifiable commitment now: {required_commitment}"

        return (
            "Barely acceptable. I will hold you to that exact condition, and if you miss it, "
            "next time I will be much less flexible."
        )

    def negotiate(self, user_message):
        """Send one negotiation message and return the AI reply."""
        self.history.append({"role": "user", "content": user_message})

        try:
            response = self.provider_client.generate_text(
                system_prompt=self.system_prompt,
                user_input=user_message,
                history=self.history[:-1],
                max_tokens=200,
            )
            if response is None:
                if ALLOW_LOCAL_NEGOTIATION_FALLBACK:
                    reply = self._local_fallback_reply(user_message)
                else:
                    reply = "(AI API key is not configured, negotiation is unavailable.)"
            else:
                reply = response.text or "(The model returned no usable reply.)"
        except Exception as e:
            if ALLOW_LOCAL_NEGOTIATION_FALLBACK:
                reply = self._local_fallback_reply(user_message)
            else:
                reply = f"(The AI is temporarily unavailable: {e})"

        self.history.append({"role": "assistant", "content": reply})
        return reply

    def reset(self):
        self.history = []
        self.system_prompt = ""
        self.negotiation_context = {}
