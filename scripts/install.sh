#!/usr/bin/env bash
set -euo pipefail

OBScript_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
OBScript_BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
OBScript_SKILLS_DIR="${CODEX_HOME:-$HOME/.codex}/skills"

mkdir -p "$OBScript_BIN_DIR" "$OBScript_SKILLS_DIR"

install_link() {
    local source_path="$1"
    local target_path="$2"
    if [[ -e "$target_path" && ! -L "$target_path" ]]; then
        printf 'obscript install: refusing to replace %s\n' "$target_path" >&2
        return 1
    fi
    if [[ -L "$target_path" ]]; then
        local current_target
        current_target="$(readlink -f -- "$target_path")"
        if [[ "$current_target" != "$(readlink -f -- "$source_path")" ]]; then
            printf 'obscript install: refusing to replace symlink %s -> %s\n' "$target_path" "$current_target" >&2
            return 1
        fi
    fi
    ln -sfn -- "$source_path" "$target_path"
}

install_link "$OBScript_ROOT/bin/obscript" "$OBScript_BIN_DIR/obscript"

for skill_path in "$OBScript_ROOT"/skills/*; do
    [[ -d "$skill_path" ]] || continue
    install_link "$skill_path" "$OBScript_SKILLS_DIR/$(basename -- "$skill_path")"
done

printf 'Installed obscript at %s\n' "$OBScript_BIN_DIR/obscript"
printf 'Installed Codex skills from %s\n' "$OBScript_ROOT/skills"
