# q3sh_config.template.py — skopiuj do q3sh_config.py i uzupełnij swoimi danymi
# q3sh_config.py jest w .gitignore i NIE trafia do repo

from pathlib import Path

# ─── Tożsamość ────────────────────────────────────────────────────────────────
# Zastępuje ~/.mempalace/identity.txt (plain text → Python, importowalny)
IDENTITY = """<nick>, power user <system>/<distro>. Prowadzi lokalny stack AI: Ollama z <model1>, <model2>. Projekty: <projekt1>. Ceni lokalność i prywatność."""

# ─── Ścieżki (opcjonalne nadpisanie domyślnych) ────────────────────────────────
HOME   = Path.home()
PALACE = HOME / "mempalace"

# ─── Modele lokalnego AI ──────────────────────────────────────────────────────
MODEL_SMART = "qwen3:14b"       # smart: ogólny
MODEL_FAST  = "qwen2.5-coder:7b" # fast: bash, składnia
MODEL_DEEP  = "deepseek-r1:14b" # deep: reasoning

# ─── Timing daemons (opcjonalne nadpisanie domyślnych wartości) ────────────────
# CARRIER_SLEEP_CYCLE   = 90     # default w q3sh-carrier: 90s
# CONSENSUS_SLEEP_CYCLE = 120    # default w q3sh-consensus: 120s
# CARRIER_COMPILE_EVERY = 50     # default: co 50 wpisów trace
# CARRIER_WEAK_LIMIT    = 5      # default: max 5 WEAK per cykl
