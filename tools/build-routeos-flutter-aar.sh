#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root/flutter_routeos"
flutter build aar --no-debug --no-profile --release --build-number=1 --output="$PWD/build"
