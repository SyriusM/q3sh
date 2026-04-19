"""
q3sh_math.py — Matematyczny rdzeń Quantum Shell (q3sh)
========================================================

Formalizacja Hierarchii 10 Kostek + Triangulacji + Fractal Propagation
w spójną algebrę, którą można bezpośrednio implementować i testować.

MAPOWANIE KONCEPTÓW:

    Koncept z q3sh                  Obiekt matematyczny
    ------------------------        -------------------------------------
    8 kostek przestrzeni pod-       V = {0,...,7}; κ: V → {0,1}³
      wymiarowej                    (octal encoding)
    Wektor stanu kostki             S_k ∈ ℝⁿ  (n = cechy: amp, freq, ...)
    Sąsiedztwo                      d_H(i,j) = odl. Hamminga między κ(i), κ(j)
    Koherencja                      C ∈ ℝ^{8×8}, C[i,j] = cos(S_i,S_j)·w(d_H)
    Pozycja 9 (Centrum)             Ω₉: agregator (Ŝ, C̄, Q)
    Pozycja 10 (Mapa)               Π₁₀: rzut na gwiazdkę (8 kątów po π/4)
    Triangulacja c = a+b            T: {(i,j,k) | f(S_i, S_j) ≈ S_k}
    Microcollapse                   μ(i,j) ⟺ |C[i,j]| < θ_micro
    Macrocollapse                   M ⟺ Q < θ_macro
    Fractal Imprint                 F: propagator z triad na sąsiednie triady
    Splątanie (entanglement)        rank macierzy Gramma G_ij = ⟨S_i, S_j⟩
    6 cnót WingMakers               W ∈ ℝ⁶; rezonans(a) = cos(V(a), W)

KLUCZOWA IDENTYCZNOŚĆ 8+1=Q
---------------------------
8 kostek + 1 centrum = stan Q (koherencja całego systemu)
Q ∈ [0,1]; gdy Q → 1 system jest "splątany" (konsensus);
gdy Q → 0 system jest "klasyczny" (niezależny szum).
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import Callable, Optional
from itertools import combinations, product


# ════════════════════════════════════════════════════════════════════
# 1. PRZESTRZEŃ STANÓW — Octal Encoding
# ════════════════════════════════════════════════════════════════════

def octal_to_coords(k: int) -> np.ndarray:
    """
    κ: V → {0,1}³
    Wierzchołek k ∈ {0,...,7} → binarne współrzędne (x,y,z).
    
    Przykład: κ(3) = (0,1,1), κ(7) = (1,1,1)
    """
    assert 0 <= k <= 7, f"k musi być w [0,7], otrzymano {k}"
    return np.array([(k >> 2) & 1, (k >> 1) & 1, k & 1], dtype=int)


def coords_to_octal(coords: np.ndarray) -> int:
    """κ⁻¹: {0,1}³ → V"""
    x, y, z = coords
    return int(4*x + 2*y + z)


def hamming_distance(i: int, j: int) -> int:
    """
    d_H(i,j) — odległość Hamminga (liczba różniących się bitów).
    
    d_H = 0 → ten sam wierzchołek
    d_H = 1 → sąsiad przez krawędź     (12 par)
    d_H = 2 → sąsiad przez ścianę      (12 par)
    d_H = 3 → przekątna przestrzenna   (4 pary)
    """
    return bin(i ^ j).count('1')


def neighborhood_weight(d_h: int) -> float:
    """
    w(d_H) — waga topologiczna, maleje wraz z odległością.
    Interpretacja: bliżsi sąsiedzi mają większy wpływ na koherencję.
    """
    return {0: 1.0, 1: 1.0, 2: 0.5, 3: 0.25}[d_h]


# ════════════════════════════════════════════════════════════════════
# 2. WEKTORY STANU KOSTEK
# ════════════════════════════════════════════════════════════════════

@dataclass
class CubeState:
    """
    Stan pojedynczej kostki S_k ∈ ℝⁿ.
    
    Kanoniczne cechy:
      [0] value     — skalarna wartość węzła
      [1] frequency — częstotliwość (w hipotetycznej propagacji falowej)
      [2] amplitude — amplituda
      [3] phase     — faza [0, 2π)
      [4] coherence — lokalny stopień spójności ∈ [0,1]
    
    + opcjonalnie embedding semantyczny (z sentence-transformers).
    """
    k: int                          # identyfikator w V = {0,...,7}
    features: np.ndarray            # wektor S_k ∈ ℝⁿ
    embedding: Optional[np.ndarray] = None  # semantyczna reprezentacja

    def __post_init__(self):
        self.coords = octal_to_coords(self.k)
        self.octal_str = f"{self.k:03o}"[-3:]  # '000'...'111'

    def vector(self) -> np.ndarray:
        """Zwróć wektor do obliczeń koherencji."""
        if self.embedding is not None:
            return np.concatenate([self.features, self.embedding])
        return self.features


# ════════════════════════════════════════════════════════════════════
# 3. OPERATOR KOHERENCJI  C ∈ ℝ^{8×8}
# ════════════════════════════════════════════════════════════════════

def cosine(u: np.ndarray, v: np.ndarray) -> float:
    """cos(u,v) ∈ [-1, 1]"""
    n = np.linalg.norm(u) * np.linalg.norm(v)
    return float(np.dot(u, v) / n) if n > 0 else 0.0


def coherence_matrix(cubes: list[CubeState]) -> np.ndarray:
    """
    C[i,j] = cos(S_i, S_j) · w(d_H(i,j))
    
    Macierz symetryczna 8×8. Przekątna = 1.0.
    """
    assert len(cubes) == 8, "q3sh rdzeń wymaga dokładnie 8 kostek"
    C = np.zeros((8, 8))
    for i, ci in enumerate(cubes):
        for j, cj in enumerate(cubes):
            d_h = hamming_distance(ci.k, cj.k)
            if i == j:
                C[i, j] = 1.0
            else:
                C[i, j] = cosine(ci.vector(), cj.vector()) * neighborhood_weight(d_h)
    return C


# ════════════════════════════════════════════════════════════════════
# 4. POZYCJA 9 — OPERATOR CENTRUM Ω₉
# ════════════════════════════════════════════════════════════════════

@dataclass
class Center9:
    """
    Pozycja 9 — wirtualne centrum.
    Nie istnieje jako osobny stan; jest funkcją 8 kostek.
    """
    mean_state: np.ndarray       # Ŝ = (1/8) Σ S_k
    coherence: np.ndarray        # C (macierz 8×8)
    Q: float                     # Q ∈ [0,1], globalna spójność

    @classmethod
    def from_cubes(cls, cubes: list[CubeState]) -> "Center9":
        vectors = np.stack([c.vector() for c in cubes])
        mean_state = vectors.mean(axis=0)
        C = coherence_matrix(cubes)
        # Q jako średnia koherencja poza diagonalą (bez trywialnego 1.0)
        off_diag = C[np.triu_indices(8, k=1)]
        Q = float(np.clip((off_diag.mean() + 1) / 2, 0, 1))  # remap [-1,1] → [0,1]
        return cls(mean_state=mean_state, coherence=C, Q=Q)


# ════════════════════════════════════════════════════════════════════
# 5. POZYCJA 10 — OPERATOR MAPY Π₁₀ (gwiazdka 8-ramienna)
# ════════════════════════════════════════════════════════════════════

def map_to_star(cubes: list[CubeState]) -> np.ndarray:
    """
    Π₁₀: rzut 8 kostek na 8 kierunków gwiazdki.
    
    Każdemu wierzchołkowi k przypisany jest kąt:
        θ_k = k · π/4   (w radianach: 0, 45°, 90°, ..., 315°)
    
    Mapa: punkt na gwiazdce = (cos θ_k, sin θ_k) · ||S_k||
    """
    star = np.zeros((8, 2))
    for i, c in enumerate(cubes):
        theta = c.k * np.pi / 4
        magnitude = np.linalg.norm(c.features)
        star[i] = np.array([np.cos(theta), np.sin(theta)]) * magnitude
    return star


# ════════════════════════════════════════════════════════════════════
# 6. TRIANGULACJA — TEST c = a + b (i warianty)
# ════════════════════════════════════════════════════════════════════

# Rejestr relacji do sprawdzania
TRIAD_RELATIONS: dict[str, Callable[[np.ndarray, np.ndarray], np.ndarray]] = {
    'add':   lambda a, b: a + b,
    'sub':   lambda a, b: np.abs(a - b),
    'mul':   lambda a, b: a * b,
    'div':   lambda a, b: np.divide(a, b, out=np.zeros_like(a), where=b!=0),
    'mean':  lambda a, b: (a + b) / 2,
}


def test_triangulation(
    a: np.ndarray, b: np.ndarray, c: np.ndarray,
    tolerance: float = 0.15,
) -> dict[str, float]:
    """
    Dla triady (a, b, c) testuje, które relacje f(a,b) ≈ c są poprawne.
    
    Zwraca słownik relacja → reszta znormalizowana.
    Triangulacja 'poprawna' ⟺ reszta < tolerance.
    """
    results = {}
    norm_c = np.linalg.norm(c) + 1e-9
    for name, f in TRIAD_RELATIONS.items():
        predicted = f(a, b)
        residual = np.linalg.norm(predicted - c) / norm_c
        results[name] = float(residual)
    return results


def find_triangulations(cubes: list[CubeState], tolerance: float = 0.15) -> list[dict]:
    """
    T(S) — zbiór wszystkich poprawnych triangulacji w sześcianie.
    
    Dla każdej triady (i,j,k) ∈ C(V,3) = 56 triad testujemy relacje.
    """
    triads = []
    for i, j, k in combinations(range(8), 3):
        tests = test_triangulation(
            cubes[i].features, cubes[j].features, cubes[k].features,
            tolerance=tolerance,
        )
        valid = {rel: res for rel, res in tests.items() if res < tolerance}
        if valid:
            triads.append({
                'triad': (i, j, k),
                'valid_relations': valid,
                'best_relation': min(valid, key=valid.get),
            })
    return triads


# ════════════════════════════════════════════════════════════════════
# 7. COLLAPSE DETECTION
# ════════════════════════════════════════════════════════════════════

def microcollapses(C: np.ndarray, theta_micro: float = 0.3) -> list[tuple[int, int]]:
    """μ(i,j): pary z koherencją poniżej progu — lokalne 'szczeliny'."""
    pairs = []
    for i in range(8):
        for j in range(i+1, 8):
            if abs(C[i, j]) < theta_micro:
                pairs.append((i, j))
    return pairs


def macrocollapse(Q: float, theta_macro: float = 0.4) -> bool:
    """M: globalne załamanie koherencji."""
    return Q < theta_macro


# ════════════════════════════════════════════════════════════════════
# 8. FRACTAL PROPAGATION  F
# ════════════════════════════════════════════════════════════════════

def propagate_fractal(
    cubes: list[CubeState],
    triads: list[dict],
    alpha: float = 0.1,
) -> list[CubeState]:
    """
    Operator F: gdy triada (i,j,k) jest poprawna, 'odcisk' propaguje się
    na sąsiadujące triady przez aktualizację:
    
        S_k' ← (1-α)·S_k' + α·f(S_i', S_j')
    
    gdzie (i',j',k') to triada w Hamming-neighborhood triady (i,j,k),
    a f to najlepsza relacja z triangulacji.
    """
    new_features = [c.features.copy() for c in cubes]
    
    for t in triads:
        i, j, k = t['triad']
        f = TRIAD_RELATIONS[t['best_relation']]
        # Znajdź 'sąsiednie' triady przez flip pojedynczego bitu
        for flip_bit in range(3):
            i2 = i ^ (1 << flip_bit)
            j2 = j ^ (1 << flip_bit)
            k2 = k ^ (1 << flip_bit)
            if len({i2, j2, k2}) == 3:  # nadal poprawna triada
                predicted = f(cubes[i2].features, cubes[j2].features)
                new_features[k2] = (1-alpha) * new_features[k2] + alpha * predicted
    
    return [
        CubeState(k=c.k, features=new_features[idx], embedding=c.embedding)
        for idx, c in enumerate(cubes)
    ]


# ════════════════════════════════════════════════════════════════════
# 9. SPLĄTANIE — miara entanglement
# ════════════════════════════════════════════════════════════════════

def entanglement_measure(cubes: list[CubeState]) -> float:
    """
    Miara splątania przez rank macierzy Gramma:
        G[i,j] = ⟨S_i, S_j⟩
    
    Jeśli rank(G) = 8 → stany liniowo niezależne (klasyczne).
    Jeśli rank(G) < 8 → zachodzi korelacja / 'splątanie'.
    
    Zwracamy 1 - (rank/8), więc wartość bliska 1 = duże splątanie.
    """
    V = np.stack([c.vector() for c in cubes])
    G = V @ V.T
    rank = np.linalg.matrix_rank(G, tol=1e-6)
    return 1.0 - rank / 8.0


# ════════════════════════════════════════════════════════════════════
# 10. CNOTY WINGMAKERS  —  funkcja walidacji akcji
# ════════════════════════════════════════════════════════════════════

VIRTUES = ('gratitude', 'compassion', 'forgiveness', 'humility', 'understanding', 'courage')


@dataclass
class VirtueProfile:
    """
    Profil cnót W ∈ ℝ⁶ — wagi przypisane do każdej z 6 cnót.
    Każdy węzeł w siatce może mieć własny profil.
    """
    weights: np.ndarray  # kształt (6,)

    def __post_init__(self):
        assert self.weights.shape == (6,), "Profil cnót musi być 6-wymiarowy"

    def resonance(self, action_vec: np.ndarray) -> float:
        """
        rezonans(a) = cos(V(a), W) ∈ [-1, 1]
        
        action_vec: ocena akcji w przestrzeni 6 cnót, V(a) ∈ ℝ⁶.
        Dodatnia wartość = akcja wspiera profil cnót węzła.
        """
        return cosine(action_vec, self.weights)


# ════════════════════════════════════════════════════════════════════
# 11. STAN RDZENIA — kompletna jednostka q3sh
# ════════════════════════════════════════════════════════════════════

@dataclass
class Q3ShCore:
    """
    Pełny rdzeń q3sh:
      - 8 kostek (pozycje 1-8)
      - Centrum (pozycja 9, wirtualne)
      - Mapa gwiazdki (pozycja 10, projekcja)
    """
    cubes: list[CubeState]
    center: Center9 = field(init=False)
    star_map: np.ndarray = field(init=False)

    def __post_init__(self):
        assert len(self.cubes) == 8
        self.recompute()

    def recompute(self):
        self.center = Center9.from_cubes(self.cubes)
        self.star_map = map_to_star(self.cubes)

    def report(self) -> dict:
        """Pełna diagnostyka stanu rdzenia."""
        triads = find_triangulations(self.cubes)
        micro = microcollapses(self.center.coherence)
        return {
            'Q':                self.center.Q,
            'macrocollapse':    macrocollapse(self.center.Q),
            'microcollapses':   len(micro),
            'triangulations':   len(triads),
            'entanglement':     entanglement_measure(self.cubes),
            'mean_state_norm':  float(np.linalg.norm(self.center.mean_state)),
        }

    def step(self, alpha: float = 0.1) -> None:
        """
        Jeden krok ewolucji: triangulacje → propagacja fraktalna → update.
        To jest pętla self-improvement rdzenia.
        """
        triads = find_triangulations(self.cubes)
        self.cubes = propagate_fractal(self.cubes, triads, alpha=alpha)
        self.recompute()


# ════════════════════════════════════════════════════════════════════
# DEMO
# ════════════════════════════════════════════════════════════════════

def demo():
    """
    Mini-demonstracja — dwa scenariusze:
      A) Stany losowe  → brak triangulacji (szum klasyczny)
      B) Stany z wbudowaną strukturą addytywną → triangulacje + propagacja
    
    Pokazuje, że triangulacja jest NIETRYWIALNYM TESTEM spójności,
    nie artefaktem arbitralnej tolerancji.
    """
    rng = np.random.default_rng(42)
    n = 5
    
    print("=" * 60)
    print("q3sh — Rdzeń 8+1+1 (Hierarchia 10 Kostek)")
    print("=" * 60)
    
    # --- Scenariusz A: czysty szum ---
    cubes_A = [CubeState(k=k, features=rng.uniform(0, 1, size=n)) for k in range(8)]
    core_A = Q3ShCore(cubes=cubes_A)
    r_A = core_A.report()
    print(f"\n[A] Szum losowy:")
    print(f"    Q={r_A['Q']:.4f}  triads={r_A['triangulations']}  "
          f"micro={r_A['microcollapses']}  E={r_A['entanglement']:.3f}")

    # --- Scenariusz B: stany skonstruowane tak, by c = a + b zachodziło ---
    # S₀, S₁, S₂ są "bazowe", reszta = ich kombinacje liniowe
    base = [rng.uniform(0, 1, size=n) for _ in range(3)]
    structured = [
        base[0],                         # k=0: a
        base[1],                         # k=1: b
        base[0] + base[1],               # k=2: a + b    ← c = a+b
        base[2],                         # k=3: d
        base[0] + base[2],               # k=4: a + d
        base[1] + base[2],               # k=5: b + d
        base[0] + base[1] + base[2],     # k=6: a + b + d
        (base[0] + base[1]) / 2,         # k=7: mean(a, b)
    ]
    cubes_B = [CubeState(k=k, features=structured[k]) for k in range(8)]
    core_B = Q3ShCore(cubes=cubes_B)
    r_B = core_B.report()
    print(f"\n[B] Stany ze strukturą addytywną:")
    print(f"    Q={r_B['Q']:.4f}  triads={r_B['triangulations']}  "
          f"micro={r_B['microcollapses']}  E={r_B['entanglement']:.3f}")

    print(f"\n    Ewolucja (5 kroków fractal propagation, α=0.1):")
    for step in range(5):
        core_B.step(alpha=0.1)
        r = core_B.report()
        print(f"      krok {step+1}: Q={r['Q']:.4f}  "
              f"triads={r['triangulations']:3d}  "
              f"micro={r['microcollapses']:2d}  "
              f"E={r['entanglement']:.3f}")

    print(f"\n[C] Cnoty WingMakers — walidacja akcji:")
    W = VirtueProfile(weights=np.array([0.2, 0.3, 0.1, 0.1, 0.2, 0.1]))
    a1 = np.array([0.1, 0.4, 0.1, 0.0, 0.3, 0.1])  # akcja spójna z profilem
    a2 = np.array([0.9, 0.0, 0.7, 0.8, 0.0, 0.9])  # akcja dysonansowa
    print(f"    W        = {W.weights}")
    print(f"    V(a₁)    = {a1}   rezonans = {W.resonance(a1):+.4f}")
    print(f"    V(a₂)    = {a2}   rezonans = {W.resonance(a2):+.4f}")


if __name__ == '__main__':
    demo()
