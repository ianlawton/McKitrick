"""Regenerate the README / documentation images from the built OTF.

    python3 sources/make_docs_images.py          (needs uharfbuzz, fonttools, cairosvg)

Writes documentation/specimen.png, documentation/charset.png and
documentation/sample-in-use.png (plus the copy in documentation/article/).
Text is shaped with HarfBuzz, so kerning and features (ss01) are applied.
"""
import os
import shutil
import unicodedata

import cairosvg
import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(ROOT, "fonts", "otf", "Mckitrick-Regular.otf")
DOCS = os.path.join(ROOT, "documentation")

INK, PAPER = "#2A2728", "#F3EEE2"
APRICOT, GREEN = "#ECB28B", "#3F6152"

tt = TTFont(FONT)
gs = tt.getGlyphSet()
order = tt.getGlyphOrder()
upm = tt["head"].unitsPerEm
hbfont = hb.Font(hb.Face(hb.Blob.from_file_path(FONT)))


def text(s, x, baseline, size, fill=INK, features=None):
    """SVG for a shaped line of text with its baseline at y=baseline (pixels)."""
    buf = hb.Buffer()
    buf.add_str(s)
    buf.guess_segment_properties()
    hb.shape(hbfont, buf, features or {})
    k = size / upm
    pen_x, paths = 0, []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        pen = SVGPathPen(gs)
        gs[order[info.codepoint]].draw(pen)
        d = pen.getCommands()
        if d:
            paths.append(f'<path transform="translate({pen_x + pos.x_offset},{pos.y_offset})" d="{d}"/>')
        pen_x += pos.x_advance
    return f'<g fill="{fill}" transform="translate({x},{baseline}) scale({k},{-k})">{"".join(paths)}</g>'


def save(name, w, h, bg, body):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">'
           f'<rect width="100%" height="100%" fill="{bg}"/>{body}</svg>')
    out = os.path.join(DOCS, name)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=out)
    print("wrote", out)
    return out


# ---------------------------------------------------------------- specimen
save("specimen.png", 2080, 1367, PAPER, "".join([
    text("McKitrick", 70, 352, 305),
    text("ABCDEFGHIJKLMNOPQRSTUVWXYZ", 70, 548, 118),
    text("abcdefghijklmnopqrstuvwxyz", 70, 690, 118),
    text("0123456789 & £ € $ ¥ % @ ! ? ( ) « »", 70, 822, 118),
    text("Quick fjords hold the oak barge.", 70, 952, 110),
    text("Été à la forêt · Grüße aus Łódź · Țară · Ţară", 70, 1063, 86),
    text("Stylistic set 1 · descending f", 70, 1142, 56),
    text("fjord fine affair", 70, 1238, 86, features={"ss01": True}),
]))

# ---------------------------------------------------------------- sample in use
save("sample-in-use.png", 1600, 1000, APRICOT, "".join([
    text("Marché du samedi", 88, 332, 250),
    text("Sýry · Chléb · Květiny · Káva", 84, 520, 112, GREEN),
    text("Náměstí, Hôtel de Ville, Rynek", 86, 690, 96),
    text("8h – 13h", 84, 880, 156),
    text("fjords & affaires", 900, 880, 112, GREEN, features={"ss01": True}),
]))
shutil.copy(os.path.join(DOCS, "sample-in-use.png"), os.path.join(DOCS, "article", "sample-in-use.png"))

# ---------------------------------------------------------------- character set
cmap = tt.getBestCmap()
chars = [cp for cp in sorted(cmap)
         if cp > 0x20 and cp != 0xA0 and unicodedata.category(chr(cp)) != "Mn"]
COLS, CELL, M = 20, 84, 10
rows = (len(chars) + COLS - 1) // COLS
W, H = M * 2 + COLS * CELL, M * 2 + rows * CELL
grid = []
for r in range(rows + 1):
    grid.append(f'<line x1="{M}" x2="{M + COLS * CELL}" y1="{M + r * CELL}" y2="{M + r * CELL}"/>')
for c in range(COLS + 1):
    grid.append(f'<line x1="{M + c * CELL}" x2="{M + c * CELL}" y1="{M}" y2="{M + rows * CELL}"/>')
cells = []
size = 52
for i, cp in enumerate(chars):
    r, c = divmod(i, COLS)
    gname = cmap[cp]
    adv = tt["hmtx"][gname][0] * size / upm
    x = M + c * CELL + (CELL - adv) / 2
    cells.append(text(chr(cp), x, M + r * CELL + 60, size, "#000"))
save("charset.png", W, H, "#FFFFFF",
     f'<g stroke="#D7D7D7" stroke-width="1">{"".join(grid)}</g>' + "".join(cells))
