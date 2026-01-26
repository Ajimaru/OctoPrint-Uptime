#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob

# Generate class/package diagrams for the docs.
# Primary path: pyreverse -> dot -> svg
# Fallback: pyreverse -> png -> potrace (requires ImageMagick + potrace)

mkdir -p docs/reference/diagrams

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
  if command -v pyreverse >/dev/null 2>&1; then
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
    fi
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
  fi
fi

echo "Generating packages diagram..."
pyreverse -o dot -p OctoPrint-Uptime octoprint_uptime
PKG_DOT="packages_OctoPrint-Uptime.dot"
PKG_OUT="docs/reference/diagrams/packages.svg"
if command -v dot >/dev/null 2>&1; then
  dot -Tsvg "${PKG_DOT}" -o "${PKG_OUT}"
  echo "Wrote ${PKG_OUT}"
fi

# Cleanup intermediate files produced by pyreverse (DOT/PNG/PNM)
echo "Cleaning up intermediate files..."
for f in classes_OctoPrint-Uptime*.dot classes_OctoPrint-Uptime*.png classes_OctoPrint-Uptime*.pnm packages_OctoPrint-Uptime*.dot packages_OctoPrint-Uptime*.png packages_OctoPrint-Uptime*.pnm; do
  if [ -e "$f" ]; then
    rm -f -- "$f"
    echo "removed $f"
  fi
done
