#!/usr/bin/env bash

# If running on native Windows, re-exec this script under Git Bash if available.
# This is idempotent: if already running under Bash it does nothing.
if _dir="$(cd "$(dirname "$0")" >/dev/null 2>&1 && pwd)"; then
  _SCRIPT_DIR_HINT="$_dir"
else
  _SCRIPT_DIR_HINT="$(dirname "$0")"
fi
if _repo_root="$(cd "$_SCRIPT_DIR_HINT/.." >/dev/null 2>&1 && pwd)"; then
  REPO_ROOT="$_repo_root"
else
  REPO_ROOT="$_SCRIPT_DIR_HINT"
fi
WRAPPER="$REPO_ROOT/scripts/win-bash-wrapper.sh"
if [ -z "${BASH_VERSION-}" ]; then
  if [ -x "$WRAPPER" ]; then
    exec "$WRAPPER" "$0" "$@"
  elif command -v bash >/dev/null 2>&1; then
    exec bash "$0" "$@"
  fi
fi

# Ensure relative paths and module discovery resolve from repo root
cd "$REPO_ROOT" || {
  echo "Failed to cd to repo root: $REPO_ROOT" >&2
  exit 1
}

# Description: Generate UML class and package diagrams used in project documentation.
# Behavior:
#  - Uses `pyreverse` to emit DOT (or PNG fallback) files for classes and packages.
#  - Renders DOT -> SVG via `graphviz` (`dot`). If `dot` is unavailable, falls back to
#    PNG + ImageMagick `convert` + `potrace` to produce SVGs when possible.
#  - Outputs are written to `docs/reference/diagrams/` and intermediate files are cleaned.
#  - Exits non-zero when rendering fails so CI can detect the problem.

set -euo pipefail
shopt -s nullglob

mkdir -p docs/reference/diagrams
RENDER_FAILED=0
FAILED_TARGETS=()

generate_diagram() {
  local description="$1"
  local dotfile="$2"
  local out_svg="$3"
  local pngfile="$4"
  local pnmfile="$5"
  local fallback_label="$6"
  local failure_message="$7"
  shift 7
  local pyreverse_args=("$@")

  echo "Generating ${description}..."
  pyreverse "${pyreverse_args[@]}" -o dot

  if command -v dot >/dev/null 2>&1; then
    echo "Rendering ${dotfile} -> ${out_svg} with graphviz"
    dot -Tsvg "${dotfile}" -o "${out_svg}"
    echo "Wrote ${out_svg}"
    return
  fi

  echo "graphviz 'dot' not found, attempting PNG fallback for ${fallback_label}"
  pyreverse "${pyreverse_args[@]}" -o png

  # Defensive check: verify PNG was generated before proceeding
  if [ ! -s "${pngfile}" ]; then
    echo "${failure_message}" >&2
    RENDER_FAILED=1
    FAILED_TARGETS+=("${dotfile} -> ${out_svg}")
    return
  fi

  if command -v convert >/dev/null 2>&1 && command -v potrace >/dev/null 2>&1; then
    echo "Converting ${pngfile} -> ${pnmfile}..."
    convert "${pngfile}" "${pnmfile}"
    echo "Tracing ${pnmfile} -> ${out_svg} with potrace..."
    potrace -s -o "${out_svg}" "${pnmfile}"
    echo "Wrote ${out_svg}"
  else
    echo "${failure_message}" >&2
    RENDER_FAILED=1
    FAILED_TARGETS+=("${dotfile} -> ${out_svg}")
  fi
}

DOTFILE="classes_OctoPrint-Uptime.dot"
OUT_SVG="docs/reference/diagrams/classes.svg"
PNGFILE="classes_OctoPrint-Uptime.png"
PNMFILE="classes_OctoPrint-Uptime.pnm"
generate_diagram \
  "UML class diagram (include ancestors + associations + module names)" \
  "${DOTFILE}" \
  "${OUT_SVG}" \
  "${PNGFILE}" \
  "${PNMFILE}" \
  "compact diagram" \
  "Neither graphviz nor ImageMagick+potrace available; cannot render compact diagram" \
  -A -S -m y -p OctoPrint-Uptime octoprint_uptime

# detailed diagram (show private/protected and expanded details)
DOTFILE_D="classes_OctoPrint-Uptime-detailed.dot"
OUT_SVG_D="docs/reference/diagrams/classes_detailed.svg"
PNGFILE_D="classes_OctoPrint-Uptime-detailed.png"
PNMFILE_D="classes_OctoPrint-Uptime-detailed.pnm"
generate_diagram \
  "detailed class diagram (filter-mode=ALL)" \
  "${DOTFILE_D}" \
  "${OUT_SVG_D}" \
  "${PNGFILE_D}" \
  "${PNMFILE_D}" \
  "detailed diagram" \
  "Cannot render detailed diagram: missing graphviz and potrace/ImageMagick" \
  -f ALL -A -S -m y -p OctoPrint-Uptime-detailed octoprint_uptime

PKG_DOT="packages_OctoPrint-Uptime.dot"
PKG_OUT="docs/reference/diagrams/packages.svg"
PKG_PNG="packages_OctoPrint-Uptime.png"
PKG_PNM="packages_OctoPrint-Uptime.pnm"
generate_diagram \
  "packages diagram" \
  "${PKG_DOT}" \
  "${PKG_OUT}" \
  "${PKG_PNG}" \
  "${PKG_PNM}" \
  "packages diagram" \
  "Cannot render packages diagram: missing graphviz and potrace/ImageMagick" \
  -p OctoPrint-Uptime octoprint_uptime

# If any rendering failed above, print a concise summary and exit non-zero so CI
# or callers can detect the problem.
if [[ "${RENDER_FAILED}" -ne 0 ]]; then
  echo "Some diagram targets failed to render:" >&2
  for t in "${FAILED_TARGETS[@]}"; do
    echo " - ${t}" >&2
  done
  exit 2
fi

# Cleanup intermediate files produced by pyreverse (DOT/PNG/PNM)
echo "Cleaning up intermediate files..."
# Use an array of glob patterns so each pattern is preserved as an element
# and iterated safely. `nullglob` is enabled at the top of the script so
# patterns that match nothing expand to an empty list instead of themselves.
patterns=(classes_OctoPrint-Uptime*.{dot,png,pnm} packages_OctoPrint-Uptime*.{dot,png,pnm})
for f in "${patterns[@]}"; do
  rm -f -- "$f"
  echo "removed $f"
done
