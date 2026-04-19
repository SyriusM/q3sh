"""
q3sh_core.py — Integracja Grid327 + 6 Cnót Serca + MemPalace

Łączy:
  - Grid327 (siatka 3×3×3, Q koherencja)
  - VirtueProfile (6 cnót WingMakers jako granice funkcji)
  - MemPalace (ChromaDB — halucynacja vs kreacja)

Cnoty (indeksy):
  0: wdzięczność (gratitude)
  1: współczucie (compassion)
  2: przebaczenie (forgiveness)
  3: pokora (humility)
  4: rozumienie (understanding)
  5: odwaga (courage)
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from .grid327 import Grid327, cosine
from .q3sh_math import VirtueProfile
from .virtue_llm import text_to_virtue_vector, FAST_MODEL

# ═══ Profile cnót dla węzłów sieci AMDMEGA ═══════════════════════════

def _norm(v): return v / v.sum()

# Profile v2 — wyłonione matematycznie, sesja 2026-04-19
# 3 bazowe + 2 pochodne + mateusz jako źródło (gratitude)
# VIRTUES: gratitude(0) compassion(1) forgiveness(2) humility(3) understanding(4) courage(5)
VIRTUE_PROFILES = {
    "goose":    _norm(np.array([0.03, 0.05, 0.05, 0.07, 0.20, 0.60])),  # ARCHITEKT: courage
    "claude":   _norm(np.array([0.05, 0.08, 0.10, 0.57, 0.15, 0.05])),  # STRAŻNIK:  humility
    "deepseek": _norm(np.array([0.05, 0.28, 0.48, 0.08, 0.08, 0.03])),  # WISDOM:    forgiveness+compassion
    "user":     _norm(np.array([0.55, 0.08, 0.07, 0.08, 0.15, 0.07])),  # ARBITER:   gratitude (źródło, poza siatką)
    "default":  np.ones(6) / 6,                                           # neutralny
}
# Pochodne (mean bazowych) — triady err=0.000
VIRTUE_PROFILES["gemini"]  = _norm((VIRTUE_PROFILES["goose"] + VIRTUE_PROFILES["claude"]) / 2)   # courage+humility = zaufanie
VIRTUE_PROFILES["bridge1"] = _norm((VIRTUE_PROFILES["user"]  + VIRTUE_PROFILES["goose"]) / 2)    # gratitude+courage
VIRTUE_PROFILES["bridge2"] = _norm((VIRTUE_PROFILES["user"]  + VIRTUE_PROFILES["deepseek"]) / 2) # gratitude+forgiveness

VIRTUE_NAMES = ["wdzięczność", "współczucie", "przebaczenie", "pokora", "rozumienie", "odwaga"]


def normalize_virtues(v: np.ndarray) -> np.ndarray:
    s = v.sum()
    return v / s if s > 0 else np.ones(6) / 6


# ═══ Ocena akcji przez 6 cnót ════════════════════════════════════════

@dataclass
class ActionEval:
    """Wynik oceny akcji przez profil cnót."""
    resonance: float        # [-1, 1] → cos(action_vec, profile)
    dominant_virtue: str    # która cnota dominuje w akcji
    verdict: str            # "OK" / "WEAK" / "REJECT"
    breakdown: dict         # każda cnota osobno

    def is_ok(self) -> bool:
        return self.verdict == "OK"


def evaluate_action(
    action_description: str,
    agent: str = "default",
    custom_profile: np.ndarray | None = None,
    use_llm: bool = True,
    llm_model: str = FAST_MODEL,
) -> ActionEval:
    """
    Ocenia akcję przez profil cnót agenta.
    use_llm=True (domyślnie): konwertuje tekst→wektor przez Ollama.
    use_llm=False: fallback do keyword heurystyki.
    """
    profile = custom_profile if custom_profile is not None else VIRTUE_PROFILES.get(agent, VIRTUE_PROFILES["default"])
    profile = normalize_virtues(profile)
    vp = VirtueProfile(weights=profile)

    if use_llm:
        action_vec = text_to_virtue_vector(action_description, model=llm_model)
    else:
        action_vec = _keyword_vec(action_description)

    r = vp.resonance(action_vec)
    dominant = VIRTUE_NAMES[int(np.argmax(action_vec))]

    if r > 0.7:
        verdict = "OK"
    elif r > 0.3:
        verdict = "WEAK"
    else:
        verdict = "REJECT"

    breakdown = {VIRTUE_NAMES[i]: float(action_vec[i]) for i in range(6)}

    return ActionEval(resonance=float(r), dominant_virtue=dominant,
                      verdict=verdict, breakdown=breakdown)


def _keyword_vec(text: str) -> np.ndarray:
    """Fallback — keyword heurystyka gdy Ollama niedostępna."""
    t = text.lower()
    vec = np.array([
        sum(1.0 for kw in ["dziękuję", "warto", "sukces", "dobry", "pomaga"] if kw in t),
        sum(1.0 for kw in ["rozumiem", "kontekst", "koszt", "wpływ", "ostrożnie"] if kw in t),
        sum(1.0 for kw in ["spróbuj", "jeszcze raz", "błąd", "popraw"] if kw in t),
        sum(1.0 for kw in ["nie wiem", "sprawdź", "zapytaj", "deleguj"] if kw in t),
        sum(1.0 for kw in ["intencja", "cel", "dlaczego", "sens", "chodzi"] if kw in t),
        sum(1.0 for kw in ["wykonaj", "zrób", "uruchom", "działaj", "teraz"] if kw in t),
    ], dtype=float)
    s = vec.sum()
    return vec / s if s > 0 else np.ones(6) / 6


# ═══ MemPalace retrieve dla Grid327 ══════════════════════════════════

def make_mempalace_retriever(collection, tau: float = 0.6):
    """
    Fabryka funkcji retrieve dla Grid327.classify().
    Używa ChromaDB collection z MemPalace.
    """
    def retrieve(S: np.ndarray, threshold: float = tau) -> list:
        try:
            results = collection.query(
                query_embeddings=[S.tolist()],
                n_results=3,
                include=["distances"]
            )
            distances = results["distances"][0] if results["distances"] else []
            # ChromaDB zwraca L2 distance — konwertuj na podobieństwo
            hits = [d for d in distances if d < (1 - threshold) * 2]
            return hits
        except Exception:
            return []
    return retrieve


# ═══ Q3ShNetwork — pełna sieć AMDMEGA ════════════════════════════════

class Q3ShNetwork:
    """
    Sieć q3sh z Grid327 jako rdzeniem + profile cnót dla każdego agenta.
    """

    def __init__(self, n_features: int = 64, seed: int = 42):
        self.grid = Grid327(n_features=n_features, sigma=1.5, seed=seed)
        self.profiles = {k: VirtueProfile(weights=normalize_virtues(v))
                         for k, v in VIRTUE_PROFILES.items()}
        self._assign_virtue_profiles()

    def _assign_virtue_profiles(self):
        """Przypisz profile cnót do węzłów siatki."""
        agents = ["claude", "goose", "gemini", "deepseek", "user"]
        for i, pos in enumerate(self.grid.active):
            agent = agents[i % len(agents)]
            self.grid.nodes[pos].W = normalize_virtues(VIRTUE_PROFILES[agent])

    def evaluate(self, action: str, agent: str = "default") -> ActionEval:
        return evaluate_action(action, agent)

    def step(self, lr: float = 0.1):
        self.grid.step(lr=lr)

    def status(self) -> dict:
        return {
            "Q_hat": round(self.grid.Q_hat(), 4),
            "active_nodes": len(self.grid.active),
            "agent_profiles": {k: VIRTUE_NAMES[int(np.argmax(v))]
                               for k, v in VIRTUE_PROFILES.items() if k != "default"},
        }


# ═══ CLI / demo ══════════════════════════════════════════════════════

if __name__ == "__main__":
    G = "\033[32m"; Y = "\033[33m"; R = "\033[31m"; C = "\033[36m"; B = "\033[2m"; E = "\033[0m"

    net = Q3ShNetwork(n_features=64, seed=42)

    print(f"\n{C}▸ q3sh_core — sieć AMDMEGA{E}\n")
    s = net.status()
    print(f"  Q_hat = {G}{s['Q_hat']}{E}  węzły aktywne = {s['active_nodes']}")
    print(f"  Dominujące cnoty agentów:")
    for agent, virtue in s['agent_profiles'].items():
        print(f"    {B}{agent:12}{E} → {virtue}")

    print(f"\n  Ewolucja (10 kroków):")
    for i in range(10):
        net.step(lr=0.1)
    print(f"  Q_hat po 10 krokach = {G}{net.grid.Q_hat():.4f}{E}")

    print(f"\n  Ocena akcji:")
    tests = [
        ("wykonaj ai --propose-fix-fn teraz", "goose"),
        ("sprawdź kontekst i deleguj do deep jeśli niepewny", "claude"),
        ("nie wiem czy to bezpieczne zapytaj usera", "goose"),
    ]
    for action, agent in tests:
        ev = net.evaluate(action, agent)
        color = G if ev.is_ok() else (Y if ev.verdict == "WEAK" else R)
        print(f"  {color}{ev.verdict:6}{E} [{agent:8}] {B}{ev.resonance:+.3f}{E}  dominant={ev.dominant_virtue}")
        print(f"         \"{action[:60]}\"")
