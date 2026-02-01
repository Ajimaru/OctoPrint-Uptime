#!/usr/bin/env bash

# If running on native Windows, re-exec this script under Git Bash if available.
# This is idempotent: if already running under Bash it does nothing.
_SCRIPT_DIR_HINT="$(cd "$(dirname "$0")" >/dev/null 2>&1 && pwd || dirname "$0")"
REPO_ROOT="$(cd "$_SCRIPT_DIR_HINT/.." >/dev/null 2>&1 && pwd || echo "$_SCRIPT_DIR_HINT")"
WRAPPER="$REPO_ROOT/scripts/win-bash-wrapper.sh"
if [ -z "${BASH_VERSION-}" ]; then
    if [ -x "$WRAPPER" ]; then
        exec "$WRAPPER" "$0" "$@"
    elif command -v bash >/dev/null 2>&1; then
        exec bash "$0" "$@"
    fi
fi

# Description: Interactive helper to choose and apply version bumps across the project.
# Behavior:
#  - Provides interactive selection of bump types (dev, rc, major, minor, patch) and
#    computes suggested new versions when possible.
#  - Checks and reconciles versions in the bump config, `octoprint_uptime/_version.py`,
#    and `pyproject.toml`, offering to synchronize them when mismatches are found.
#  - Supports dry-run vs real execution, creating commits and tags when requested,
#    and can trigger a post-commit distribution build helper.
# Usage examples:
#  - Run interactively: ./.development/bump_control.sh
#  - Non-interactive: ./.development/bump_control.sh minor 1.2.0 true true --execute

set -euo pipefail

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

