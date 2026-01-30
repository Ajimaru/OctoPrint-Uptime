#!/usr/bin/env bash

# Windows Git-Bash re-exec wrapper
# This script attempts to ensure the calling script runs under Git Bash on
# native Windows. It locates a suitable `bash.exe` and execs the original
# script with that interpreter. Comments in this file are English-only.

# If already running under Bash, do nothing (when sourced). If executed,
# behave as a launcher: first argument should be the target script path.
if [ -n "${BASH_VERSION-}" ]; then
    # Running under bash already — return when sourced, or exit when executed.
    if [ "${BASH_SOURCE[0]}" != "$0" ]; then
        return 0
    else
        exit 0
    fi
fi

# Determine target script (first argument) and remaining args
target_script="$1"
shift || true

# Try to find a bash executable in PATH
find_bash() {
    if command -v bash >/dev/null 2>&1; then
        command -v bash 2>/dev/null | tr -d '\r' || true
        return 0
    fi

    # On Windows, try where.exe (may output CRLF)
    if command -v where.exe >/dev/null 2>&1; then
        # pick first result
        local w
        w=$(where.exe bash 2>/dev/null | tr -d '\r' | sed -n '1p' || true)
        if [ -n "$w" ]; then
            printf '%s' "$w"
            return 0
        fi
    fi

    # Common Program Files locations (Windows paths)
    if [ -n "${PROGRAMFILES-}" ] && [ -x "${PROGRAMFILES}/Git/bin/bash.exe" ]; then
        printf '%s' "${PROGRAMFILES}/Git/bin/bash.exe"
        return 0
    fi
    if [ -n "${PROGRAMFILES(x86)-}" ] && [ -x "${PROGRAMFILES(x86)}/Git/bin/bash.exe" ]; then
        printf '%s' "${PROGRAMFILES(x86)}/Git/bin/bash.exe"
        return 0
    fi

    # WSL-style path checks (/c/Program Files)
    if [ -x "/c/Program Files/Git/bin/bash.exe" ]; then
        printf '%s' "/c/Program Files/Git/bin/bash.exe"
        return 0
    fi
    if [ -x "/c/Program Files (x86)/Git/bin/bash.exe" ]; then
        printf '%s' "/c/Program Files (x86)/Git/bin/bash.exe"
        return 0
    fi

    return 1
}

bash_path=$(find_bash 2>/dev/null || true)

if [ -n "$bash_path" ]; then
    # Exec the target script under the discovered bash; preserve args
    exec "$bash_path" "$target_script" "$@"
else
    printf '%s\n' "Git Bash not found on this system. Please run the script in Git Bash or install Git for Windows: https://git-scm.com/download/win" >&2
    exit 1
fi
#!/usr/bin/env bash

# Windows Git-Bash re-exec wrapper
# This script attempts to ensure the calling script runs under Git Bash on
# native Windows. It locates a suitable `bash.exe` and execs the original
# script with that interpreter. Comments in this file are English-only.

# If already running under Bash, do nothing (when sourced). If executed,
# behave as a launcher: first argument should be the target script path.
if [ -n "${BASH_VERSION-}" ]; then
    # Running under bash already — return when sourced, or exit when executed.
    if [ "${BASH_SOURCE[0]}" != "$0" ]; then
        return 0
    else
        exit 0
    fi
fi

# Determine target script (first argument) and remaining args
target_script="$1"
shift || true

# Try to find a bash executable in PATH
find_bash() {
    if command -v bash >/dev/null 2>&1; then
        command -v bash 2>/dev/null | tr -d '\r' || true
        return 0
    fi

    # On Windows, try where.exe (may output CRLF)
    if command -v where.exe >/dev/null 2>&1; then
        # pick first result
        local w
        w=$(where.exe bash 2>/dev/null | tr -d '\r' | sed -n '1p' || true)
        if [ -n "$w" ]; then
            printf '%s' "$w"
            return 0
        fi
    fi

    # Common Program Files locations (Windows paths)
    if [ -n "${PROGRAMFILES-}" ] && [ -x "${PROGRAMFILES}/Git/bin/bash.exe" ]; then
        printf '%s' "${PROGRAMFILES}/Git/bin/bash.exe"
        return 0
    fi
    if [ -n "${PROGRAMFILES(x86)-}" ] && [ -x "${PROGRAMFILES(x86)}/Git/bin/bash.exe" ]; then
        printf '%s' "${PROGRAMFILES(x86)}/Git/bin/bash.exe"
        return 0
    fi

    # WSL-style path checks (/c/Program Files)
    if [ -x "/c/Program Files/Git/bin/bash.exe" ]; then
        printf '%s' "/c/Program Files/Git/bin/bash.exe"
        return 0
    fi
    if [ -x "/c/Program Files (x86)/Git/bin/bash.exe" ]; then
        printf '%s' "/c/Program Files (x86)/Git/bin/bash.exe"
        return 0
    fi

    return 1
}

bash_path=$(find_bash 2>/dev/null || true)

if [ -n "$bash_path" ]; then
    # Exec the target script under the discovered bash; preserve args
    exec "$bash_path" "$target_script" "$@"
else
    printf '%s\n' "Git Bash not found on this system. Please run the script in Git Bash or install Git for Windows: https://git-scm.com/download/win" >&2
    exit 1
fi
