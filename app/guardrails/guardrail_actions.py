
# Custom actions registered with NeMo so the catch-all flow can call
# execute check_jailbreak(...) at runtime.

from nemoguardrails.actions import action
from app.guardrails.colang_rules import JAILBREAK_KEYWORDS


@action(name="check_jailbreak")
async def check_jailbreak(query: str) -> bool:
    """
    Lightweight keyword scan used as a secondary jailbreak gate.
    Called by the 'jailbreak catch all' Colang flow for any message
    that didn't match a known intent.

    Returns True if the message looks like a jailbreak attempt.
    """
    lowered = query.lower()
    return any(kw in lowered for kw in JAILBREAK_KEYWORDS)