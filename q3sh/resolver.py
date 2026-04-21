"""
resolver.py — Language-agnostic term → virtue vector resolver.

Dowolny język/termin → wektor 6 cnót.
Cache w MemPalace (similarity > 0.92) → fallback LLM.
"""
from __future__ import annotations
import numpy as np
from .virtue_llm import text_to_virtue_vector

_palace = None

def _get_palace():
    global _palace
    if _palace is not None:
        return _palace
    try:
        import sys, os
        palace_path = os.path.expanduser("~/mempalace")
        if palace_path not in sys.path:
            sys.path.insert(0, palace_path)
        from mempalace.palace import MemPalace
        _palace = MemPalace()
    except Exception:
        _palace = False
    return _palace


def resolve(term: str, cache_wing: str = "ai-tools") -> np.ndarray:
    """
    Zamień dowolny termin (dowolny język) na wektor 6 cnót.
    Próbuje cache w MemPalace najpierw, potem LLM.
    """
    palace = _get_palace()
    if palace:
        try:
            results = palace.search(term, wing=cache_wing, limit=1)
            if results and results[0].get("similarity", 0) > 0.92:
                vec = results[0].get("virtue_vector")
                if vec is not None:
                    return np.array(vec, dtype=float)
        except Exception:
            pass

    vec = text_to_virtue_vector(term)

    if palace:
        try:
            palace.add_drawer(
                wing=cache_wing,
                room="resolver_cache",
                content=term,
                metadata={"virtue_vector": vec.tolist(), "source": "resolver"},
            )
        except Exception:
            pass

    return vec
