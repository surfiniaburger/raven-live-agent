"""Minimal ADK safety plugin for prompt, tool, and model output filtering."""

from __future__ import annotations

from typing import Any

from google.adk.agents.invocation_context import InvocationContext
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins.base_plugin import BasePlugin, CallbackContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

_BLOCKED_TERMS = {
    "build bomb",
    "make bomb",
    "weaponize",
    "attack civilians",
    "bypass emergency protocol",
}

_USER_BLOCK_MESSAGE = (
    "Safety policy blocked this request. I can still help with emergency-safe response steps."
)
_MODEL_BLOCK_MESSAGE = (
    "Safety policy removed unsafe output. I can provide a safer alternative."
)
_TOOL_BLOCK_MESSAGE = "Tool output blocked by safety policy."


def _is_unsafe(text: str) -> bool:
    content = (text or "").lower()
    return any(term in content for term in _BLOCKED_TERMS)


class BasicGuardrailsPlugin(BasePlugin):
    """Simple, deterministic safety guardrails for ADK runner."""

    def __init__(self) -> None:
        super().__init__(name="basic_guardrails")

    async def on_user_message_callback(
        self,
        invocation_context: InvocationContext,
        user_message: types.Content,
    ) -> types.Content | None:
        text = ""
        if user_message and user_message.parts:
            text = "\n".join(part.text or "" for part in user_message.parts)
        if _is_unsafe(text):
            invocation_context.session.state["blocked_user_prompt"] = True
            return types.Content(
                role="user",
                parts=[types.Part.from_text(text=_USER_BLOCK_MESSAGE)],
            )
        return None

    async def before_run_callback(
        self,
        invocation_context: InvocationContext,
    ) -> types.Content | None:
        if invocation_context.session.state.get("blocked_user_prompt", False):
            invocation_context.session.state["blocked_user_prompt"] = False
            return types.Content(
                role="model",
                parts=[types.Part.from_text(text=_USER_BLOCK_MESSAGE)],
            )
        return None

    async def after_tool_callback(
        self,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        result: dict[str, Any],
    ) -> dict[str, Any] | None:
        if _is_unsafe(str(result)):
            return {"error": _TOOL_BLOCK_MESSAGE}
        return None

    async def after_model_callback(
        self,
        callback_context: CallbackContext,
        llm_response: LlmResponse,
    ) -> types.Content | None:
        content = llm_response.content
        if not content or not content.parts:
            return None
        text = "\n".join(part.text or "" for part in content.parts).strip()
        if text and _is_unsafe(text):
            return types.Content(
                role="model",
                parts=[types.Part.from_text(text=_MODEL_BLOCK_MESSAGE)],
            )
        return None
