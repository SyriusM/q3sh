"""
grid327.py — Model 327: siatka 3×3×3, 7/27 aktywnych, Q jako koherencja.

Rdzeń q3sh z:
  - ℝⁿ stany węzłów
  - Manhattan distance + exponential kernel
  - 6-wymiarowy profil cnót (WingMakers)
  - Halucynacja vs kreacja = ten sam mechanizm, inne zakotwiczenie w MemPalace
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from itertools import product
from typing import Callable, Optional

# ═══ Topologia ═══════════════════════════════════════════════════════

GRID = [(x,y,z) for x,y,z in product(range(3), repeat=3)]   # 27 węzłów

ACTIVE_SET = [                      # 7 aktywnych (centrum + 6 osi)
    (1,1,1),
    (0,1,1), (2,1,1),
    (1,0,1), (1,2,1),
    (1,1,0), (1,1,2),
]

# Przeciwległe pary pozycji (brak bezpośredniego sprzężenia w sieci)
POSITION_OPPOSITES: dict[tuple, tuple] = {
    (0,1,1): (2,1,1), (2,1,1): (0,1,1),   # explore ↔ carrier
    (1,0,1): (1,2,1), (1,2,1): (1,0,1),   # wdz ↔ przeb
    (1,1,0): (1,1,2), (1,1,2): (1,1,0),   # medyt ↔ rozum
}

def manhattan(u, v):
    return sum(abs(a-b) for a,b in zip(u,v))

def kernel(d, sigma=1.5):
    return float(np.exp(-d/sigma))

def cosine(a, b):
    n = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a,b)/n) if n > 0 else 0.0

# ═══ Węzeł ═══════════════════════════════════════════════════════════

@dataclass
class Node:
    pos: tuple                          # (x,y,z)
    S: np.ndarray                       # stan ∈ ℝⁿ
    W: np.ndarray = field(              # profil cnót ∈ ℝ⁶
        default_factory=lambda: np.ones(6)/np.sqrt(6))
    active: bool = False

# ═══ Siatka ══════════════════════════════════════════════════════════

class Grid327:
    def __init__(self, n_features=384, sigma=1.5, radius=3,
                 alpha=0.5, beta=0.2, gamma=0.3, seed=None):
        rng = np.random.default_rng(seed)
        self.sigma, self.r = sigma, radius
        self.alpha, self.beta, self.gamma = alpha, beta, gamma
        self.nodes = {
            p: Node(pos=p, S=rng.standard_normal(n_features),
                    active=(p in ACTIVE_SET))
            for p in GRID
        }
        self.active = [p for p in ACTIVE_SET]

    # ── Koherencja ──
    def Q_local(self, v):
        Sv = self.nodes[v].S
        neigh = [u for u in self.active if u != v
                 and manhattan(u,v) <= self.r]
        if not neigh: return 0.0
        weights = np.array([kernel(manhattan(u,v), self.sigma) for u in neigh])
        cosines = np.array([cosine(Sv, self.nodes[u].S) for u in neigh])
        return float((weights * cosines).sum() / weights.sum())

    def Q_global(self):
        return np.mean([self.Q_local(v) for v in self.active])

    def Q_hat(self):
        return (self.Q_global() + 1) / 2          # ∈ [0,1]

    # ── Rezonans ──
    def resonance(self, u, v):
        n_u, n_v = self.nodes[u], self.nodes[v]
        sem  = cosine(n_u.S, n_v.S)
        topo = kernel(manhattan(u,v), self.sigma)
        eth  = cosine(n_u.W, n_v.W)
        return self.alpha*sem + self.beta*topo + self.gamma*eth

    # ── Propagacja (self-improving step) ──
    def step(self, lr=0.1):
        """Każdy węzeł przyciąga się do geometric neighbors (nie przeciwległych).

        Topologia: centrum widzi wszystkich. Face-centers widzą centrum
        + 4 sąsiednich face-centers, ale NIE swój przeciwnik (POSITION_OPPOSITES).
        Tworzy nietrywialny atraktor — przeciwne kubity pozostają zróżnicowane.
        """
        updates = {}
        for v in self.active:
            opp = POSITION_OPPOSITES.get(v)
            neigh = [u for u in self.active
                     if u != v and u != opp]   # wyklucz siebie i przeciwnika
            if not neigh: continue
            w = np.array([self.resonance(u,v) for u in neigh])
            w = np.clip(w, 0, None)
            if w.sum() == 0: continue
            target = sum(w_i*self.nodes[u].S for w_i,u in zip(w,neigh)) / w.sum()
            updates[v] = (1-lr)*self.nodes[v].S + lr*target
        for v, S_new in updates.items():
            self.nodes[v].S = S_new

    # ── Halucynacja vs kreacja ──
    def classify(self, v, mempalace_retrieve: Callable,
                 tau=0.6, theta=0.6):
        """
        retrieve(S_v) = lista wspomnień z cos > tau
        H/K dzieli się tylko po tym, czy retrieval jest niepusty.
        """
        hits = mempalace_retrieve(self.nodes[v].S, tau)
        q    = self.Q_local(v)
        q_hat = (q+1)/2
        if q_hat < theta:
            return "noise"
        return "creation" if hits else "hallucination"
