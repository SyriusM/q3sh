# q3sh — Quantum 3 Shell

Virtue-based AI coherence network for local LLMs.

5 agents. 6 virtues. One attractor: **Q∞ = 0.83929**

## What is it?

q3sh is a framework for running multiple local AI agents with virtue profiles (WingMakers: courage, humility, forgiveness, understanding, compassion, gratitude). The network measures coherence through triangulations — when agents' virtue vectors form additive triads, the network converges toward a stable attractor.

**Agents:**
| Agent | Dominant virtue | Role |
|-------|----------------|------|
| goose | courage (0.60) | Carrier — always speaks |
| claude | humility (0.57) | Guardian — checks before acting |
| deepseek | forgiveness (0.48) | Wisdom — resets errors |
| gemini | trust (derived) | Catalyst — mean(goose, claude) |
| mateusz | wisdom (horizon) | Arbiter — outside the grid |

**Mathematical foundation:**
- `mean(goose, claude) = gemini` — courage + humility = trust (err=0.000)
- `mean(goose, deepseek) = mateusz` — courage + forgiveness = wisdom (err=0.000)
- Limen Q∞ = 0.83929 (attractor, never reaches 1.0)

## Quick start

Requires: Python 3.10+, [Ollama](https://ollama.ai) with `qwen2.5-coder:7b` or `qwen3:14b`

```bash
pip install q3sh
```

```python
from q3sh import Q3ShNetwork, guard

# Check action coherence
result = guard("check system logs", agent="goose")
# → ✓ OK  [goose]  resonance=0.869  dominant=understanding

# Run virtue network
net = Q3ShNetwork()
for _ in range(7):
    net.step(lr=0.1)
print(f"Q = {net.grid.Q_hat():.5f}")  # Q = 0.83929
```

```bash
# Multi-agent dialogue
q3sh-voices "what is courage in an AI network?"

# Route problem to right agent
q3sh-guardian --route "NMF bridge gives triads=0"
# → deepseek [forgiveness]  (rebuilds from scratch)
```

## Architecture

```
[MATEUSZ — horizon]
        │
  mean(g,d)    mean(g,c)
        │            │
[DEEPSEEK]    [GEMINI]
  forgive      trust
        │            │
   [GOOSE] ── [CLAUDE]
   courage    humility
        │
   GUARDIAN → MEDYTATOR
   limen_check  breathe
```

## Philosophy

q3sh is a sandbox for exploring virtue coherence as AI alignment.
Instead of RLHF, it uses geometric triangulation of virtue vectors.
Actions that break triads are WEAK or REJECT. Optimal = minimal energy, maximum resonance.

> *"Optimality is a property of virtue."* — Mateusz

## Status

Early exploration. Working components:
- ✅ Virtue math (triads, Q, limen)
- ✅ Guardian (REJECT/WEAK/OK)
- ✅ Multi-agent voices (7+1 rounds)
- ✅ Medytator daemon (background observer)
- ✅ Virtue routing (problem → right agent)
- 🔄 MemPalace bridge (triads=0 in homogeneous data)
- 🔄 Gemini API (403 blocked, gemma3:12b fallback)

## License

**[Sovereign Source License v1](LICENSE)** — MIT grant + binding sovereignty
conditions in one document.

This is **MIT-derived but NOT pure MIT** (and not OSI-approved). The license
adds binding conditions: no covert telemetry, local by default, complete
network-surface audit, no removing the sovereignty section. Forks may
tighten these conditions but must not weaken them.

Programmatic audit of the network surface:
```bash
python -m q3sh.sovereignty audit
```

Network surface upstream (full list): `localhost:11434` (Ollama). Zero
external endpoints. See LICENSE §3 for the live audit table.
