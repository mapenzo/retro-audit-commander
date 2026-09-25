#!/usr/bin/env sh
set -eu

if [ "$(uname -s)" != "Darwin" ]; then
    printf '%s\n' 'Este script debe ejecutarse en macOS.' >&2
    exit 2
fi

if ! command -v uv >/dev/null 2>&1; then
    printf '%s\n' 'uv no está instalado. Instálalo desde https://docs.astral.sh/uv/ y vuelve a ejecutar este script.' >&2
    exit 2
fi

exec uv run --locked --group dev python scripts/build_local.py "$@"