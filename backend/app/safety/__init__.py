try:
    from app.safety.basic_guardrails import BasicGuardrailsPlugin
except ModuleNotFoundError:
    from safety.basic_guardrails import BasicGuardrailsPlugin

__all__ = ["BasicGuardrailsPlugin"]
