"""Mckitrick: write the UFO source for the Google Fonts build.

glyphs.py (stroke drawings) -> spacing.py (optical sidebearings, kerning)
-> fitcurves.py (smooth cubic outlines) -> Mckitrick-Regular.ufo
The fonts are then compiled from the UFO with `gftools builder sources/config.yaml`.
"""
import os
import sys
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient
from shapely import affinity
import ufoLib2
from fontTools.pens.pointPen import SegmentToPointPen
import glyphs as GL
import spacing as SP
import fitcurves as FC

FAMILY = "Mckitrick"
VERSION = (2, 6)
REPO = "https://github.com/ianlawton/McKitrick"
UFO_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{FAMILY}-Regular.ufo")

SUFFIXES = ("acute", "grave", "circumflex", "dieresis", "cedilla", "tilde", "ring", "caron", "macron",
            "breve", "dotaccent", "ogonek", "hungarumlaut", "commaaccent", "croat", "bar", "slash")
COMBINING = set(GL.COMBINING)
SELF_SPACED = set(GL.SELF_SPACED)


ALIASES = {}   # glyphs spaced and kerned exactly like another (name -> original)


def base_of(name):
    if name in ALIASES:
        return ALIASES[name]
    if name.endswith(".case"):      # all-caps forms space like the original
        return name[:-5]
    if name in SELF_SPACED or name in COMBINING:
        return name
    for m in SUFFIXES:
        if name.endswith(m) and len(name) > len(m):
            b = name[: -len(m)]
            b = "dotlessi" if b == "i" else b
            if b in GL.G:
                return b
    return name


# ------------------------------------------------------------------ placement and spacing
SPACE_LIKE = ("space", "uni00A0")
placed, adv, shift = {}, {}, {}
for name, (uni, geom) in GL.G.items():
    if name in SPACE_LIKE:
        placed[name], adv[name], shift[name] = geom, GL.SPACE_WIDTH, 0
        continue
    if name in COMBINING:
        placed[name], adv[name], shift[name] = geom, 0, 0
        continue
    b = base_of(name)
    bgeom = GL.G[b][1]
    opt = SP.optical_sidebearings(bgeom, b, GL.G[b][0])
    if opt:
        exl, exr, lsb, rsb = opt
    else:
        exl, _, exr, _ = bgeom.bounds
        lsb, rsb = GL.SPACING.get(b, (40, 40))
    if name in SELF_SPACED:   # include the apostrophe caron in the right side
        exr = max(exr, geom.bounds[2])
        rsb = max(rsb, 30)
    shift[name] = lsb - exl
    placed[name] = affinity.translate(geom, shift[name], 0)
    adv[name] = round(exr - exl + lsb + rsb)

MATH = ["plus", "minus", "equal", "plusminus", "multiply", "divide", "less", "greater", "logicalnot"]
for n in MATH:   # one shared width for the maths signs, each centred
    minx, _, maxx, _ = GL.G[n][1].bounds
    shift[n] = (340 - (maxx - minx)) / 2 - minx
    placed[n] = affinity.translate(GL.G[n][1], shift[n], 0)
    adv[n] = 340

placed[".notdef"] = Polygon([(50, 0), (450, 0), (450, 700), (50, 700)]).difference(
    Polygon([(110, 60), (390, 60), (390, 640), (110, 640)]))
adv[".notdef"], shift[".notdef"] = 500, 0

# ------------------------------------------------------------------ kerning with classes
prof = {n: SP.profile(placed[n]) for n in placed if n not in SPACE_LIKE and not placed[n].is_empty}


def kind(n):
    b = base_of(n)
    return SP.zone_of(b, GL.G[b][0])[0] if b in GL.G else None


