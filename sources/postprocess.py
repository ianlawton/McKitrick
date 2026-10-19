"""Finish the OTF after gftools builder: drop the TrueType-only prep table (it does
nothing in a CFF font) and add PostScript hints with otfautohint, so the OTF renders
cleanly at small sizes on Windows. Outlines are not changed."""
import subprocess
import sys
from fontTools.ttLib import TTFont

path = sys.argv[1] if len(sys.argv) > 1 else "fonts/otf/Mckitrick-Regular.otf"
f = TTFont(path)
if "prep" in f:
    del f["prep"]
f.save(path)
subprocess.run(["otfautohint", path], check=True)
print("hinted", path)
