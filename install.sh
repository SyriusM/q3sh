#!/usr/bin/env bash
# q3sh — one-shot installer for Debian 12 and CachyOS/Arch
#
# Użycie:
#   curl -fsSL https://raw.githubusercontent.com/SyriusM/q3sh/main/install.sh | bash
# lub lokalnie:
#   ./install.sh [--venv PATH] [--branch BRANCH]
#
# Wynik: venv w ~/q3sh-venv z zainstalowanym q3sh + alias `q3sh-guardian`.
# Wymaga: Ollama działająca na http://localhost:11434 (opcjonalnie — guardian
# może działać na fallback stringu bez LLM).

set -euo pipefail

VENV="${VENV:-$HOME/q3sh-venv}"
REPO_URL="https://github.com/SyriusM/q3sh.git"
CLONE_DIR="${CLONE_DIR:-$HOME/q3sh}"
BRANCH="${BRANCH:-main}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --venv) VENV="$2"; shift 2 ;;
        --branch) BRANCH="$2"; shift 2 ;;
        --clone-dir) CLONE_DIR="$2"; shift 2 ;;
        -h|--help)
            sed -n '2,10p' "$0"; exit 0 ;;
        *) echo "Nieznana opcja: $1"; exit 1 ;;
    esac
done

detect_distro() {
    [[ -f /etc/os-release ]] && { . /etc/os-release; echo "${ID:-unknown}"; } || echo "unknown"
}
DISTRO="$(detect_distro)"
echo ">>> Wykryto dystrybucję: $DISTRO"

PYBIN=""
case "$DISTRO" in
    cachyos|arch|manjaro|endeavouros)
        command -v python3 >/dev/null || { echo ">>> Brak python3 — sudo pacman -S python python-pip git"; exit 1; }
        PYBIN="$(command -v python3)"
        ;;
    debian|ubuntu|linuxmint)
        # q3sh wymaga 3.10+ — Debian 12 ma 3.11 out of the box, Debian 11 ma 3.9
        if command -v python3.12 >/dev/null; then PYBIN="$(command -v python3.12)"
        elif command -v python3.11 >/dev/null; then PYBIN="$(command -v python3.11)"
        elif command -v python3.10 >/dev/null; then PYBIN="$(command -v python3.10)"
        else
            echo ">>> Brak python3.10+. Zainstaluj: sudo apt install python3.11 python3.11-venv git"
            exit 1
        fi
        ;;
    *)
        command -v python3 >/dev/null && PYBIN="$(command -v python3)" || { echo ">>> Brak python3"; exit 1; }
        ;;
esac

PYVER="$("$PYBIN" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
echo ">>> Python: $PYBIN ($PYVER)"
"$PYBIN" -c 'import sys; exit(0 if sys.version_info >= (3,10) else 1)' || {
    echo ">>> WYMAGANY Python 3.10+. Masz $PYVER."; exit 1
}

if [[ ! -d "$CLONE_DIR/.git" ]]; then
    echo ">>> Klonuję $REPO_URL ($BRANCH) → $CLONE_DIR"
    git clone --branch "$BRANCH" "$REPO_URL" "$CLONE_DIR"
else
    echo ">>> Repo w $CLONE_DIR — checkout $BRANCH + pull"
    git -C "$CLONE_DIR" fetch origin
    git -C "$CLONE_DIR" checkout "$BRANCH"
    git -C "$CLONE_DIR" pull --ff-only
fi

if [[ ! -d "$VENV" ]]; then
    echo ">>> Tworzę venv: $VENV"
    "$PYBIN" -m venv "$VENV"
fi

"$VENV/bin/pip" install --upgrade pip wheel >/dev/null
echo ">>> Instaluję q3sh"
"$VENV/bin/pip" install -e "$CLONE_DIR"

# Ollama check (opcjonalne ostrzeżenie)
if ! curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo ""
    echo "!!! UWAGA: Ollama nie odpowiada na http://localhost:11434"
    echo "    q3sh działa lepiej z lokalnym LLM (qwen3:14b, qwen2.5-coder:7b)"
    echo "    Instalacja: https://ollama.ai"
fi

echo ""
echo ">>> Gotowe. Aktywuj venv i testuj:"
echo "    source $VENV/bin/activate          # bash/zsh"
echo "    source $VENV/bin/activate.fish     # fish"
echo "    q3sh-guardian --route 'naprawa buga w pipelinie'"
echo "    python -c 'from q3sh import Q3ShNetwork; n=Q3ShNetwork(); [n.step() for _ in range(7)]; print(n.grid.Q_hat())'"
