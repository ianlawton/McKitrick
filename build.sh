#!/usr/bin/env bash
# Rebuild McKitrick from source.
# Usage:  pip install -r sources/requirements.txt && ./build.sh
set -euo pipefail
cd "$(dirname "$0")"

MCKITRICK_UFO="sources/McKitrick-Regular.ufo" python3 sources/build.py

cp sources/out/McKitrick-Regular.ttf   fonts/ttf/
cp sources/out/McKitrick-Regular.otf   fonts/otf/
cp sources/out/McKitrick-Regular.woff2 fonts/webfonts/
echo "Fonts written to fonts/ and the UFO source refreshed in sources/."
