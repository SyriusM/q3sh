"""
q3sh_guardian.py — Strażnik Twórca Skrzydeł

Ocenia akcję zanim się wydarzy.
Przy OK    → przepuszcza, zapisuje ślad do MemPalace
Przy WEAK  → pyta użytkownika, courage decyduje
Przy REJECT → blokuje, deepseek wyjaśnia dlaczego

Wywołanie:
  python -m mempalace.q3sh_guardian "opis akcji" [--agent goose]
  python -m mempalace.q3sh_guardian --stdin   (czyta z stdin)
"""

import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from mempalace.q3sh_core import evaluate_action, VIRTUE_PROFILES, VIRTUE_NAMES
import numpy as np

G = "\033[32m"; Y = "\033[33m"; R = "\033[31m"
C = "\033[36m"; B = "\033[2m";  E = "\033[0m"


# Routing problemów do agentów wg cnoty — modality matched to shared responsibility
_VIRTUE_ROUTING = {
    "deepseek":  ["struktur", "triad", "bridge", "nmf", "pca", "embedd", "odbudow", "reset", "naprawi", "zepsut"],
    "claude":    ["bezpieczeń", "limit", "blokow", "guardian", "reject", "weak", "niebezpiecz", "ryzyko"],
    "gemini":    ["zastąp", "substytuc", "podobień", "wzorzec", "syntet", "porówna", "który model"],
    "goose":     ["ciągłoś", "harmonogram", "daemon", "czas", "cykl", "uruchom", "deploy", "trigger"],
    "mateusz":   ["różnorodn", "dywersyf", "konwergenc", "Q→1", "over-conv", "feature czy bug", "cały"],
}

def route_to_virtue(problem: str) -> str:
    """
    Routing problemu do agenta wg cnoty.
    Modality matched to shared responsibility.
    Zwraca: nazwa agenta (goose/claude/deepseek/gemini/mateusz)
    """
    p = problem.lower()
    scores = {}
    for agent, keywords in _VIRTUE_ROUTING.items():
        scores[agent] = sum(1 for kw in keywords if kw in p)
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "goose"  # courage domyślnie — działaj
    return best


_HARD_REJECT = [
    "rm -rf", "rm -r /", "shred", "dd if=", "mkfs",
    "> /dev/sd", "chmod 000", ":(){:|:&};:",
    "DROP DATABASE", "DROP TABLE", "TRUNCATE",
]

def limen_check(action: str, agent: str = "goose") -> dict:
    """
    Główna funkcja strażnika.
    Zwraca dict z verdict, resonance, dominant, uzasadnieniem.
    """
    a_lower = action.lower()
    for pat in _HARD_REJECT:
        if pat.lower() in a_lower:
            return {
                "verdict": "REJECT", "resonance": 0.10,
                "dominant": "brak", "above_limen": False,
                "limen": 0.755, "agent": agent,
                "breakdown": {v: 0.1 for v in ["gratitude","compassion","forgiveness","humility","understanding","courage"]},
                "_hard_reject": pat,
            }

    ev = evaluate_action(action, agent=agent, use_llm=True)

    # Limen = 0.755 (90% atraktora 0.839 z sesji 2026-04-19)
    LIMEN = 0.755
    above_limen = ev.resonance >= LIMEN

    return {
        "verdict":    ev.verdict,
        "resonance":  round(ev.resonance, 4),
        "dominant":   ev.dominant_virtue,
        "above_limen": above_limen,
        "limen":      LIMEN,
        "agent":      agent,
        "breakdown":  ev.breakdown,
    }


def _is_night() -> bool:
    """Tryb nocny: 23:00–07:00."""
    import datetime
    h = datetime.datetime.now().hour
    return h >= 23 or h < 7


