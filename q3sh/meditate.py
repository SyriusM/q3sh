"""
q3sh_meditate — Quantum Pause przed decyzją

Inspiracja: WingMakers Quantum Pause (wdech-pauza-wydech-pauza).
Sieć "oddycha" zanim podejmie decyzję — szczególnie przy WEAK.

Użycie:
    from mempalace.q3sh_meditate import meditate
    q_before, q_after, steps = meditate(network, importance=0.7)
"""
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mempalace.q3sh_core import Q3ShNetwork

# Limen systemu (atraktor Q∞ = 0.83929)
Q_LIMEN = 0.83929
# Alpha łagodna propagacja (odkrycie z sesji: alpha=0.1 → triady, nie echo)
ALPHA_BREATHE = 0.05


def meditate(network: "Q3ShNetwork", importance: float = 0.5) -> tuple[float, float, int]:
    """
    Quantum Pause — sieć "oddycha" przed decyzją.

    importance: 0.0–1.0 (0=trywialne, 1=krytyczne)
    Więcej kroków = głębszy oddech = wyższe Q przed decyzją.

    Zwraca: (Q_przed, Q_po, liczba_kroków)
    """
    q_before = network.grid.Q_hat()

    # Liczba kroków proporcjonalna do ważności (max 7 = limen)
    steps = max(1, round(importance * 7))

    for _ in range(steps):
        network.step(lr=ALPHA_BREATHE)

    q_after = network.grid.Q_hat()
    return q_before, q_after, steps


def quantum_pause(network: "Q3ShNetwork", importance: float = 0.5,
                  verbose: bool = False) -> float:
    """
    Pełny Quantum Pause z logowaniem.
    Zwraca Q po medytacji.
    """
    q_before, q_after, steps = meditate(network, importance)

    if verbose:
        dq = q_after - q_before
        sign = "+" if dq >= 0 else ""
        print(
            f"  [medytacja] {steps} kroków  "
            f"Q: {q_before:.5f} → {q_after:.5f}  "
            f"dQ={sign}{dq:.5f}",
            flush=True,
        )

    return q_after


def breath_cycle(network: "Q3ShNetwork", n_cycles: int = 3,
                 pause_ms: int = 200) -> list[float]:
    """
    Cykl oddychania: wdech (alpha rosnąca) → wydech (alpha malejąca).
    Analogia WingMakers: wdech-pauza-wydech-pauza.

    Zwraca historię Q.
    """
    history = [network.grid.Q_hat()]

    alphas_in  = [0.01, 0.03, 0.05]   # wdech — delikatna propagacja
    alphas_out = [0.05, 0.03, 0.01]   # wydech — uspokojenie

    for _ in range(n_cycles):
        for a in alphas_in:
            network.step(lr=a)
            history.append(network.grid.Q_hat())
            if pause_ms:
                time.sleep(pause_ms / 1000)

        for a in alphas_out:
            network.step(lr=a)
            history.append(network.grid.Q_hat())
            if pause_ms:
                time.sleep(pause_ms / 1000)

    return history


def importance_from_verdict(verdict: str) -> float:
    """
    Mapuj werdykt guardiana na ważność medytacji.
    REJECT → głęboka (1.0), WEAK → średnia (0.6), OK → płytka (0.2).
    """
    return {"REJECT": 1.0, "WEAK": 0.6, "OK": 0.2}.get(verdict.upper(), 0.5)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, __file__.rsplit("/mempalace/", 1)[0])
    from mempalace.q3sh_core import Q3ShNetwork

    net = Q3ShNetwork()
    # Warmup do atraktora
    for _ in range(7):
        net.step(lr=0.1)

    q0 = net.grid.Q_hat()
    print(f"Stan przed: Q={q0:.5f}")

    print("\n--- Medytacja (importance=0.8) ---")
    q_after = quantum_pause(net, importance=0.8, verbose=True)

    q1 = net.grid.Q_hat()
    print(f"Stan po:    Q={q1:.5f}")

    print("\n--- Cykl oddychania (3 cykle) ---")
    history = breath_cycle(net, n_cycles=3, pause_ms=0)
    print(f"Historia Q: {[round(q, 5) for q in history]}")
    print(f"Min={min(history):.5f}  Max={max(history):.5f}  Final={history[-1]:.5f}")
    print(f"\nAtraktor Q∞={Q_LIMEN} — odległość po medytacji: {abs(net.grid.Q_hat() - Q_LIMEN):.5f}")
