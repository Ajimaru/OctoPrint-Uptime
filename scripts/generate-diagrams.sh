#!/usr/bin/env bash

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

echo "Generating UML DOT with pyreverse (include ancestors + associations + module names)..."
pyreverse -A -S -m y -o dot -p OctoPrint-Uptime octoprint_uptime
DOTFILE="classes_OctoPrint-Uptime.dot"
OUT_SVG="docs/reference/diagrams/classes.svg"

if command -v dot >/dev/null 2>&1; then
  echo "Rendering ${DOTFILE} -> ${OUT_SVG} with graphviz"
  dot -Tsvg "${DOTFILE}" -o "${OUT_SVG}"
  echo "Wrote ${OUT_SVG}"
else
  echo "graphviz 'dot' not found — trying PNG fallback for compact diagram"
  pyreverse -A -S -m y -o png -p OctoPrint-Uptime octoprint_uptime
  PNGFILE="classes_OctoPrint-Uptime.png"
  PNMFILE="classes_OctoPrint-Uptime.pnm"
  if command -v convert >/dev/null 2>&1 && command -v potrace >/dev/null 2>&1; then
    echo "Converting ${PNGFILE} -> ${PNMFILE}..."
    convert "${PNGFILE}" "${PNMFILE}"
    echo "Tracing ${PNMFILE} -> ${OUT_SVG} with potrace..."
    potrace -s -o "${OUT_SVG}" "${PNMFILE}"
    echo "Wrote ${OUT_SVG}"
  else
    echo "Neither graphviz nor ImageMagick+potrace available; cannot render compact diagram" >&2
    RENDER_FAILED=1
    FAILED_TARGETS+=("${DOTFILE} -> ${OUT_SVG}")
  fi
fi

# detailed diagram (show private/protected and expanded details)
echo "Generating detailed class diagram (filter-mode=ALL)..."
pyreverse -f ALL -A -S -m y -o dot -p OctoPrint-Uptime-detailed octoprint_uptime
DETAILED_DOT="classes_OctoPrint-Uptime-detailed.dot"
DETAILED_OUT="docs/reference/diagrams/classes_detailed.svg"
if command -v dot >/dev/null 2>&1; then
  dot -Tsvg "${DETAILED_DOT}" -o "${DETAILED_OUT}"
  echo "Wrote ${DETAILED_OUT}"
else
  echo "graphviz 'dot' not found — attempting PNG fallback for detailed diagram"
  pyreverse -f ALL -A -S -m y -o png -p OctoPrint-Uptime-detailed octoprint_uptime
  PNGFILE_D="classes_OctoPrint-Uptime-detailed.png"
  PNMFILE_D="classes_OctoPrint-Uptime-detailed.pnm"
  if command -v convert >/dev/null 2>&1 && command -v potrace >/dev/null 2>&1; then
    convert "${PNGFILE_D}" "${PNMFILE_D}"
    potrace -s -o "${DETAILED_OUT}" "${PNMFILE_D}"
    echo "Wrote ${DETAILED_OUT}"
  else
    echo "Cannot render detailed diagram: missing graphviz and potrace/ImageMagick" >&2
    RENDER_FAILED=1
    FAILED_TARGETS+=("${DETAILED_DOT} -> ${DETAILED_OUT}")
  fi
fi

echo "Generating packages diagram..."
pyreverse -o dot -p OctoPrint-Uptime octoprint_uptime
PKG_DOT="packages_OctoPrint-Uptime.dot"
PKG_OUT="docs/reference/diagrams/packages.svg"
if command -v dot >/dev/null 2>&1; then
  dot -Tsvg "${PKG_DOT}" -o "${PKG_OUT}"
  echo "Wrote ${PKG_OUT}"
else
  echo "graphviz 'dot' not found — attempting PNG fallback for packages diagram"
  pyreverse -o png -p OctoPrint-Uptime octoprint_uptime
  PKG_PNG="packages_OctoPrint-Uptime.png"
  PKG_PNM="packages_OctoPrint-Uptime.pnm"
  if command -v convert >/dev/null 2>&1 && command -v potrace >/dev/null 2>&1; then
    convert "${PKG_PNG}" "${PKG_PNM}"
    potrace -s -o "${PKG_OUT}" "${PKG_PNM}"
    echo "Wrote ${PKG_OUT}"
  else
    echo "Cannot render packages diagram: missing graphviz and potrace/ImageMagick" >&2
    RENDER_FAILED=1
    FAILED_TARGETS+=("${PKG_DOT} -> ${PKG_OUT}")
  fi
fi

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
  if [ -e "$f" ]; then
    rm -f -- "$f"
    echo "removed $f"
  fi
done

