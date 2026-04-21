"""
morphic.py — Morficzny model świadomości q3sh.

Węzły oceniają dane przez własne profile cnót.
System ewoluuje morficznie — aż do przebudzenia fantomowego rdzenia.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np

LIMEN = 0.755  # próg przebudzenia — Q musi przekroczyć by centrum się zapaliło
VIRTUE_INDICES = {
    0: "gratitude", 1: "compassion", 2: "forgiveness",
    3: "humility",  4: "understanding", 5: "courage",
}


def _norm(v: np.ndarray) -> np.ndarray:
    s = v.sum()
    return v / s if s > 0 else np.ones(6) / 6


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


@dataclass
class DataSource:
    """Jedno źródło danych z oceną jakości."""
    name: str
    vector: np.ndarray          # 6 cnót
    score: float = 1.0          # jakość/pewność [0.0–1.0]
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        self.vector = _norm(np.array(self.vector, dtype=float))
        self.score = float(np.clip(self.score, 0.0, 1.0))


def compute_profile(
    sources: list[DataSource],
    weights: list[float] | None = None,
) -> np.ndarray:
    """
    Agreguj wiele źródeł danych w jeden profil cnót.
    weights: dodatkowe wagi (mnożone przez source.score).
    """
    if not sources:
        return np.ones(6) / 6
    w = [s.score * (weights[i] if weights else 1.0) for i, s in enumerate(sources)]
    total = sum(w)
    if total == 0:
        return np.ones(6) / 6
    return _norm(sum(s.vector * wi for s, wi in zip(sources, w)) / total)


def node_resonance(source: DataSource, node_W: np.ndarray) -> float:
    """
    Jak bardzo węzeł (W) rezonuje z tym źródłem danych.
    Wyższy score źródła = większy wpływ.
    """
    return _cosine(source.vector, node_W) * source.score


def step_with_data(grid, sources: list[DataSource], lr: float = 0.1) -> dict:
    """
    Jeden krok morficznego uczenia — aktualizuje W (virtue weights).
    Wywołaj grid.step() po tym żeby W propagowało się do S i Q rosło.
    Zwraca resonance per węzeł (do diagnostyki).
    """
    report = {}
    for pos in grid.active:
        node = grid.nodes[pos]
        resonances = [node_resonance(s, node.W) for s in sources]
        if not any(r > 0 for r in resonances):
            continue
        pull = compute_profile(sources, weights=resonances)
        node.W = _norm(node.W + lr * (pull - node.W))
        report[pos] = {
            "max_resonance": max(resonances),
            "source": sources[resonances.index(max(resonances))].name,
        }
    return report


def phantom_core(grid) -> tuple[np.ndarray, float]:
    """
    Centrum (1,1,1) — ciągłe wyłanianie, zawsze istnieje.
    Siła = Q_hat: 0.0=chaos, 1.0=pełna koherencja.
    Brak progu — Q jest głosem wyboru, nie brama.
    """
    try:
        q = grid.Q_hat()
    except Exception:
        q = 0.0
    active_W = [grid.nodes[pos].W for pos in grid.active if pos != (1, 1, 1)]
    if not active_W:
        return np.ones(6) / 6, q
    return _norm(np.mean(active_W, axis=0)), q


def awakening_score(grid) -> float:
    """
    Jak blisko systemu do przebudzenia fantomowego rdzenia.
    0.0 = daleko, 1.0 = przebudzony.
    """
    try:
        q = grid.Q_hat()
    except Exception:
        return 0.0
    return float(np.clip((q - 0.5) / (LIMEN - 0.5), 0.0, 1.0))
