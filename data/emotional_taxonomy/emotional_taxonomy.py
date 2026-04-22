"""
emotional_taxonomy - Python loader for NVC + Max-Neef datasets.

Use cases:
- Prompt engineering for LLMs (give model the inventory as context).
- Classification of user input into feeling/need space.
- Self-empathy CLI tools.
- Cross-mapping between frameworks.

Example:
    from emotional_taxonomy import Taxonomy
    t = Taxonomy.load()
    t.find_feeling("frustrated")          # -> ('unmet', 'annoyed', {...})
    t.needs_of_category("autonomy")       # -> list of needs
    t.maxneef_cell("creation", "doing")   # -> list of satisfiers
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).parent / "data"


@dataclass
class Taxonomy:
    feelings: dict[str, Any] = field(default_factory=dict)
    needs: dict[str, Any] = field(default_factory=dict)
    maxneef: dict[str, Any] = field(default_factory=dict)
    mapping: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, data_dir: Path | str | None = None) -> "Taxonomy":
        d = Path(data_dir) if data_dir else DATA_DIR
        return cls(
            feelings=json.loads((d / "nvc_feelings.json").read_text(encoding="utf-8")),
            needs=json.loads((k / "nvc_needs.json").read_text(encoding="utf-8")),
            maxneef=json.loads((k / "maxneef_matrix.json").read_text(encoding="utf-8")),
            mapping=json.loads((k / "mapping_nvc_maxneef.json").read_text(encoding="utf-8")),
        )

    def find_feeling(self, query: str, lang: str = "en") -> list[tuple[str, str, dict]]:
        q = query.lower().strip()
        hits: list[tuple[str, str, dict]] = []
        for cat in self.feelings["categories"]:
            for grp in cat["groups"]:
                for f in grp["feelings"]:
                    if q in f.get(lang, "").lower():
                        hits.append((cat["id"], grp["id"], f))
        return hits

    def needs_of_category(self, category_id: str, lang: str = "en") -> list[str]:
        for c in self.needs["categories"]:
            if c["id"] == category_id:
                return [n[lang] for n in c["needs"]]
        return []

    def maxneef_cell(self, need_id: str, category_id: str) -> list[str]:
        for n in self.maxneef["axiological_needs"]:
            if n["id"] == need_id:
                return n["matrix"].get(category_id, [])
        return []

    def nvc_to_maxneef(self, cnvc_category_id: str) -> list[str]:
        for m in self.mapping["mappings"]:
            if m["cnvc_category"] == cnvc_category_id:
                return m["primary_maxneef"]
        return []

    def stats(self) -> dict[str, int]:
        n_feelings = sum(len(g["feelings"]) for cat in self.feelings["categories"]
                         for g in cat["groups"])
        n_needs = sum(len(c["needs"]) for c in self.needs["categories"])
        return {"feelings": n_feelings, "needs": n_needs}
