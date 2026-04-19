"""
q3sh — Quantum 3 Shell
Virtue-based AI coherence network.
"""
__version__ = "0.1.0"

from q3sh.core import Q3ShNetwork, evaluate_action
from q3sh.guardian import guard, route_to_virtue
from q3sh.meditate import meditate, quantum_pause

__all__ = ["Q3ShNetwork", "evaluate_action", "guard", "route_to_virtue",
           "meditate", "quantum_pause"]
