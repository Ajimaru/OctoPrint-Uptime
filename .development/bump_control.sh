#!/usr/bin/env bash
set -euo pipefail

# Clean, single-copy bump_control.sh
# - choose_menu: arrow keys + numeric + Enter fallback
# - version consistency check and RC handling

# ANSI colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

SCRIPT_PATH="${BASH_SOURCE[0]}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ "$PWD" != "$REPO_ROOT" ]]; then
    cd "$REPO_ROOT"
fi

usage() {
    cat <<EOF
Usage: $(basename "$0") [--config CONFIG] [BUMP_TYPE] [NEW_CURRENT] [COMMIT] [TAG] [--execute]

Interactive helper to update bump-my-version config and run a bump.

Options:
  --config CONFIG  Path to bump config file (default: .development/bumpversion.toml)
  --silent         Disable verbose output (overrides default -vv)
  --execute        Run the real bump; otherwise runs a dry-run

Examples:
  $(basename "$0")                # interactive mode
EOF
}

choose_menu() {
    local prompt="$1"; shift
    local options=("$@")
    local count=${#options[@]}
    local idx=0

    printf "%b\n" "${BOLD}${prompt}${RESET}" >&2
    for i in "${!options[@]}"; do
        if [[ $i -eq $idx ]]; then
            printf "  %d) \e[7m%s\e[0m\n" $((i+1)) "${options[i]}" >&2
        else
            printf "  %d) %s\n" $((i+1)) "${options[i]}" >&2
        fi
    done
    printf "%b\n" "Use ↑/↓ or number keys; Enter confirms current; q cancels." >&2

    if [[ ! -t 0 ]]; then
        printf "Enter number [1-%d]: " "$count" >&2
        read -r num || true
        if [[ "$num" =~ ^[0-9]+$ ]] && (( num>=1 && num<=count )); then
            CHOSEN="${options[num-1]}"
            printf "%s" "$CHOSEN"
            return 0
        else
            printf "%b\n" "${RED}Invalid selection.${RESET}" >&2
            return 1
        fi
    fi

    local lines_to_move=$((count + 2))
    while true; do
        read -r -n1 -s key || true
        if [[ $key == $'\x1b' ]]; then
            read -r -n2 -s rest || true
            key+=$rest
        fi
        case "$key" in
            $'\x1b[A') idx=$(( (idx-1+count) % count )) ;;
            $'\x1b[B') idx=$(( (idx+1) % count )) ;;
            [1-9])
                num=$key
                if (( num>=1 && num<=count )); then
                    CHOSEN="${options[num-1]}"
                    printf "%s\n" "$CHOSEN"
                    return 0
                fi
                ;;
            '')
                CHOSEN="${options[idx]}"
                printf "%s\n" "$CHOSEN"
                return 0
                ;;
            $'\n'|$'\r') CHOSEN="${options[idx]}"; printf "%s\n" "$CHOSEN"; return 0 ;;
            q) return 1 ;;
            *) ;; # ignore
        esac

        printf "\e[%dA" "$lines_to_move" >&2
        printf "%b\n" "${BOLD}${prompt}${RESET}" >&2
        for i in "${!options[@]}"; do
            if [[ $i -eq $idx ]]; then
                printf "  %d) \e[7m%s\e[0m\n" $((i+1)) "${options[i]}" >&2
            else
                printf "  %d) %s\n" $((i+1)) "${options[i]}" >&2
            fi
        done
        printf "%b\n" "Use ↑/↓ or number keys; Enter confirms current; q cancels." >&2
    done
}

