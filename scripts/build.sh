#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
APP_DIR="${ROOT_DIR}/src/Charge Limiter.app"
MAIN_JS="${ROOT_DIR}/src/main.js"
TARGET_SCPT="${APP_DIR}/Contents/Resources/Scripts/main.scpt"

echo "==> Compiling JXA script..."
osacompile -l JavaScript -o "${TARGET_SCPT}" "${MAIN_JS}"

echo "==> Re-signing Charge Limiter.app..."
codesign --force --deep --sign - "${APP_DIR}"

echo "==> Done! App is ready at: ${APP_DIR}"
