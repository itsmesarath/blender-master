#!/usr/bin/env bash
# Install the blender-master skill into an agent's skills folder.
#   ./install.sh                 -> ~/.claude/skills/blender-master
#   ./install.sh --cursor        -> ./.cursor/skills/blender-master (current project)
#   ./install.sh --dir PATH      -> PATH/blender-master
#   add --flat to also expose every sub-skill as its own top-level skill (symlinks)
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
dest="$HOME/.claude/skills"
flat=0
while [ $# -gt 0 ]; do
  case "$1" in
    --cursor) dest="$PWD/.cursor/skills" ;;
    --dir) dest="$2"; shift ;;
    --flat) flat=1 ;;
    -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 1 ;;
  esac
  shift
done
mkdir -p "$dest"
target="$dest/blender-master"
if [ -e "$target" ]; then
  backup="$target.bak.$(date +%Y%m%d%H%M%S)"
  echo "existing install moved to $backup"
  mv "$target" "$backup"
fi
cp -R "$here/blender-master" "$target"
find "$target" -name "__pycache__" -type d -prune -exec rm -rf {} +
if [ "$flat" = 1 ]; then
  for d in "$target"/subskills/*/; do
    name="$(basename "$d")"
    [ -e "$dest/$name" ] && { echo "skip $name (exists)"; continue; }
    ln -s "$d" "$dest/$name"
  done
fi
echo "installed: $target"
