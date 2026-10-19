#!/usr/bin/env bash
# Rebuild Mckitrick from source.
#   pip install -r sources/requirements.txt && ./build.sh
# 1. sources/build.py draws every glyph, fits smooth curves, spaces and kerns
#    them, and writes the UFO source.
# 2. gftools builder compiles TTF, OTF and WOFF2 into fonts/.
# 3. sources/postprocess.py hints the OTF (otfautohint, from afdko).
set -euo pipefail
cd "$(dirname "$0")"
python3 sources/build.py
cd sources && gftools builder config.yaml
cd .. && python3 sources/postprocess.py fonts/otf/Mckitrick-Regular.otf