REPS = sorted({base_of(n) for n in GL.G if n not in SPACE_LIKE and n not in COMBINING and kind(n)})
MEMBERS = {r: sorted(n for n in GL.G if base_of(n) == r and n not in COMBINING) for r in REPS}
PUNCT = [n for n in ["period", "comma", "colon", "semicolon", "quoteright", "quoteleft", "quotedblright",
                     "quotedblleft", "quotesingle", "quotedbl", "hyphen", "endash", "parenleft", "parenright",
                     "bracketleft", "bracketright", "exclam", "question", "slash", "ellipsis", "periodcentered",
                     "quotesinglbase", "quotedblbase", "guillemotleft", "guillemotright", "guilsinglleft",
                     "guilsinglright"] if n in placed]
PUNCT += [n + ".case" for n in GL.CASE if n + ".case" in placed]
STEM = {"lower": "l", "cap": "I", "fig": "l"}


def ext(n):
    _, y0, _, y1 = placed[n].bounds
    return (int(y0 // SP.STEP * SP.STEP), int(y1))


def optical(a, b, zone):
    gaps = SP.pair_gap_profile(prof[a][1], adv[a], prof[b][0])
    if not gaps:
        return None
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
    return 0 if ref is None else SP.kern_value(prof[a][1], adv[a], prof[b][0], zone, ref)


SOFT = {"quoteright", "quoteleft", "quotedblright", "quotedblleft", "quotesingle", "quotedbl", "hyphen", "endash"}
SOFT |= {"hyphen.case", "endash.case"}
CLASS_KERN = {}
for a in REPS + PUNCT:
    for b in REPS + PUNCT:
        if a in PUNCT and b in PUNCT:
            continue
        k = kern(a, b)
        if k and SOFT & {a, b}:
            k = max(k, -50)
        CLASS_KERN[(a, b)] = k

# Exceptions: an accented member must not collide with its neighbour once the class kern applies.
ACCENT_GAP = 24
EXCEPTIONS = {}
for (a, b), k in CLASS_KERN.items():
    left = MEMBERS.get(a, [a]); right = MEMBERS.get(b, [b])
    if len(left) == 1 and len(right) == 1:
        continue
    for x in left:
        for y in right:
            if x == a and y == b:
                continue
            gaps = SP.pair_gap_profile(prof[x][1], adv[x] + k, prof[y][0])
            if gaps and min(gaps.values()) < ACCENT_GAP:
                EXCEPTIONS[(x, y)] = k + round(ACCENT_GAP - min(gaps.values()))
# Clearance pass: the f's overhanging top must never touch a quote or an accent that
# follows it. Measure the real outlines and open each pair just enough.
CLEAR = 45
OVERHANG = [n for n in ("f", "f.ss01") if n in placed]
FOLLOWERS = sorted({n for n in placed if n not in SPACE_LIKE and n not in COMBINING and n in prof
                    and (kind(n) == "lower" and placed[n].bounds[3] > GL.XH + 40 and base_of(n) != n
                         or n in ("quoteright", "quotedblright", "quotesingle", "quotedbl",
                                  "quoteleft", "quotedblleft", "question", "exclam", "asterisk",
                                  "parenright", "bracketright", "braceright", "trademark", "registered"))})


def current_kern(x, y):
    if (x, y) in EXCEPTIONS:
        return EXCEPTIONS[(x, y)]
    rx = base_of(x) if base_of(x) in MEMBERS else x
    ry = base_of(y) if base_of(y) in MEMBERS else y
    return CLASS_KERN.get((rx, ry), 0)


CLEARANCE = {}
for x in OVERHANG:
    for y in FOLLOWERS:
        k = current_kern(x, y)
        gaps = SP.pair_gap_profile(prof[x][1], adv[x] + k, prof[y][0])
        b = base_of(y)
        if b == "dotlessi" and y.startswith("i"):   # į keeps the i's own dot
            b = "i"
        if b != y and b in prof:   # only where the accent itself closes the gap
            bg = SP.pair_gap_profile(prof[x][1], adv[x] + current_kern(x, b), prof[b][0])
            if bg and gaps and min(gaps.values()) >= min(bg.values()) - 3:
                continue
        if gaps and min(gaps.values()) < CLEAR:
            EXCEPTIONS[(x, y)] = k + round(CLEAR - min(gaps.values()))
            CLEARANCE[(x, y)] = EXCEPTIONS[(x, y)]
print(f"clearance pairs: {len(CLEARANCE)}", dict(list(CLEARANCE.items())[:12]))
CLASS_KERN = {p: v for p, v in CLASS_KERN.items() if v}
print(f"{len(REPS)} kerning classes, {len(CLASS_KERN)} class pairs, {len(EXCEPTIONS)} exceptions")

# ------------------------------------------------------------------ vertical metrics
ys = [placed[n].bounds for n in placed if not placed[n].is_empty]
ymax = max(b[3] for b in ys); ymin = min(b[1] for b in ys)
VM = {"asc": int(max(placed["Agrave"].bounds[3], 950) + 0.999), "desc": -260,
      "winAsc": int(ymax + 0.999), "winDesc": int(-ymin + 0.999)}

# ------------------------------------------------------------------ write the UFO
shutil.rmtree(UFO_PATH, ignore_errors=True)
os.makedirs(os.path.dirname(os.path.abspath(UFO_PATH)), exist_ok=True)
u = ufoLib2.Font()
i = u.info
i.familyName, i.styleName = FAMILY, "Regular"
i.styleMapFamilyName, i.styleMapStyleName = FAMILY, "regular"
i.versionMajor, i.versionMinor = VERSION
i.unitsPerEm, i.xHeight, i.capHeight, i.ascender, i.descender = 1000, GL.XH, GL.CAP, GL.ASC, GL.DSC
i.italicAngle = 0
i.copyright = f"Copyright 2026 The {FAMILY} Project Authors ({REPO})"
i.openTypeNameDesigner = i.openTypeNameManufacturer = "Ian Lawton"
i.openTypeNameDesignerURL = "https://github.com/ianlawton"
i.openTypeNameManufacturerURL = REPO
i.openTypeNameDescription = ("Mckitrick is a condensed display typeface drawn from hand-cut marker sketches: "
                             "separate flat-ended strokes, tapered dots and an optional descending f (ss01).")
i.openTypeNameLicense = ("This Font Software is licensed under the SIL Open Font License, Version 1.1. "
                         "This license is available with a FAQ at: https://openfontlicense.org")
i.openTypeNameLicenseURL = "https://openfontlicense.org"
i.openTypeOS2VendorID = "NONE"
i.openTypeOS2WeightClass, i.openTypeOS2WidthClass = 400, 5
i.openTypeOS2Type = []
i.openTypeOS2Selection = [7]
i.openTypeOS2TypoAscender, i.openTypeOS2TypoDescender, i.openTypeOS2TypoLineGap = VM["asc"], VM["desc"], 0
i.openTypeHheaAscender, i.openTypeHheaDescender, i.openTypeHheaLineGap = VM["asc"], VM["desc"], 0
i.openTypeOS2WinAscent, i.openTypeOS2WinDescent = VM["winAsc"], VM["winDesc"]
i.postscriptUnderlinePosition, i.postscriptUnderlineThickness = -110, 70
# PostScript hinting zones (baseline, x-height, figure height, cap height, ascender, each
# with its overshoot) and standard stems, used by otfautohint for the OTF
i.postscriptBlueValues = [-GL.OV, 0, GL.XH, GL.XH + GL.OV, GL.FIG, GL.FIG + GL.OV,
                          GL.CAP, GL.CAP + GL.OV, GL.ASC, GL.ASC + GL.OV]
i.postscriptOtherBlues = [GL.DSC - GL.OV, GL.DSC]
i.postscriptStemSnapV = [GL.W]
i.postscriptStemSnapH = [GL.WB, GL.WB + 10]
i.postscriptBlueFuzz = 0
i.openTypeGaspRangeRecords = [{"rangeMaxPPEM": 65535, "rangeGaspBehavior": [0, 1, 2, 3]}]

cmap = {}
for n, (uni, _) in GL.G.items():
    if uni:
        cmap.setdefault(n, []).append(uni)

order = [".notdef", "space"] + sorted(n for n in placed if n not in (".notdef", "space"))
total_segments = 0
for n in order:
    gl = u.newGlyph(n)
    gl.width = adv[n]
    gl.unicodes = sorted(cmap.get(n, []))
    geom = placed[n]
    polys = [] if geom.is_empty else ([geom] if geom.geom_type == "Polygon" else
                                       [p for p in geom.geoms if p.geom_type == "Polygon"])
    pen = SegmentToPointPen(gl.getPointPen())
    for p in polys:
        if p.area < 40:
            continue
        p = orient(p, 1.0)                     # PostScript direction: outer counter-clockwise
        for ring in [p.exterior, *p.interiors]:
            segs = FC.round_segments(FC.fit_ring(list(ring.coords)[:-1]))
            total_segments += len(segs)
            FC.draw_segments(pen, segs)
    # anchors for mark attachment
    src = n if n in GL.G else None
    if src:
        for aname, (ax, ay) in GL.anchors_for(src).items():
            gl.appendAnchor({"name": aname, "x": round(ax + shift[n]), "y": round(ay)})

u.glyphOrder = order
u.lib["public.openTypeMeta"] = {"dlng": ["Latn"], "slng": ["Latn"]}
u.lib["public.openTypeCategories"] = {
    **{n: "mark" for n in COMBINING},
    **{n: "base" for n in order if n not in COMBINING and n not in SPACE_LIKE and n != ".notdef"},
}
for r in REPS:
    if len(MEMBERS[r]) > 0:
        u.groups[f"public.kern1.{r}"] = MEMBERS[r]
        u.groups[f"public.kern2.{r}"] = MEMBERS[r]
side = lambda n, s: f"public.kern{s}.{n}" if n in MEMBERS else n
for (a, b), v in CLASS_KERN.items():
    u.kerning[(side(a, 1), side(b, 2))] = v
for (a, b), v in EXCEPTIONS.items():
    u.kerning[(a, b)] = v
for alias, orig in ALIASES.items():          # aliases take the original's pairs
    for (a, b), v in list(u.kerning.items()):
        if a == orig:
            u.kerning[(alias, b)] = v
        if b == orig:
            u.kerning[(a, alias)] = v

tops = " ".join(n for n in sorted(COMBINING) if GL.COMBINING[n][2] == "top")
bottoms = " ".join(n for n in sorted(COMBINING) if GL.COMBINING[n][2] != "top")
case_subs = "\n".join(f"    sub {n} by {n}.case;" for n in GL.CASE if n + ".case" in placed)
u.features.text = f"""languagesystem DFLT dflt;
languagesystem latn dflt;

@CombiningTop = [{tops}];
@CombiningBottom = [{bottoms}];

feature ccmp {{
    lookup soft_dotted {{
        sub i' @CombiningTop by dotlessi;
        sub i' @CombiningBottom @CombiningTop by dotlessi;
        sub i' @CombiningBottom @CombiningBottom @CombiningTop by dotlessi;
        sub j' @CombiningTop by dotlessj;
        sub j' @CombiningBottom @CombiningTop by dotlessj;
        sub iogonek' @CombiningTop by iogonek.dotless;
        sub iogonek' @CombiningBottom @CombiningTop by iogonek.dotless;
    }} soft_dotted;
}} ccmp;

feature ss01 {{
    featureNames {{ name "Descending f"; }};
    sub f by f.ss01;
}} ss01;

feature salt {{
    sub f by f.ss01;
}} salt;

feature case {{
{case_subs}
}} case;
"""
u.save(UFO_PATH)
print(f"{len(order)} glyphs, {total_segments} outline segments, written to {UFO_PATH}")
