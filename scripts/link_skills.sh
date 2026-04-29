#!/usr/bin/env bash

# Adapted from https://github.com/mattpocock/skills/blob/main/scripts/link-skills.sh
set -euo pipefail

# Links all skills in this repository into local agent skill directories.
# Default targets are Claude and Codex. Pass "copilot" explicitly if your
# Copilot setup watches a local skills directory.

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SKILLS_ROOT="$REPO/skills"
FORCE=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: scripts/link_skills.sh [options] [agent...]

Agents:
  claude    Link into ${CLAUDE_SKILLS_DIR:-${CLAUDE_HOME:-$HOME/.claude}/skills}
  codex     Link into ${CODEX_SKILLS_DIR:-${CODEX_HOME:-$HOME/.codex}/skills}
  copilot   Link into ${COPILOT_SKILLS_DIR:-${COPILOT_HOME:-$HOME/.copilot}/skills}
  all       Link into Claude, Codex, and Copilot

Options:
  --dest NAME=PATH  Also link skills into a custom destination
  --dry-run         Print actions without changing files
  --force           Replace existing non-symlink skill directories
  -h, --help        Show this help

With no agents, the script links Claude and Codex.
EOF
}

agent_dest() {
  case "$1" in
    claude)
      printf '%s\n' "${CLAUDE_SKILLS_DIR:-${CLAUDE_HOME:-$HOME/.claude}/skills}"
      ;;
    codex)
      printf '%s\n' "${CODEX_SKILLS_DIR:-${CODEX_HOME:-$HOME/.codex}/skills}"
      ;;
    copilot)
      printf '%s\n' "${COPILOT_SKILLS_DIR:-${COPILOT_HOME:-$HOME/.copilot}/skills}"
      ;;
    *)
      echo "error: unknown agent '$1'" >&2
      usage >&2
      exit 2
      ;;
  esac
}

declare -a TARGET_NAMES=()
declare -a TARGET_DIRS=()

add_target() {
  local name="$1"
  local dest="$2"
  local i

  for i in "${!TARGET_DIRS[@]}"; do
    if [ "${TARGET_DIRS[$i]}" = "$dest" ]; then
      return
    fi
  done

  TARGET_NAMES+=("$name")
  TARGET_DIRS+=("$dest")
}

add_agent() {
  local agent="$1"

  if [ "$agent" = "all" ]; then
    add_agent claude
    add_agent codex
    add_agent copilot
    return
  fi

  add_target "$agent" "$(agent_dest "$agent")"
}

link_one_dest() {
  local label="$1"
  local dest="$2"
  local resolved skill_md src name target current_target

  # If a skills destination is a symlink that resolves into this repo, we'd end
  # up writing per-skill symlinks back into the repo's own skills/ tree.
  if [ -L "$dest" ]; then
    resolved="$(readlink -f "$dest" || true)"
    case "$resolved" in
      "$REPO"|"$REPO"/*)
        echo "error: $dest is a symlink into this repo ($resolved)." >&2
        echo "Remove it (rm \"$dest\") and re-run; the script will recreate it as a real dir." >&2
        exit 1
        ;;
    esac
  fi

  echo "==> $label: $dest"

  if [ "$DRY_RUN" -eq 0 ]; then
    mkdir -p "$dest"
  fi

  find "$SKILLS_ROOT" -name SKILL.md -not -path '*/node_modules/*' -print0 |
  sort -z |
  while IFS= read -r -d '' skill_md; do
    src="$(dirname "$skill_md")"
    name="$(basename "$src")"
    target="$dest/$name"

    if [ -L "$target" ]; then
      current_target="$(readlink -f "$target" || true)"
      if [ "$current_target" = "$src" ]; then
        echo "linked $label/$name -> $src"
        continue
      fi
    fi

    if [ -e "$target" ] && [ ! -L "$target" ]; then
      if [ "$FORCE" -eq 0 ]; then
        echo "skip $label/$name: $target exists and is not a symlink (use --force to replace)" >&2
        continue
      fi

      if [ "$DRY_RUN" -eq 0 ]; then
        rm -rf "$target"
      fi
    fi

    if [ "$DRY_RUN" -eq 0 ]; then
      ln -sfn "$src" "$target"
    fi

    echo "linked $label/$name -> $src"
  done
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dest)
      if [ "$#" -lt 2 ]; then
        echo "error: --dest requires NAME=PATH" >&2
        exit 2
      fi
      case "$2" in
        *=*) add_target "${2%%=*}" "${2#*=}" ;;
        *)
          echo "error: --dest requires NAME=PATH" >&2
          exit 2
          ;;
      esac
      shift 2
      ;;
    --dest=*)
      dest_arg="${1#--dest=}"
      case "$dest_arg" in
        *=*) add_target "${dest_arg%%=*}" "${dest_arg#*=}" ;;
        *)
          echo "error: --dest requires NAME=PATH" >&2
          exit 2
          ;;
      esac
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --force)
      FORCE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    claude|codex|copilot|all)
      add_agent "$1"
      shift
      ;;
    *)
      echo "error: unknown argument '$1'" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ "${#TARGET_DIRS[@]}" -eq 0 ]; then
  add_agent claude
  add_agent codex
fi

for i in "${!TARGET_DIRS[@]}"; do
  link_one_dest "${TARGET_NAMES[$i]}" "${TARGET_DIRS[$i]}"
done