check_versions_consistent() {
    local config_file="$1"
    local config_version py_version toml_version
    config_version=$(grep -E '^current_version[[:space:]]*=' "$config_file" | sed -E 's/.*=\s*"([^\"]+)".*/\1/' || true)
    py_version=$(grep -E '^VERSION[[:space:]]*=' octoprint_uptime/_version.py | sed -E 's/.*=\s*"([^\"]+)".*/\1/' || true)
    toml_version=$(grep -E '^version[[:space:]]*=' pyproject.toml | sed -E 's/.*=\s*"([^\"]+)".*/\1/' || true)

    local versions=()
    for v in "$config_version" "$py_version" "$toml_version"; do
        [[ -n "$v" ]] && versions+=("$v")
    done
    local uniq_versions=($(printf "%s\n" "${versions[@]}" | sort -u))

    if (( ${#uniq_versions[@]} > 1 )); then
        printf "%b\n" "${YELLOW}WARNING: Version mismatch detected!${RESET}"
        printf "%b\n" "  ${CYAN}bumpversion.toml:${RESET} $config_version"
        printf "%b\n" "  ${CYAN}_version.py:${RESET}      $py_version"
        printf "%b\n" "  ${CYAN}pyproject.toml:${RESET}   $toml_version"
        printf "\n"
        local opts=("${uniq_versions[@]}" "Abort")
        choose_menu "Choose version or Abort:" "${opts[@]}"
        if [[ $? -ne 0 ]]; then printf "%b\n" "${RED}Aborted by user.${RESET}"; exit 1; fi
        local chosen="$CHOSEN"
        if [[ "$chosen" == "Abort" ]]; then printf "%b\n" "${RED}Aborted by user due to version mismatch.${RESET}"; exit 1; fi
        printf "%b\n" "Setting all files to version: ${GREEN}$chosen${RESET}"
        sed -E -i "s/^current_version[[:space:]]*=[[:space:]]*\"[^\"]+\"/current_version = \"$chosen\"/" "$config_file"
        sed -E -i "s/VERSION = \"[^\"]+\"/VERSION = \"$chosen\"/" octoprint_uptime/_version.py
        sed -E -i "s/^version[[:space:]]*=[[:space:]]*\"[^\"]+\"/version = \"$chosen\"/" pyproject.toml
    fi
}

update_toml() {
    local key="$1" val="$2" file="$3"
    if [[ -z "$val" ]]; then return; fi
    if [[ "$val" =~ ^(true|false)$ ]]; then
        sed -E -i "s/^[[:space:]]*$key[[:space:]]*=.*/$key = $val/" "$file"
    else
        sed -E -i "s/^[[:space:]]*$key[[:space:]]*=.*/$key = \"$val\"/" "$file"
    fi
}

# Defaults
CONFIG=""
BUMP_TYPE=
NEW_CURRENT=
COMMIT=
TAG=
EXECUTE=0
VERBOSE_FLAGS=("-vv")

while [[ $# -gt 0 ]]; do
    case $1 in
        --silent) VERBOSE_FLAGS=(); shift ;;
        --config) CONFIG="$2"; shift 2 ;;
        --execute) EXECUTE=1; shift ;;
        -*) echo "Unknown option: $1" >&2; usage; exit 1 ;;
        *)
            if [[ -z "$BUMP_TYPE" ]]; then
                BUMP_TYPE="$1"
            elif [[ -z "$NEW_CURRENT" ]]; then
                NEW_CURRENT="$1"
            elif [[ -z "$COMMIT" ]]; then
                COMMIT="$1"
            elif [[ -z "$TAG" ]]; then
                TAG="$1"
            fi
            shift
            ;;
    esac
done

if [[ -z "$CONFIG" ]]; then CONFIG=".development/bumpversion.toml"; fi

if [[ -z "$BUMP_TYPE" ]]; then
    if [[ -f "octoprint_uptime/_version.py" ]]; then
        CURRENT_VERSION=$(grep -E "^VERSION\s*=" octoprint_uptime/_version.py | sed -E 's/.*"([^\"]+)".*/\1/')
    else
        CURRENT_VERSION=""
    fi
    CURRENT_VERSION="$(printf '%s' "$CURRENT_VERSION" | tr -d '\r' | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
    printf "%b\n" "Current package version: ${CYAN}${CURRENT_VERSION:-(unknown)}${RESET}"

    choose_menu "Select bump type:" major minor bug rc cancel
    if [[ $? -ne 0 ]]; then printf "%b\n" "${RED}Cancelled.${RESET}"; exit 1; fi
    CHOICE="$CHOSEN"
    case "$CHOICE" in
        major) BUMP_TYPE=major ;;
        minor) BUMP_TYPE=minor ;;
        bug) BUMP_TYPE=patch ;;
        rc) BUMP_TYPE=rc ;;
        cancel) printf "%b\n" "${RED}Aborted.${RESET}"; exit 0 ;;
        *) printf "%b\n" "${RED}Invalid choice.${RESET}"; exit 1 ;;
    esac

    read -r -p "Create a commit after bump? [y/N] " ans_commit
    ans_commit=${ans_commit:-N}
    if [[ "$ans_commit" =~ ^[Yy] ]]; then COMMIT=true; else COMMIT=false; fi

    read -r -p "Create a tag after bump? [y/N] " ans_tag
    ans_tag=${ans_tag:-N}
    if [[ "$ans_tag" =~ ^[Yy] ]]; then TAG=true; else TAG=false; fi

    read -r -p "Perform actual bump (real run) or preview (dry-run)? [d/dry, r/real] " ans_run
    if [[ "$ans_run" =~ ^[Rr] ]]; then EXECUTE=1; else EXECUTE=0; fi

    if [[ "$BUMP_TYPE" == "rc" ]]; then
        if [[ -n "$CURRENT_VERSION" && "$CURRENT_VERSION" =~ rc([0-9]+)$ ]]; then
            base=${CURRENT_VERSION%rc*}
            num=${BASH_REMATCH[1]}
            next=$((num+1))
            NEW_CURRENT="${base}rc${next}"
        elif [[ -n "$CURRENT_VERSION" && ! "$CURRENT_VERSION" =~ rc ]]; then
            NEW_CURRENT="${CURRENT_VERSION}rc1"
        else
            NEW_CURRENT=""
        fi
        if [[ -z "$NEW_CURRENT" ]]; then
            read -r -p "Enter RC version to set (e.g. 0.2.0rc1): " NEW_CURRENT
            if [[ -z "$NEW_CURRENT" ]]; then printf "%b\n" "${RED}No version provided, aborting.${RESET}"; exit 1; fi
        else
            printf "%b\n" "Auto-selected RC version: ${GREEN}$NEW_CURRENT${RESET}"
            read -r -p "Accept this version? [Y/n] " accept_rc
            accept_rc=${accept_rc:-Y}
            if [[ ! "$accept_rc" =~ ^[Yy] ]]; then
                read -r -p "Enter RC version to set (e.g. 0.2.0rc1): " NEW_CURRENT
                if [[ -z "$NEW_CURRENT" ]]; then printf "%b\n" "${RED}No version provided, aborting.${RESET}"; exit 1; fi
            fi
        fi
    fi
