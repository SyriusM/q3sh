"""
q3sh sovereignty — programmatic audit of the project's network surface.

Run: `python -m q3sh.sovereignty audit`

This module is the runtime counterpart of LICENSE §3. It declares — in code —
exactly what endpoints upstream q3sh contacts. Forks that add network calls
MUST extend NETWORK_SURFACE here (and update LICENSE §3) per LICENSE §2.3.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field


@dataclass(frozen=True)
class NetworkEndpoint:
    module: str
    endpoint: str
    direction: str  # "local→local", "local→public", "local→private"
    user_data: str  # what user data is transmitted
    optin_flag: str  # how the user opts in/out
    notes: str = ""


# Upstream q3sh network surface — keep in sync with LICENSE §3
NETWORK_SURFACE: tuple[NetworkEndpoint, ...] = (
    NetworkEndpoint(
        module="q3sh.virtue_llm",
        endpoint="http://localhost:11434/api/generate",
        direction="local→local",
        user_data="prompt text (LLM input)",
        optin_flag="local Ollama only; no external transmission",
    ),
    NetworkEndpoint(
        module="q3sh.guardian",
        endpoint="http://localhost:11434/api/generate",
        direction="local→local",
        user_data="prompt text (LLM input)",
        optin_flag="local Ollama only; no external transmission",
    ),
)

EXTERNAL_ENDPOINTS = tuple(
    e for e in NETWORK_SURFACE if e.direction == "local→public"
)


def audit() -> int:
    print("q3sh — Sovereignty Audit")
    print("=" * 70)
    print(f"Total endpoints: {len(NETWORK_SURFACE)}")
    print(f"External (local→public): {len(EXTERNAL_ENDPOINTS)}")
    print()
    for i, ep in enumerate(NETWORK_SURFACE, 1):
        print(f"[{i}] {ep.module}")
        print(f"    endpoint:   {ep.endpoint}")
        print(f"    direction:  {ep.direction}")
        print(f"    user data:  {ep.user_data}")
        print(f"    opt-in:     {ep.optin_flag}")
        if ep.notes:
            print(f"    notes:      {ep.notes}")
        print()
    if not EXTERNAL_ENDPOINTS:
        print("✓ No external endpoints. Upstream q3sh runs fully offline-capable.")
    else:
        print(f"⚠ {len(EXTERNAL_ENDPOINTS)} external endpoint(s) — see LICENSE §3.")
    print()
    print("See LICENSE §2 (Sovereignty Conditions) and §3 (full audit).")
    return 0


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "audit":
        return audit()
    print("Usage: python -m q3sh.sovereignty audit", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