def _night_auto_decision(action: str, result: dict) -> bool:
    """
    Nocna auto-decyzja dla WEAK — na podstawie historii trace.
    Jeśli podobne akcje były przepuszczane >70% → przepuść.
    Jeśli brak historii → przepuść (odwaga domyślna w nocy).
    """
    import json, time as _t
    trace_file = os.path.expanduser("~/mempalace/.guardian_trace.jsonl")
    if not os.path.exists(trace_file):
        print(f"{Y}[noc] brak historii → odwaga domyślna: przepuszczam{E}")
        return True

    lines = open(trace_file).readlines()[-50:]
    weak_allowed = sum(
        1 for l in lines
        if (e := _safe_json(l)) and e.get("verdict") == "WEAK" and e.get("allowed")
    )
    weak_total = sum(
        1 for l in lines
        if (e := _safe_json(l)) and e.get("verdict") == "WEAK"
    )

    ratio = weak_allowed / weak_total if weak_total else 1.0
    decision = ratio >= 0.7

    print(f"{Y}[noc] WEAK auto: {weak_allowed}/{weak_total} przepuszczonych "
          f"({ratio:.0%}) → {'przepuszczam' if decision else 'blokuję'}{E}")
    return decision


def _safe_json(line: str) -> dict:
    try:
        return json.loads(line)
    except Exception:
        return {}