fi

if [[ -x "${REPO_ROOT}/venv/bin/bump-my-version" ]]; then BUMP_CMD="${REPO_ROOT}/venv/bin/bump-my-version"; else BUMP_CMD="bump-my-version"; fi

echo "Using config: $CONFIG"

if [[ "$BUMP_TYPE" == "rc" ]]; then
    printf "%b\n" "RC mode: will set version to ${GREEN}$NEW_CURRENT${RESET} in known files"
    printf "%b\n" "Preview of changes (first 50 lines of config):"
    sed -n '1,50p' "$CONFIG" || true
    if [[ $EXECUTE -eq 0 ]]; then
        printf "%b\n" "DRY-RUN: Files that would be updated:"
        echo "  - octoprint_uptime/_version.py"
        echo "  - setup.py"
        echo "  - pyproject.toml"
        echo "  - $CONFIG (current_version)"
        printf "%b\n" "New version: ${GREEN}$NEW_CURRENT${RESET}"
        exit 0
    fi
    sed -E -i "s/VERSION = \"[^\"]+\"/VERSION = \"$NEW_CURRENT\"/" octoprint_uptime/_version.py
    sed -E -i "s/version[[:space:]]*=[[:space:]]*\"[^\"]+\"/version = \"$NEW_CURRENT\"/" pyproject.toml
    sed -E -i "s/^current_version[[:space:]]*=[[:space:]]*\"[^\"]+\"/current_version = \"$NEW_CURRENT\"/" "$CONFIG"

    if [[ "$COMMIT" == "true" ]]; then
        git add octoprint_uptime/_version.py pyproject.toml "$CONFIG"
        git commit -m "Bump version to $NEW_CURRENT"
    fi
    if [[ "$TAG" == "true" ]]; then
        git tag "$NEW_CURRENT"
    fi
    printf "%b\n" "RC bump completed."
    exit 0
else
    if [[ ! -f "$CONFIG" ]]; then printf "%b\n" "${RED}Config file '$CONFIG' not found.${RESET}" >&2; usage; exit 1; fi
    if [[ -n "$NEW_CURRENT" ]]; then printf "%b\n" "Setting current_version => ${GREEN}$NEW_CURRENT${RESET} in $CONFIG"; update_toml "current_version" "$NEW_CURRENT" "$CONFIG"; fi
    if [[ -n "$COMMIT" ]]; then printf "%b\n" "Setting commit => $COMMIT in $CONFIG"; update_toml "commit" "$COMMIT" "$CONFIG"; fi
    if [[ -n "$TAG" ]]; then printf "%b\n" "Setting tag => $TAG in $CONFIG"; update_toml "tag" "$TAG" "$CONFIG"; fi
    check_versions_consistent "$CONFIG"
    printf "%b\n" "Prepared config. Preview (first 50 lines):"
    sed -n '1,50p' "$CONFIG" || true
    if [[ $EXECUTE -eq 1 ]]; then
        run_type="actual run"
    else
        run_type="dry-run"
    fi
    read -r -p "Proceed with $run_type bump ($BUMP_TYPE)? [Y/n] " ans
    ans=${ans:-Y}
    if [[ ! "$ans" =~ ^[Yy] ]]; then printf "%b\n" "${RED}Aborted by user.${RESET}"; exit 0; fi
    CMD=("$BUMP_CMD" "${VERBOSE_FLAGS[@]}" bump "$BUMP_TYPE" --config "$CONFIG")
    if [[ $EXECUTE -eq 0 ]]; then CMD+=(--dry-run); fi
    printf "%b\n" "Running: ${CYAN}${CMD[*]}${RESET}"
    "${CMD[@]}"
    if [[ $EXECUTE -eq 0 ]]; then
        printf "%b\n" "Done (dry-run). Note: remove --dry-run (use --execute) to perform real bump."
    else
        printf "%b\n" "Done."
    fi
fi
