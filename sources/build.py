import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from shapely.geometry import Polygon, MultiPolygon
from shapely.geometry.polygon import orient
from shapely import affinity
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.ttLib import TTFont
import glyphs as GL
import spacing as SP

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)
MARKS = ("acute", "grave", "circumflex", "dieresis", "cedilla", "tilde", "ring", "caron")


def base_of(name):
    for m in MARKS:
        if name.endswith(m) and len(name) > len(m):
            b = name[: -len(m)]
            b = "dotlessi" if b == "i" else b
            if b in GL.G:
                return b
    return name


def polys(geom):
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    return [p for p in getattr(geom, "geoms", []) if isinstance(p, Polygon)]


def rings_of(geom, ccw_outer):
    out = []
    for p in polys(geom):
        p = p.simplify(0.6)
        if p.is_empty or p.area < 50:
            continue
        for q in polys(p):
            q = orient(q, sign=1.0 if ccw_outer else -1.0)
            for r in [q.exterior, *q.interiors]:
                pts = [(round(x), round(y)) for x, y in list(r.coords)[:-1]]
                clean = []
                for pt in pts:
                    if not clean or pt != clean[-1]:
                        clean.append(pt)
                if len(clean) > 1 and clean[0] == clean[-1]:
                    clean.pop()
                if len(clean) >= 3:
                    out.append(clean)
    return out


def draw(pen, rings):
    for r in rings:
        pen.moveTo(r[0])
        for p in r[1:]:
            pen.lineTo(p)
        pen.closePath()


order = [".notdef", "space"] + sorted(n for n in GL.G if n != "space")
placed, adv = {}, {}
for name, (uni, geom) in GL.G.items():
    if name in ("space", "uni00A0"):
        placed[name] = geom
        adv[name] = GL.SPACE_WIDTH
        continue
    b = base_of(name)
    bgeom = GL.G[b][1]
    opt = SP.optical_sidebearings(bgeom, b, GL.G[b][0])
    if opt:
        exl, exr, lsb, rsb = opt
    else:
        exl, _, exr, _ = bgeom.bounds
        lsb, rsb = GL.SPACING.get(b, (40, 40))
    placed[name] = affinity.translate(geom, lsb - exl, 0)
    adv[name] = round(exr - exl + lsb + rsb)

# ---- kerning
prof = {n: SP.profile(placed[n]) for n in placed if n != "space"}
def kind(n):
    b = base_of(n)
    return SP.zone_of(b, GL.G[b][0])[0]
LETTERS = [n for n in placed if n != "space" and kind(n)]
PUNCT = [n for n in ["period", "comma", "colon", "semicolon", "quoteright", "quoteleft",
         "quotedblright", "quotedblleft", "quotesingle", "quotedbl", "hyphen", "endash",
         "parenleft", "parenright", "bracketleft", "bracketright", "exclam", "question",
         "slash", "ellipsis", "periodcentered"] if n in placed]
STEM = {"lower": "l", "cap": "I", "fig": "l"}