to_pep440() {
    # Convert a developer-suffixed version (".dev") to PEP 440 ".dev" form.
    # Accepts a single version string argument and writes the converted
    # version to stdout so callers can use: result="$(to_pep440 "$ver")".
    # Note: Already using dot notation, so no conversion needed
    local ver="${1:-}"
    printf '%s' "${ver}"
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

    local config_version_norm py_version_norm toml_version_norm
    config_version_norm=$(to_pep440 "${config_version:-}")
    py_version_norm=$(to_pep440 "${py_version:-}")
    toml_version_norm=$(to_pep440 "${toml_version:-}")

    local versions=()
    for v in "$config_version_norm" "$py_version_norm" "$toml_version_norm"; do
        [[ -n "$v" ]] && versions+=("$v")
    done
    readarray -t uniq_versions < <(printf "%s\n" "${versions[@]}" | sort -u)

    if (( ${#uniq_versions[@]} > 1 )); then
        printf "%b\n" "${YELLOW}WARNING: Version mismatch detected!${RESET}"
        printf "%b\n" "  ${CYAN}bumpversion.toml:${RESET} $config_version"
        printf "%b\n" "  ${CYAN}_version.py:${RESET}      $py_version"
        printf "%b\n" "  ${CYAN}pyproject.toml:${RESET}   $toml_version"
        printf "\n"
        local opts=("${uniq_versions[@]}" "Abort")
        if ! choose_menu "Choose version or Abort:" "${opts[@]}"; then
            printf "%b\n" "${RED}Aborted by user.${RESET}"
            exit 1
        fi
        local chosen="$CHOSEN"
        if [[ "$chosen" == "Abort" ]]; then printf "%b\n" "${RED}Aborted by user due to version mismatch.${RESET}"; exit 1; fi
        printf "%b\n" "Setting all files to version: ${GREEN}$chosen${RESET}"
        sed -E -i "s/^current_version[[:space:]]*=[[:space:]]*\"[^\"]+\"/current_version = \"$chosen\"/" "$config_file"
        sed -E -i "s/VERSION = \"[^\"]+\"/VERSION = \"$chosen\"/" octoprint_uptime/_version.py
        # Use PEP 440 compatible dev separator in pyproject.toml (0.1.0.dev35)
        py_ver="$(to_pep440 "$chosen")"
        sed -E -i "s/^version[[:space:]]*=[[:space:]]*\"[^\"]+\"/version = \"$py_ver\"/" pyproject.toml
    fi
}

update_toml() {
    local key="$1" val="$2" file="$3"
    if [[ -z "$val" ]]; then return; fi
    if [[ "$val" =~ ^(true|false)$ ]]; then
        sed -E -i "s/^[[:space:]]*${key}[[:space:]]*=.*/${key} = $val/" "$file"
    else
        sed -E -i "s/^[[:space:]]*${key}[[:space:]]*=.*/${key} = \"$val\"/" "$file"
    fi
}

run_post_commit_build() {
    local run_post
    # If dist artifacts for the new version already exist (post-commit hook ran),
    # skip asking/running the build script again.
    if [[ -n "${NEW_CURRENT:-}" ]]; then
        local normalized
        normalized="${NEW_CURRENT//-/.}"
        shopt -s nullglob nocaseglob
        local candidates=(dist/*"${NEW_CURRENT}"*.tar.gz dist/*"${NEW_CURRENT}"*.tgz dist/*"${NEW_CURRENT}"*.whl dist/*"${normalized}"*.tar.gz dist/*"${normalized}"*.tgz dist/*"${normalized}"*.whl dist/*"${normalized}"*.zip)
        shopt -u nullglob nocaseglob
        if (( ${#candidates[@]} > 0 )); then
            printf "%b
" "[OctoPrint-Uptime] Detected dist artifacts for ${GREEN}${NEW_CURRENT}${RESET}; skipping post-commit build." >&2
            return 0
        fi
    fi
    if [[ -t 0 ]]; then
        read -r -p "Run .development/post_commit_build_dist.sh now? [Y/n] " run_post
        run_post=${run_post:-Y}
    else
        run_post=Y
    fi

    if [[ "$run_post" =~ ^[Yy] ]]; then
        local -a cmd
        if [[ -x ".development/post_commit_build_dist.sh" ]]; then
            cmd=( "./.development/post_commit_build_dist.sh" )
        else
            cmd=( "bash" ".development/post_commit_build_dist.sh" )
        fi

        if ! "${cmd[@]}"; then
            printf "%b\n" "Warning: .development/post_commit_build_dist.sh exited with an error." >&2
        fi
    fi
}

# Defaults
CONFIG=""
BUMP_TYPE=
NEW_CURRENT=
COMMIT=
TAG=
EXECUTE=0
VERBOSE_FLAGS=()

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

    if ! choose_menu "Select bump type:" dev rc major minor bug cancel; then
        printf "%b\n" "${RED}Cancelled.${RESET}"
        exit 1
    fi
    CHOICE="$CHOSEN"
    case "$CHOICE" in
        dev) BUMP_TYPE=dev ;;
        rc) BUMP_TYPE=rc ;;
        major) BUMP_TYPE=major ;;
        minor) BUMP_TYPE=minor ;;
        bug)
            BUMP_TYPE="patch"
            ;;
        cancel) printf "%b\n" "${RED}Aborted.${RESET}"; exit 0 ;;
        *) printf "%b\n" "${RED}Invalid choice.${RESET}"; exit 1 ;;
    esac

    BUMP_CANDIDATE_CMD="${REPO_ROOT}/venv/bin/bump-my-version"
    if [[ ! -x "$BUMP_CANDIDATE_CMD" ]]; then
        BUMP_CANDIDATE_CMD="bump-my-version"
    fi
    if [[ "$BUMP_TYPE" != "rc" && "$BUMP_TYPE" != "dev" ]]; then
        NEW_GUESS=""
        if command -v "$BUMP_CANDIDATE_CMD" >/dev/null 2>&1; then
            NEW_GUESS=$("$BUMP_CANDIDATE_CMD" show-bump --config-file "$CONFIG" --current-version "${CURRENT_VERSION:-}" "$BUMP_TYPE" 2>/dev/null || true)
            NEW_GUESS=$(printf '%s' "$NEW_GUESS" | sed -n '1p' | awk '{print $NF}')
        fi
        if [[ -z "$NEW_GUESS" ]]; then
            local_ver="${CURRENT_VERSION:-0.0.0}"
            local_ver=$(printf '%s' "$local_ver" | tr -d '\r' | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')
            if [[ "$local_ver" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)([.-]?([a-zA-Z]+)([0-9]+))?$ ]]; then
                major=${BASH_REMATCH[1]}
                minor=${BASH_REMATCH[2]}
                patch=${BASH_REMATCH[3]}
                _suffix=${BASH_REMATCH[4]:-}
                _suftype=${BASH_REMATCH[5]:-}
                _sufnum=${BASH_REMATCH[6]:-}
                case "$BUMP_TYPE" in
                    major)
                        major=$((major+1)); minor=0; patch=0; NEW_GUESS="$major.$minor.$patch" ;;
                    minor)
                        minor=$((minor+1)); patch=0; NEW_GUESS="$major.$minor.$patch" ;;
                    patch|bug)
                        patch=$((patch+1)); NEW_GUESS="$major.$minor.$patch" ;;
                    *) NEW_GUESS="" ;;
                esac
            fi
        fi
        if [[ -n "$NEW_GUESS" ]]; then
            NEW_CURRENT="$NEW_GUESS"
            printf "%b\n" "Selected bump: ${GREEN}$BUMP_TYPE${RESET} → new version: ${CYAN}$NEW_CURRENT${RESET}"
        fi
    fi

    read -r -p "Create a commit after bump? [Y/n] " ans_commit
    ans_commit=${ans_commit:-Y}
    if [[ "$ans_commit" =~ ^[Yy] ]]; then COMMIT=true; else COMMIT=false; fi

    read -r -p "Create a tag after bump? [y/N] " ans_tag
    ans_tag=${ans_tag:-N}
    if [[ "$ans_tag" =~ ^[Yy] ]]; then TAG=true; else TAG=false; fi

    read -r -p "Perform actual bump (real run) or preview (dry-run)? [d/dry, R/real] " ans_run
    ans_run=${ans_run:-R}
    if [[ "$ans_run" =~ ^[Rr] ]]; then
        EXECUTE=1
    else
        EXECUTE=0
    fi

    if [[ "$BUMP_TYPE" == "rc" ]]; then
        if [[ -n "$CURRENT_VERSION" && "$CURRENT_VERSION" =~ \.dev([0-9]+)$ ]]; then
            base=${CURRENT_VERSION%.dev*}
            NEW_CURRENT="${base}.rc1"
        elif [[ -n "$CURRENT_VERSION" && "$CURRENT_VERSION" =~ dev([0-9]+)$ ]]; then
            base=${CURRENT_VERSION%dev*}
            NEW_CURRENT="${base}.rc1"
        elif [[ -n "$CURRENT_VERSION" && "$CURRENT_VERSION" =~ \.rc([0-9]+)$ ]]; then
            base=${CURRENT_VERSION%.rc*}
            num=${BASH_REMATCH[1]}
            next=$((num+1))
            NEW_CURRENT="${base}.rc${next}"
        elif [[ -n "$CURRENT_VERSION" && "$CURRENT_VERSION" =~ rc([0-9]+)$ ]]; then
            base=${CURRENT_VERSION%rc*}
            num=${BASH_REMATCH[1]}
            next=$((num+1))
            NEW_CURRENT="${base}.rc${next}"
        elif [[ -n "$CURRENT_VERSION" && ! "$CURRENT_VERSION" =~ rc ]]; then
            NEW_CURRENT="${CURRENT_VERSION}.rc1"
        else
            NEW_CURRENT=""
        fi
        if [[ -z "$NEW_CURRENT" ]]; then
            read -r -p "Enter RC version to set (e.g. 0.2.0.rc1): " NEW_CURRENT
            if [[ -z "$NEW_CURRENT" ]]; then printf "%b\n" "${RED}No version provided, aborting.${RESET}"; exit 1; fi
        else
            printf "%b\n" "Auto-selected RC version: ${GREEN}$NEW_CURRENT${RESET}"
            read -r -p "Accept this version? [Y/n] " accept_rc
            accept_rc=${accept_rc:-Y}
            if [[ ! "$accept_rc" =~ ^[Yy] ]]; then
                read -r -p "Enter RC version to set (e.g. 0.2.0.rc1): " NEW_CURRENT
                if [[ -z "$NEW_CURRENT" ]]; then printf "%b\n" "${RED}No version provided, aborting.${RESET}"; exit 1; fi
            fi
        fi
    fi

    if [[ "$BUMP_TYPE" == "dev" ]]; then
        if [[ -n "$CURRENT_VERSION" && "$CURRENT_VERSION" =~ \.rc([0-9]+)$ ]]; then
            base=${CURRENT_VERSION%.rc*}
            NEW_CURRENT="${base}.dev1"
        elif [[ -n "$CURRENT_VERSION" && "$CURRENT_VERSION" =~ rc([0-9]+)$ ]]; then
            base=${CURRENT_VERSION%rc*}
            NEW_CURRENT="${base}.dev1"
        elif [[ -n "$CURRENT_VERSION" && "$CURRENT_VERSION" =~ \.dev([0-9]+)$ ]]; then
            base=${CURRENT_VERSION%.dev*}
            num=${BASH_REMATCH[1]}
            next=$((num+1))
            NEW_CURRENT="${base}.dev${next}"
        elif [[ -n "$CURRENT_VERSION" && "$CURRENT_VERSION" =~ dev([0-9]+)$ ]]; then
            base=${CURRENT_VERSION%dev*}
            num=${BASH_REMATCH[1]}
            next=$((num+1))
            NEW_CURRENT="${base}.dev${next}"
        elif [[ -n "$CURRENT_VERSION" && ! "$CURRENT_VERSION" =~ dev ]]; then
            NEW_CURRENT="${CURRENT_VERSION}.dev1"
        else
            NEW_CURRENT=""
        fi
        if [[ -z "$NEW_CURRENT" ]]; then
            read -r -p "Enter $BUMP_TYPE version to set (e.g. 0.2.0.${BUMP_TYPE}1): " NEW_CURRENT
            if [[ -z "$NEW_CURRENT" ]]; then printf "%b\n" "${RED}No version provided, aborting.${RESET}"; exit 1; fi
        else
            printf "%b\n" "Auto-selected $BUMP_TYPE version: ${GREEN}$NEW_CURRENT${RESET}"
            read -r -p "Accept this version? [Y/n] " accept_pre
            accept_pre=${accept_pre:-Y}
            if [[ ! "$accept_pre" =~ ^[Yy] ]]; then
                read -r -p "Enter $BUMP_TYPE version to set (e.g. 0.2.0.${BUMP_TYPE}1): " NEW_CURRENT
                if [[ -z "$NEW_CURRENT" ]]; then printf "%b\n" "${RED}No version provided, aborting.${RESET}"; exit 1; fi
            fi
        fi
        printf "%b\n" "$BUMP_TYPE mode: will set version to ${GREEN}$NEW_CURRENT${RESET} in known files"
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
        # Version already uses dot notation (PEP 440 compatible)
        sed -E -i "s/version[[:space:]]*=[[:space:]]*\"[^\"]+\"/version = \"$NEW_CURRENT\"/" pyproject.toml
        sed -E -i "s/^current_version[[:space:]]*=[[:space:]]*\"[^\"]+\"/current_version = \"$NEW_CURRENT\"/" "$CONFIG"
        if [[ "$COMMIT" == "true" ]]; then
            git add octoprint_uptime/_version.py pyproject.toml "$CONFIG"
            git commit -m "Bump version to $NEW_CURRENT"
        fi
        if [[ "$TAG" == "true" ]]; then
            git tag "$NEW_CURRENT"
        fi
        printf "%b\n" "$BUMP_TYPE bump completed."

        run_post_commit_build
        exit 0
    fi
    if [[ -n "$COMMIT" ]]; then
        printf "%b\n" "Would set commit => $COMMIT in $CONFIG"
    fi
    if [[ -n "$TAG" ]]; then
        printf "%b\n" "Would set tag => $TAG in $CONFIG"
    fi
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
    if [[ $EXECUTE -eq 1 ]]; then
        if [[ -n "$COMMIT" ]]; then
            printf "%b\n" "Setting commit => $COMMIT in $CONFIG"
            update_toml "commit" "$COMMIT" "$CONFIG"
        fi
        if [[ -n "$TAG" ]]; then
            printf "%b\n" "Setting tag => $TAG in $CONFIG"
            update_toml "tag" "$TAG" "$CONFIG"
        fi
    fi

    BUMP_CMD="${REPO_ROOT}/venv/bin/bump-my-version"
    if [[ ! -x "${BUMP_CMD}" ]]; then
        BUMP_CMD="bump-my-version"
    fi

    CMD=("$BUMP_CMD" "${VERBOSE_FLAGS[@]}" bump "$BUMP_TYPE" --config-file "$CONFIG")
    if [[ -f "octoprint_uptime/_version.py" ]]; then
        CURRENT_VERSION=$(grep -E "^VERSION\s*=" octoprint_uptime/_version.py | sed -E 's/.*"([^\"]+)".*/\1/' || true)
        CURRENT_VERSION="$(printf '%s' "$CURRENT_VERSION" | tr -d '\r' | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
    fi
    if [[ -n "${CURRENT_VERSION:-}" ]]; then
        CMD+=(--current-version "$CURRENT_VERSION")
    fi
    if [[ -n "$NEW_CURRENT" ]]; then
        CMD+=(--new-version "$NEW_CURRENT")
    fi
    if [[ $EXECUTE -eq 0 ]]; then
        CMD+=(--dry-run --allow-dirty)
    fi
    # If executing for real, ensure git working tree is acceptable
    if [[ $EXECUTE -eq 1 ]]; then
        unstaged=$(git status --porcelain 2>/dev/null || true)
        if [[ -n "$unstaged" ]]; then
            printf "%b\n" "${YELLOW}Git working directory appears dirty:${RESET}"
            printf "%s\n" "$unstaged"
            printf "%b\n" "Choose action: [c]ommit local changes now, [d]o it anyway (pass --allow-dirty), [a]bort"
            read -r -p "Action [a/c/d]? " action
            action=${action:-a}
            case "$action" in
                c)
                    printf "%b\n" "${YELLOW}Preview of changes to be staged and committed:${RESET}"
                    git add -u
                    staged=$(git diff --name-only --staged 2>/dev/null || true)
                    if [[ -n "$staged" ]]; then
                        printf "%s\n" "$staged"
                    else
                        printf "%b\n" "${YELLOW}No tracked modifications to stage.${RESET}"
                    fi
                    printf "\n"
                    read -r -p "Commit these changes? [y/N] " commit_confirm
                    commit_confirm=${commit_confirm:-N}
                    if [[ "$commit_confirm" =~ ^[Yy] ]]; then
                        git commit -m "Prepare bump: commit local modifications before bump"
                        printf "%b\n" "${GREEN}Changes committed.${RESET}"
                    else
                        printf "%b\n" "${YELLOW}Commit cancelled. Resetting staged changes.${RESET}"
                        git reset HEAD
                        exit 1
                    fi
                    ;;
                d)
                    CMD+=(--allow-dirty)
                    ;;
                *)
                    printf "%b\n" "Aborted due to dirty working tree." >&2
                    exit 1
                    ;;
            esac
        fi
    fi

    printf "%b\n" "Running: ${CYAN}${CMD[*]}${RESET}"
    "${CMD[@]}"
    if [[ $EXECUTE -eq 1 && -n "${NEW_CURRENT:-}" ]]; then
        update_toml "current_version" "$NEW_CURRENT" "$CONFIG" || true
    fi
    # After bumping, normalize pyproject.toml to use PEP 440 '.dev' for dev
    # versions so tooling that expects PEP 440 sees the correct form.
    if [[ $EXECUTE -eq 1 && -n "${NEW_CURRENT:-}" && -f pyproject.toml ]]; then
        py_ver="$(to_pep440 "$NEW_CURRENT")"
        sed -E -i "s/^[[:space:]]*version[[:space:]]*=[[:space:]]*\"[^\"]+\"/version = \"${py_ver}\"/" pyproject.toml || true

        # If a commit exists, stage and try to amend it so the pyproject change
        # is included in the bump commit. If amend fails, create a follow-up commit.
        if git rev-parse --verify HEAD >/dev/null 2>&1; then
            git add pyproject.toml || true
            if ! git diff --cached --quiet; then
                if git commit --amend --no-edit >/dev/null 2>&1; then
                    if [[ "${TAG:-}" == "true" || "${TAG:-}" == "True" ]]; then
                        git tag -f "${NEW_CURRENT}" >/dev/null 2>&1 || true
                    fi
                else
                    git commit -m "Normalize pyproject version to PEP440 (${py_ver})" || true
                fi
            fi
        fi
    fi

    if [[ $EXECUTE -eq 1 && -n "${NEW_CURRENT:-}" && "${TAG:-}" == "true" ]]; then
        vtag="v${NEW_CURRENT}"
        if git rev-parse --verify "$vtag" >/dev/null 2>&1; then
            :
        else
            if git rev-parse --verify "${NEW_CURRENT}" >/dev/null 2>&1; then
                target=$(git rev-parse "${NEW_CURRENT}")
                git tag -a "$vtag" "$target" -m "$vtag" || git tag "$vtag" "$target"
                git push origin "$vtag" || true
                git tag -d "${NEW_CURRENT}" >/dev/null 2>&1 || true
                git push origin ":refs/tags/${NEW_CURRENT}" >/dev/null 2>&1 || true
            else
                target=$(git log -n1 --pretty=format:%H -- pyproject.toml octoprint_uptime/_version.py || true)
                if [[ -n "$target" ]]; then
                    git tag -a "$vtag" "$target" -m "$vtag" || git tag "$vtag" "$target"
                    git push origin "$vtag" || true
                fi
            fi
        fi
    fi

    if [[ $EXECUTE -eq 0 ]]; then
        printf "%b\n" "Done (dry-run). Note: remove --dry-run (use --execute) to perform real bump."
    else
        printf "%b\n" "Done."

        run_post_commit_build
    fi
fi