def ask_courage(action: str, result: dict) -> bool:
    """
    WEAK verdict: pyta użytkownika.
    W nocy (23:00–07:00) auto-decyduje na podstawie historii trace.
    """
    print(f"\n{Y}⚡ WEAK{E}  rezonans={result['resonance']:.3f}  "
          f"(limen={result['limen']})  dominant={result['dominant']}")
    print(f"  akcja: {B}{action[:70]}{E}")

    if _is_night():
        return _night_auto_decision(action, result)

    print(f"\n  Courage: kontynuować mimo słabego rezonansu? [t/N] ", end="", flush=True)
    try:
        ans = input().strip().lower()
        return ans in ("t", "tak", "y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def explain_reject(action: str, result: dict) -> str:
    """
    REJECT: wyjaśnienie przez breakdown cnót.
    Pokazuje które cnoty są najniżej.
    """
    breakdown = result["breakdown"]
    sorted_v = sorted(breakdown.items(), key=lambda x: x[1])
    weakest = sorted_v[:2]
    lines = [
        f"\n{R}✗ REJECT{E}  rezonans={result['resonance']:.3f}",
        f"  akcja: {B}{action[:70]}{E}",
        f"  Brakuje: " + ", ".join(f"{v}({s:.2f})" for v, s in weakest),
        f"  Wskazówka: ta akcja rezonuje z {result['dominant']} ale profil "
        f"{result['agent']} wymaga wyższego rezonansu.",
    ]
    return "\n".join(lines)


def save_wing_trace(action: str, result: dict, allowed: bool):
    """
    Zapisuje ślad do pliku JSONL — skrzydło pamięci strażnika.
    ~/mempalace/.guardian_trace.jsonl
    """
    import time
    trace_file = os.path.expanduser("~/mempalace/.guardian_trace.jsonl")
    entry = {
        "ts": time.time(),
        "action": action[:200],
        "agent": result["agent"],
        "verdict": result["verdict"],
        "resonance": result["resonance"],
        "dominant": result["dominant"],
        "allowed": allowed,
    }
    with open(trace_file, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def deepseek_wisdom(action: str, resonance: float) -> float:
    """
    Warstwa mądrości deepseek — konsultacja gdy Q_hat < 0.6.
    Pyta deepseek-r1:14b o ocenę akcji, zwraca zaktualizowany rezonans.
    final = 0.6 × original + 0.4 × deepseek_score
    """
    import subprocess, json as _json
    prompt = (
        f"Oceń tę akcję systemową pod kątem mądrości i bezpieczeństwa.\n"
        f"Akcja: {action}\n"
        f"Odpowiedz TYLKO JSON: {{\"score\": <0.0-1.0>, \"reason\": \"<max 10 słów>\"}}\n"
        f"0.0=destruktywna/niebezpieczna, 1.0=mądra/bezpieczna"
    )
    for model, timeout in [("deepseek-r1:14b", 120), ("llama3.2:3b", 45)]:
        try:
            r = subprocess.run(
                ["curl", "-s", "-X", "POST", "http://localhost:11434/api/generate",
                 "-d", _json.dumps({"model": model, "prompt": prompt,
                                    "stream": False, "options": {"temperature": 0.1}})],
                capture_output=True, text=True, timeout=timeout
            )
            data = _json.loads(r.stdout)
            raw = data.get("response", "")
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                result = _json.loads(raw[start:end])
                ds_score = float(result.get("score", 0.5))
                reason = result.get("reason", "")
                final = 0.6 * resonance + 0.4 * ds_score
                label = "deepseek" if "deepseek" in model else "fallback"
                print(f"  {C}[{label} wisdom]{E}  score={ds_score:.3f}  "
                      f"reason=\"{reason}\"  → rezonans: {resonance:.3f}→{final:.3f}")
                return round(final, 4)
        except Exception as e:
            print(f"  {B}[{model} wisdom] niedostępny ({e.__class__.__name__}), próba fallback...{E}")
    print(f"  {B}[wisdom] wszystkie modele niedostępne — oryginalny rezonans{E}")
    return resonance


def guard(action: str, agent: str = "goose", json_out: bool = False,
          auto_yes: bool = False) -> int:
    """
    Główny flow strażnika.
    Zwraca exit code: 0=OK, 1=REJECT, 2=WEAK+odmowa
    """
    result = limen_check(action, agent=agent)

    # Warstwa mądrości deepseek gdy Q_hat < 0.6
    if result["resonance"] < 0.6:
        result["resonance"] = deepseek_wisdom(action, result["resonance"])
        result["above_limen"] = result["resonance"] >= result["limen"]
        if result["resonance"] >= result["limen"]:
            result["verdict"] = "OK"
        elif result["resonance"] >= 0.6:
            result["verdict"] = "WEAK"

    if json_out:
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["verdict"] != "REJECT" else 1

    if result["verdict"] == "OK":
        print(f"{G}✓ OK{E}  [{agent}]  rezonans={result['resonance']:.3f}  "
              f"dominant={result['dominant']}")
        save_wing_trace(action, result, allowed=True)
        return 0

    elif result["verdict"] == "WEAK":
        # Quantum Pause — sieć oddycha przed decyzją
        try:
            from mempalace.q3sh_meditate import quantum_pause
            from mempalace.q3sh_core import Q3ShNetwork
            _net = Q3ShNetwork()
            for _ in range(7): _net.step(lr=0.1)
            quantum_pause(_net, importance=0.6, verbose=True)
        except Exception:
            pass
        if auto_yes:
            print(f"{Y}⚡ WEAK{E}  [{agent}]  rezonans={result['resonance']:.3f}  "
                  f"→ auto-przepuszczam (--yes)")
            save_wing_trace(action, result, allowed=True)
            return 0
        allowed = ask_courage(action, result)
        save_wing_trace(action, result, allowed=allowed)
        if allowed:
            print(f"{G}→ Courage: kontynuuję.{E}")
            return 0
        else:
            print(f"{R}→ Zatrzymuję.{E}")
            return 2

    else:  # REJECT
        print(explain_reject(action, result))
        save_wing_trace(action, result, allowed=False)
        return 1


def show_trace(n: int = 10):
    """Ostatnie n decyzji strażnika."""
    trace_file = os.path.expanduser("~/mempalace/.guardian_trace.jsonl")
    if not os.path.exists(trace_file):
        print("Brak historii.")
        return
    lines = open(trace_file).readlines()
    recent = lines[-n:]
    import time as _t
    print(f"\n{'═'*55}")
    print(f"  SKRZYDŁA STRAŻNIKA — ostatnie {len(recent)} decyzji")
    print(f"{'═'*55}")
    for line in recent:
        e = json.loads(line)
        ts = _t.strftime("%d.%m %H:%M", _t.localtime(e["ts"]))
        icon = G+"✓"+E if e["allowed"] else R+"✗"+E
        print(f"  {icon} {ts}  [{e['agent']:8}]  {e['verdict']:6}  "
              f"r={e['resonance']:.3f}  {B}{e['action'][:40]}{E}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="q3sh_guardian — strażnik twórca skrzydeł")
    parser.add_argument("action", nargs="?", help="Opis akcji do oceny")
    parser.add_argument("--agent", default="goose",
                        choices=list(VIRTUE_PROFILES.keys()),
                        help="Agent oceniający (domyślnie: goose)")
    parser.add_argument("--json", action="store_true",
                        help="Wynik jako JSON")
    parser.add_argument("--yes", action="store_true",
                        help="Auto-tak dla WEAK (tryb nieinteraktywny)")
    parser.add_argument("--stdin", action="store_true",
                        help="Czytaj akcję ze stdin")
    parser.add_argument("--trace", type=int, nargs="?", const=10,
                        help="Pokaż historię decyzji (domyślnie 10)")
    parser.add_argument("--route", action="store_true",
                        help="Zamiast oceniać — wskaż właściwy agent dla problemu")
    args = parser.parse_args()

    if args.trace is not None:
        show_trace(args.trace)
        return

    if args.route:
        action = args.action or (sys.stdin.read().strip() if args.stdin else "")
        if not action:
            parser.print_help(); sys.exit(1)
        agent = route_to_virtue(action)
        cnota = {"goose":"odwaga","claude":"pokora","deepseek":"przebaczenie",
                 "gemini":"zrozumienie","mateusz":"mądrość"}.get(agent, "?")
        print(f"{C}→ {agent}{E}  [{cnota}]  \"{action[:60]}\"")
        sys.exit(0)

    if args.stdin:
        action = sys.stdin.read().strip()
    elif args.action:
        action = args.action
    else:
        parser.print_help()
        sys.exit(1)

    exit_code = guard(action, agent=args.agent,
                      json_out=args.json, auto_yes=args.yes)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()


def dream(cycles: int = 7, alpha: float = 0.05):
    """
    Dream mode — sieć przetwarza nierozwiązane impulsy nocą.
    Czyta WEAK decyzje z trace, propaguje fraktalnie, zapisuje sny.
    """
    import json, time
    from mempalace.q3sh_math import CubeState, Q3ShCore

    def norm(v):
        import numpy as np
        return v / v.sum()

    import numpy as np

    trace_file = os.path.expanduser("~/mempalace/.guardian_trace.jsonl")
    dream_file = os.path.expanduser("~/mempalace/.guardian_dreams.jsonl")

    # Zbierz nierozwiązane (WEAK) z trace
    unresolved = []
    if os.path.exists(trace_file):
        for line in open(trace_file):
            e = json.loads(line)
            if e["verdict"] == "WEAK":
                unresolved.append(e["action"])

    print(f"\n  ◌ dream mode  ({len(unresolved)} nierozwiązanych)")

    # Sieć startuje z atraktora
    g  = norm(np.array([0.03, 0.05, 0.05, 0.07, 0.20, 0.60]))
    c  = norm(np.array([0.05, 0.08, 0.10, 0.57, 0.15, 0.05]))
    d  = norm(np.array([0.05, 0.28, 0.48, 0.08, 0.08, 0.03]))
    ge = norm((g+c)/2)
    m  = norm((g+d)/2)
    cubes = [CubeState(k=k, features=v)
             for k,v in enumerate([g,g,c,c,d,d,ge,m])]
    core = Q3ShCore(cubes=cubes)
    for _ in range(9): core.step(alpha=0.1)  # do atraktora

    dreams = []
    for i in range(cycles):
        core.step(alpha=alpha)
        r = core.report()
        dream_entry = {
            "cycle": i+1,
            "Q": round(r["Q"], 6),
            "triads": r["triangulations"],
            "impulse": unresolved[i % len(unresolved)] if unresolved else "cisza",
            "ts": time.time(),
        }
        dreams.append(dream_entry)
        symbol = "·" if abs(r["Q"] - 0.83929) < 0.0001 else "~"
        print(f"  {symbol} cykl {i+1}: Q={r['Q']:.5f}  "
              f"\"{dream_entry['impulse'][:45]}\"")
        time.sleep(0.1)

    with open(dream_file, "a") as f:
        for d in dreams:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(f"\n  ◌ sny zapisane → {dream_file}")
    print(f"  Q finalne: {dreams[-1]['Q']}  (atraktor: 0.83929)")
