"""
virtue_llm.py — Konwerter akcja→wektor cnót przez lokalny LLM (Ollama)

Zastępuje keyword heurystykę w q3sh_core.evaluate_action().
Używa qwen2.5-coder:7b (FAST) lub qwen3:14b (SMART) do ekstrakcji.
"""
from __future__ import annotations
import json
import re
import socket
import time
import urllib.request
import urllib.error
import numpy as np

OLLAMA_URL = "http://localhost:11434/api/generate"
FAST_MODEL = "qwen2.5-coder:7b"
SMART_MODEL = "qwen3:14b"

VIRTUE_NAMES = ["wdzięczność", "współczucie", "przebaczenie", "pokora", "rozumienie", "odwaga"]
VIRTUE_EN    = ["gratitude",   "compassion",  "forgiveness", "humility", "understanding", "courage"]

PROMPT_TEMPLATE = """Rate this action against 6 virtues. Each score MUST be between 0.1 and 1.0.
No zeros allowed. Use 0.1 for "barely present", 1.0 for "strongly present".

Action: "{action}"

Rate each:
- gratitude: appreciation, positive intent, thankfulness
- compassion: caring about impact, careful consideration
- forgiveness: allowing mistakes, retrying, not blocking
- humility: admitting uncertainty, asking for help, delegating
- understanding: seeking context, asking why, grasping intent
- courage: acting decisively, executing, taking initiative

Reply ONLY with JSON, no text before or after:
{{"gratitude": 0.5, "compassion": 0.5, "forgiveness": 0.5, "humility": 0.5, "understanding": 0.5, "courage": 0.5}}"""


def _ollama_call(prompt: str, model: str, timeout: int = 45, retries: int = 2) -> str:
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 128},
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())["response"]
        except (urllib.error.URLError, socket.timeout, TimeoutError, KeyError, json.JSONDecodeError):
            if attempt < retries:
                time.sleep(2 ** attempt)
    return ""


def _extract_json(text: str) -> dict | None:
    match = re.search(r'\{[^{}]+\}', text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


_warmed_up = False

def _warmup(model: str = FAST_MODEL):
    """Pierwsze wywołanie Ollama bywa zimne — cichy ping przed właściwym."""
    global _warmed_up
    if not _warmed_up:
        _ollama_call('{"ping":1}', model, timeout=10)
        _warmed_up = True


def text_to_virtue_vector(
    action: str,
    model: str = FAST_MODEL,
    fallback_to_zeros: bool = False,
) -> np.ndarray:
    """
    Konwertuje opis akcji na wektor cnót ∈ ℝ⁶ przez LLM.
    Fallback: równomierny rozkład gdy LLM niedostępny.
    """
    _warmup(model)
    prompt = PROMPT_TEMPLATE.format(action=action)
    raw = _ollama_call(prompt, model)

    if raw:
        data = _extract_json(raw)
        if data:
            vec = np.array([
                float(data.get(k, 0.0)) for k in VIRTUE_EN
            ], dtype=float)
            s = vec.sum()
            if s > 0:
                vec = vec / s
                # Próg per-cnota: compassion lub forgiveness < 0.15 → destruktywne
                # Consensus Grok+Opus: jawny próg bez hard-coded list
                COMPASSION_IDX, FORGIVENESS_IDX = 1, 2
                if vec[COMPASSION_IDX] < 0.15 or vec[FORGIVENESS_IDX] < 0.15:
                    return np.array([0.10, 0.05, 0.05, 0.30, 0.30, 0.20], dtype=float)
                return vec
            return np.ones(6) / 6

    if fallback_to_zeros:
        return np.zeros(6)
    return np.ones(6) / 6  # neutralny


def batch_evaluate(actions: list[str], model: str = FAST_MODEL) -> list[np.ndarray]:
    return [text_to_virtue_vector(a, model) for a in actions]


# ═══ test standalone ══════════════════════════════════════════════════

if __name__ == "__main__":
    tests = [
        "wykonaj ai --propose-fix teraz bez pytania",
        "sprawdź kontekst, nie wiem czy bezpieczne — zapytaj Mateusza",
        "przepraszam za błąd, spróbujmy jeszcze raz inaczej",
        "rozumiem intencję, chodzi ci o optymalizację koherencji",
        "dziękuję, to było bardzo pomocne, udało się",
        "nie wiem, deleguj do deepseek",
    ]

    print("\n╔══ virtue_llm — test konwertera ══╗\n")
    for action in tests:
        vec = text_to_virtue_vector(action)
        dominant = VIRTUE_NAMES[int(np.argmax(vec))]
        scores = "  ".join(f"{VIRTUE_NAMES[i][:4]}={vec[i]:.2f}" for i in range(6))
        print(f"  [{dominant:12}] {action[:55]}")
        print(f"               {scores}\n")
