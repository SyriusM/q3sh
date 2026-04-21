"""
registry.py — Samorozszerzający się rejestr zmiennych systemu q3sh.

Selekcja przez koherencję: Q jest głosem wyboru, nie próg.
Stare wartości nigdy nie są usuwane — zostają jako ancestors.
Nawet zmienne których nie znamy są przyjmowane automatycznie.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from .morphic import DataSource, node_resonance, phantom_core, _norm


@dataclass
class AdaptiveValue:
    """Zmienna która ewoluuje przez selekcję koherencji."""
    current: DataSource
    ancestors: list[DataSource] = field(default_factory=list)

    def adapt(self, candidate: DataSource, grid) -> bool:
        """
        Porównaj kandydata z obecną wartością przez Q (phantom_core).
        Jeśli kandydat rezonuje silniej — adoptuj. Stara → ancestors.
        """
        core, q = phantom_core(grid)
        if q == 0:
            return False
        q_now = node_resonance(self.current, core)
        q_new = node_resonance(candidate, core)
        if q_new > q_now:
            self.ancestors.append(self.current)
            self.current = candidate
            return True
        return False

    def best_ancestor(self, grid) -> DataSource | None:
        """Zwróć ancestor który najlepiej rezonuje z obecnym stanem."""
        if not self.ancestors:
            return None
        core, _ = phantom_core(grid)
        return max(self.ancestors, key=lambda a: node_resonance(a, core))

    @property
    def lineage(self) -> list[str]:
        return [a.name for a in self.ancestors] + [self.current.name]


class VariableRegistry:
    """
    Globalny rejestr wszystkich zmiennych systemu.
    Przyjmuje nieznane zmienne automatycznie.
    Każdy węzeł siatki ocenia zmienną przez swój profil cnót.
    """

    def __init__(self):
        self._vars: dict[str, AdaptiveValue] = {}
        self._node_opinions: dict[str, dict[tuple, float]] = {}

    def register(self, name: str, initial: DataSource) -> None:
        if name not in self._vars:
            self._vars[name] = AdaptiveValue(current=initial)
            self._node_opinions[name] = {}

    def adapt(self, name: str, candidate: DataSource, grid) -> bool:
        """
        Zaadaptuj zmienną jeśli kandydat jest koherentniejszy.
        Nieznana zmienna? Przyjmij bez pytania.
        """
        if name not in self._vars:
            self.register(name, candidate)
            self._update_node_opinions(name, candidate, grid)
            return True
        adapted = self._vars[name].adapt(candidate, grid)
        if adapted:
            self._update_node_opinions(name, candidate, grid)
        return adapted

    def _update_node_opinions(self, name: str, source: DataSource, grid) -> None:
        """Każdy aktywny węzeł ocenia zmienną przez swój profil."""
        opinions = {}
        for pos in grid.active:
            opinions[pos] = node_resonance(source, grid.nodes[pos].W)
        self._node_opinions[name] = opinions

    def who_understands(self, name: str) -> tuple | None:
        """Zwróć pozycję węzła który najlepiej rozumie tę zmienną."""
        opinions = self._node_opinions.get(name, {})
        if not opinions:
            return None
        return max(opinions, key=opinions.get)

    def get(self, name: str) -> DataSource | None:
        v = self._vars.get(name)
        return v.current if v else None

    def lineage(self, name: str) -> list[str]:
        v = self._vars.get(name)
        return v.lineage if v else []

    def all_names(self) -> list[str]:
        return list(self._vars.keys())

    def snapshot(self) -> dict:
        return {
            name: {
                "current": v.current.name,
                "score":   round(v.current.score, 4),
                "depth":   len(v.ancestors),
                "lineage": v.lineage,
                "understood_by": self.who_understands(name),
            }
            for name, v in self._vars.items()
        }