def ext(n):
    _, y0, _, y1 = placed[n].bounds
    return (int(y0 // SP.STEP * SP.STEP), int(y1))

def gap_ref(a, b, zone):
    return SP.kern_value(prof[a][1], adv[a], prof[b][0], zone, 0) / -SP.KERN_GAIN if False else None

def optical(a, b, zone):
    Ra, Lb = prof[a][1], prof[b][0]
    gaps = SP.pair_gap_profile(Ra, adv[a], Lb)
    if not gaps: return None
    t = min(gaps.values())
    rows = [min(gaps[y] - t, SP.KERN_CAP) if y in gaps else SP.KERN_CAP
            for y in SP.BANDS if zone[0] <= y < zone[1]]
    return t + sum(rows) / len(rows) * 0.62

def kern(a, b):
    ka, kb = kind(a), kind(b)
    if ka and kb:
        zone = SP.LOWER_ZONE if "lower" in (ka, kb) else (SP.CAP_ZONE if ka == kb == "cap" else SP.FIG_ZONE)
        ref = optical(STEM[ka], STEM[kb], zone)
    elif ka:
        zone = ext(b); ref = optical(STEM[ka], b, zone)
    elif kb:
        zone = ext(a); ref = optical(a, STEM[kb], zone)
    else:
        return 0
    if ref is None: return 0
    return SP.kern_value(prof[a][1], adv[a], prof[b][0], zone, ref)

KERNS = {}
for a in LETTERS + PUNCT:
    for b in LETTERS + PUNCT:
        if a in PUNCT and b in PUNCT: continue
        k = kern(a, b)
        if k: KERNS[(a, b)] = k
SOFT = {"quoteright", "quoteleft", "quotedblright", "quotedblleft", "quotesingle", "quotedbl", "hyphen", "endash"}
for p, v in list(KERNS.items()):
    if SOFT & set(p):
        KERNS[p] = max(v, -50)
KERNS.update(getattr(SP, "OVERRIDES", {}))
KERNS = {p: v for p, v in KERNS.items() if v}
nd = Polygon([(50, 0), (450, 0), (450, 700), (50, 700)]).difference(
    Polygon([(110, 60), (390, 60), (390, 640), (110, 640)]))
placed[".notdef"], adv[".notdef"] = nd, 500

cmap = {uni: n for n, (uni, _) in GL.G.items() if uni}

FEA = """
languagesystem DFLT dflt;
languagesystem latn dflt;
feature ss01 { featureNames { name "Descending f"; }; sub f by f.ss01; } ss01;
feature salt { sub f by f.ss01; } salt;
__KERN__
"""


_ys = [placed[n].bounds for n in placed if not placed[n].is_empty]
_ymax = max(y1 for _, _, _, y1 in _ys); _ymin = min(y0 for _, y0, _, _ in _ys)
_agrave = placed["Agrave"].bounds[3]
VM = {"asc": int(max(_agrave, 950) + 0.999), "desc": -260,
      "winAsc": int(_ymax + 0.999), "winDesc": int(-_ymin + 0.999)}
print("vertical metrics", VM)


def build(kind):
    fb = FontBuilder(1000, isTTF=(kind == "ttf"))
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    metrics = {}
    if kind == "ttf":
        gl = {}
        for n in order:
            pen = TTGlyphPen(None)
            draw(pen, rings_of(placed[n], ccw_outer=False))
            gl[n] = pen.glyph()
        fb.setupGlyf(gl)
        for n in order:
            metrics[n] = (adv[n], gl[n].xMin if gl[n].numberOfContours else 0)
    else:
        cs = {}
        for n in order:
            pen = T2CharStringPen(adv[n], None)
            draw(pen, rings_of(placed[n], ccw_outer=True))
            cs[n] = pen.getCharString()
        fb.setupCFF("McKitrick-Regular", {"FullName": "McKitrick Regular"}, cs, {})
        for n in order:
            mn = placed[n].bounds[0] if not placed[n].is_empty else 0
            metrics[n] = (adv[n], round(mn))
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=VM["asc"], descent=VM["desc"], lineGap=0)
    fb.setupNameTable({
        "copyright": "Copyright 2026 The McKitrick Project Authors (https://github.com/ianlawton/McKitrick)",
        "familyName": "McKitrick", "styleName": "Regular",
        "uniqueFontIdentifier": "1.500;NONE;McKitrick-Regular",
        "fullName": "McKitrick Regular", "psName": "McKitrick-Regular",
        "version": "Version 1.500",
        "manufacturer": "Ian Lawton",
        "designer": "Ian Lawton",
        "description": "McKitrick is a condensed display typeface drawn from hand-cut marker sketches: "
                       "separate flat-ended strokes, tapered dots, and an optional descending f (ss01).",
        "vendorURL": "https://github.com/ianlawton/McKitrick",
        "designerURL": "https://github.com/ianlawton",
        "licenseDescription": "This Font Software is licensed under the SIL Open Font License, Version 1.1. "
                              "This license is available with a FAQ at: https://openfontlicense.org",
        "licenseInfoURL": "https://openfontlicense.org",
    })
    fb.setupOS2(version=4, sTypoAscender=VM["asc"], sTypoDescender=VM["desc"], sTypoLineGap=0,
                usWinAscent=VM["winAsc"], usWinDescent=VM["winDesc"], sxHeight=GL.XH, sCapHeight=GL.CAP,
                achVendID="NONE", fsType=0, usWeightClass=400, fsSelection=0x40 | 0x80,
                ulCodePageRange1=0, ulCodePageRange2=0)
    fb.setupPost()
    fb.setupHead(unitsPerEm=1000, fontRevision=1.5)
    fea = FEA.replace('__KERN__', 'feature kern {\n' + '\n'.join(f'  pos {a} {b} {v};' for (a, b), v in sorted(KERNS.items())) + '\n} kern;')
    addOpenTypeFeaturesFromString(fb.font, fea)
    path = os.path.join(OUT, f"McKitrick-Regular.{kind}")
    fb.save(path)
    return path


ttf = build("ttf")
otf = build("otf")


def finish(path, truetype):
    from fontTools.ttLib import newTable
    from fontTools.ttLib.tables import ttProgram
    f = TTFont(path)
    os2 = f["OS/2"]
    os2.recalcUnicodeRanges(f)
    os2.recalcCodePageRanges(f)
    f["head"].macStyle = 0
    if truetype:
        gasp = newTable("gasp"); gasp.version = 1; gasp.gaspRange = {0xFFFF: 0x000F}
        f["gasp"] = gasp
        prep = newTable("prep"); prog = ttProgram.Program()
        prog.fromAssembly(["PUSHW[ ]", "511", "SCANCTRL[ ]", "PUSHB[ ]", "4", "SCANTYPE[ ]"])
        prep.program = prog; f["prep"] = prep
    f.save(path)


finish(ttf, True)
finish(otf, False)
f = TTFont(ttf)
f.flavor = "woff2"
f.save(os.path.join(OUT, "McKitrick-Regular.woff2"))
print(ttf, otf, len(order), "glyphs")


def write_ufo(path):
    """Editable UFO source mirroring the built font: outlines, metrics, kerning, features."""
    import shutil, ufoLib2
    from fontTools.pens.pointPen import SegmentToPointPen
    shutil.rmtree(path, ignore_errors=True)
    u = ufoLib2.Font()
    i = u.info
    i.familyName, i.styleName = "McKitrick", "Regular"
    i.unitsPerEm, i.xHeight, i.capHeight = 1000, GL.XH, GL.CAP
    i.ascender, i.descender = GL.ASC, GL.DSC
    i.versionMajor, i.versionMinor = 1, 500
    i.copyright = "Copyright 2026 The McKitrick Project Authors (https://github.com/ianlawton/McKitrick)"
    i.openTypeNameDesigner = i.openTypeNameManufacturer = "Ian Lawton"
    i.openTypeNameLicense = ("This Font Software is licensed under the SIL Open Font License, Version 1.1. "
                             "This license is available with a FAQ at: https://openfontlicense.org")
    i.openTypeNameLicenseURL = "https://openfontlicense.org"
    i.openTypeOS2TypoAscender, i.openTypeOS2TypoDescender, i.openTypeOS2TypoLineGap = VM["asc"], VM["desc"], 0
    i.openTypeHheaAscender, i.openTypeHheaDescender, i.openTypeHheaLineGap = VM["asc"], VM["desc"], 0
    i.openTypeOS2WinAscent, i.openTypeOS2WinDescent = VM["winAsc"], VM["winDesc"]
    i.openTypeOS2Selection = [7]
    i.openTypeOS2VendorID = "NONE"
    i.openTypeOS2Type = []
    i.postscriptUnderlinePosition, i.postscriptUnderlineThickness = -110, 70
    cmap_rev = {}
    for uni, n in cmap.items():
        cmap_rev.setdefault(n, []).append(uni)
    for n in order:
        gl = u.newGlyph(n)
        gl.width = adv[n]
        gl.unicodes = sorted(cmap_rev.get(n, []))
        pen = SegmentToPointPen(gl.getPointPen())
        draw(pen, rings_of(placed[n], ccw_outer=True))
    u.glyphOrder = order
    for (a, b), v in KERNS.items():
        u.kerning[(a, b)] = v
    u.features.text = FEA.replace("__KERN__", "")
    u.save(path)


if os.environ.get("MCKITRICK_UFO"):
    write_ufo(os.environ["MCKITRICK_UFO"])
    print("UFO written to", os.environ["MCKITRICK_UFO"])
