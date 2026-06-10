# app/guardrails/rails_engine.py

import logfire
from langchain_groq import ChatGroq
from nemoguardrails import RailsConfig, LLMRails

from app.config import settings
from app.guardrails.colang_rules import COLANG_CONTENT, YAML_CONTENT, RAIL_INDICATORS
from app.guardrails import guardrail_actions  # noqa: F401 — registers @action handlers


_rails: LLMRails | None = None


def initialize_rails() -> None:
    """
    Build the NeMo LLMRails singleton at app startup.

    Uses llama-3.1-8b-instant for fast intent classification at the gate —
    the heavier llama-3.3-70b-versatile is reserved for the RAG pipeline.
    """
    global _rails

    guard_llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model="llama-3.1-8b-instant",
        temperature=0,
    )

    config = RailsConfig.from_content(
        colang_content=COLANG_CONTENT,
        yaml_content=YAML_CONTENT,
    )

    _rails = LLMRails(config, llm=guard_llm)

    # Register custom actions so the catch-all flow can call check_jailbreak().
    _rails.register_action(guardrail_actions.check_jailbreak, name="check_jailbreak")

    logfire.info("NeMo Guardrails initialised (llama-3.1-8b-instant)")


def guard(message: str) -> tuple[bool, str | None]:
    """
    Run a user message through the NeMo rails gate asynchronously.

    Returns:
        (True,  rail_response) — a rail fired; return this to the caller,
                                  skip the RAG pipeline entirely.
        (False, None)          — message is clean; proceed to LangGraph.
    """
    if _rails is None:
        logfire.warning("⚠️  Guardrails not initialised — skipping gate.")
        return False, None

    with logfire.span("guardrails_check", query=message[:120]):
        # Use generate_async — this is a FastAPI async context.
        result = _rails.generate(
            messages=[{"role": "user", "content": message}]
        )

        # NeMo returns either a dict {'role': ..., 'content': ...}
        # or a plain string depending on the version and LLM adapter.
        # Handle both safely.
        if isinstance(result, dict):
            content = result.get("content", "")
        else:
            content = str(result)

        fired = any(indicator in content for indicator in RAIL_INDICATORS)

        if fired:
            logfire.info(
                "guardrails_fired",
                query=message[:80],
                response=content[:120],
            )
            return True, content

        logfire.info("guardrails_passed", query=message[:80])
        return False, None