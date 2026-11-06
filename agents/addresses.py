"""Agent addresses (deterministic from seeds) and package exports.

When the three uAgents run as independent processes with the default seeds,
their Fetch.ai addresses are fixed and known to the orchestrator. This lets
the distributed mode send real uAgents messages to the right agent.

You can also discover an agent's address by running:
    python -c "from agents.research_agent import agent; print(agent.address)"
"""

from __future__ import annotations

from .research_agent import agent as research_agent_instance
from .language_agent import agent as language_agent_instance
from .guidance_agent import agent as guidance_agent_instance


def research_address() -> str:
    return research_agent_instance.address


def language_address() -> str:
    return language_agent_instance.address


def guidance_address() -> str:
    return guidance_agent_instance.address
