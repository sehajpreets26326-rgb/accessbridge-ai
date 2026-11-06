"""Cheering teammate persona for AccessBridge AI.

The progress messages that the orchestrator posts into the Switch/Mattermost
rooms should sound like a supportive senior teammate — not a robotic status
line. This module generates warm, encouraging, human messages for every
workflow transition, while staying precise about what actually happened.

Design rules (from the user's brief):
- Tone: a cheering teammate who is on your side.
- No excessive emojis (the editorial design forbids it).
- Never overclaim. If something failed or is uncertain, say so plainly.
- Keep messages short — they appear in a chat room, not a report.
- The teammate celebrates completions and is honest about problems.

Usage:
    from backend.app.services.teammate import teammate_message
    msg = teammate_message("research_started", scholarship="AICTE Pragati")
    # "On it — digging into AICTE Pragati now. I'll have the official sources
    #  pulled together shortly."
"""
from __future__ import annotations

from typing import Optional


def teammate_message(
    event: str,
    *,
    scholarship: Optional[str] = None,
    source_count: Optional[int] = None,
    language: Optional[str] = None,
    checklist_count: Optional[int] = None,
    reviewer: Optional[str] = None,
    error: Optional[str] = None,
) -> str:
    """Return a cheering-teammate progress message for a workflow event.

    Every event has a warm fallback. When concrete details are available
    (scholarship name, source count, language) they are woven in so the
    message is informative, not just cheerful.
    """
    name = scholarship or "that scholarship"

    messages = {
        "received": f"Got your question about {name} — let me pull this together for you. Research is starting now.",

        "research_started": f"On it — digging into {name} now. I'll have the official sources pulled together shortly.",

        "research_done": (
            f"Good news — I found {_count(source_count)} official source(s) for {name}. "
            "Now I'm simplifying the language so it's actually readable."
        ),

        "translation_started": (
            f"Simplifying the official wording now"
            + (f" and translating it into {_lang_label(language)}" if language else "")
            + ". I'll keep every deadline and eligibility condition exactly as written — no paraphrasing the important bits."
        ),

        "translation_done": (
            f"Translation done — the explanation is in {_lang_label(language) or 'plain language'} now, "
            "with the original official wording preserved alongside. Building your application checklist next."
        ),

        "guidance_started": "Building your personalised application checklist now. I'll flag anything you still need to provide.",

        "guidance_done": (
            f"Checklist is ready{_count(checklist_count, ' with ', ' items')}. "
            "I've marked what's ready and what's still missing. Handing it to a human coordinator for a final look."
        ),

        "awaiting_review": (
            "I've done my part — a human coordinator is reviewing the sources and the guidance now. "
            "I'll post the final answer here as soon as they approve it."
        ),

        "approved": (
            f"{reviewer or 'The coordinator'} approved the guidance — posting the final answer now. "
            "You've got this!"
        ),

        "rejected": (
            f"{reviewer or 'The coordinator'} asked for corrections before this goes out. "
            "I'll re-check the sources and get it right."
        ),

        "corrections_requested": (
            f"{reviewer or 'The coordinator'} wants a few changes — I'll re-run the research and tighten things up."
        ),

        "delivered": (
            "Your final guidance is here — with source links so you can verify everything. "
            "Go get that scholarship!"
        ),

        "failed": (
            "I hit a snag on this one. "
            + (f"Here's what happened: {error}. " if error else "")
            + "I've logged it — try asking again, or reach out to a coordinator."
        ),
    }
    return messages.get(event, f"Working on {name} — I'll keep you posted.")


def _count(n: Optional[int], prefix: str = " ", suffix: str = "") -> str:
    """Format an optional count naturally."""
    if n is None:
        return ""
    return f"{prefix}{n}{suffix}"


def _lang_label(code: Optional[str]) -> str:
    return {"en": "English", "hi": "Hindi", "pa": "Punjabi"}.get(code or "", "")
