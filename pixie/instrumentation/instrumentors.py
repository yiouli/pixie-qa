"""Auto-discovers and activates OpenInference instrumentors."""

from __future__ import annotations

import importlib
import logging

logger = logging.getLogger("pixie.instrumentation")

_KNOWN_INSTRUMENTORS = [
    ("openinference.instrumentation.openai", "OpenAIInstrumentor"),
    ("openinference.instrumentation.anthropic", "AnthropicInstrumentor"),
    ("openinference.instrumentation.langchain", "LangChainInstrumentor"),
    ("openinference.instrumentation.google_genai", "GoogleGenAIInstrumentor"),
    ("openinference.instrumentation.dspy", "DSPyInstrumentor"),
    # OTel official OpenAI v2 as secondary fallback
    ("opentelemetry.instrumentation.openai_v2", "OpenAIInstrumentor"),
]


def _activate_instrumentors() -> list[str]:
    """Try to instrument all known LLM providers. Returns list of activated names."""
    activated: list[str] = []
    for module_path, class_name in _KNOWN_INSTRUMENTORS:
        try:
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            cls().instrument()
            activated.append(class_name)
            logger.debug("Activated instrumentor: %s from %s", class_name, module_path)
        except ImportError:
            logger.debug(
                "Instrumentor not available (package not installed): %s", module_path
            )
        except Exception:
            logger.debug(
                "Instrumentor failed to activate: %s from %s",
                class_name,
                module_path,
                exc_info=True,
            )
    if not activated:
        logger.warning(
            "No LLM instrumentors activated. Install provider packages "
            "(e.g. openinference-instrumentation-openai) for auto-capture."
        )
    return activated
