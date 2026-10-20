"""McKitrick glyph definitions.

Every glyph is drawn as centreline strokes, then expanded to outlines with
flat-cut ends, matching the hand-cut marker strokes of the source sketch.
Units: 1000 UPM, x-height 560, ascender 800, cap height 760, descender -200.
"""
import math
from shapely.geometry import LineString, Polygon, Point, box
from shapely.ops import unary_union
from shapely import affinity

XH, ASC, CAP, DSC, FIG = 560, 800, 760, -200, 720
OV = 16         # optical overshoot for round tops and bottoms
W = 84          # main stem weight
WB = 70         # crossbar / hairline-ish weight
H = W / 2


def bz(p0, c1, c2, p3, n=28):
    pts = []
    for i in range(n + 1):
        t = i / n
        a = (1 - t) ** 3
        b = 3 * (1 - t) ** 2 * t
        c = 3 * (1 - t) * t ** 2
        d = t ** 3
        pts.append((a * p0[0] + b * c1[0] + c * c2[0] + d * p3[0],
                    a * p0[1] + b * c1[1] + c * c2[1] + d * p3[1]))
    return pts


def path(*parts):
    """Join point lists / single points into one continuous centreline."""
    out = []
    for p in parts:
        seq = [p] if isinstance(p[0], (int, float)) else p
        for q in seq:
            if not out or math.dist(out[-1], q) > 0.5:
                out.append(tuple(q))
    return out


def stroke(pts, w=W, join="mitre"):
    return LineString(pts).buffer(w / 2, cap_style="flat", join_style=join,
                                  mitre_limit=4.0, quad_segs=8)


def ring(cx, cy, rx, ry, w=W, n=96):
    outer = Polygon([(cx + (rx + w / 2) * math.cos(2 * math.pi * i / n),
                      cy + (ry + w / 2) * math.sin(2 * math.pi * i / n)) for i in range(n)])
    inner = Polygon([(cx + (rx - w / 2) * math.cos(2 * math.pi * i / n),
                      cy + (ry - w / 2) * math.sin(2 * math.pi * i / n)) for i in range(n)])
    return outer.difference(inner)


def dot(cx, y0, h=110, wb=74, wt=118):
    """The sketch's tapered, wider-at-the-top dot."""
    return Polygon([(cx - wb / 2, y0), (cx + wb / 2, y0),
                    (cx + wt / 2, y0 + h), (cx - wt / 2, y0 + h)])


def clip(geom, lo=-10000, hi=10000):
    return geom.intersection(box(-10000, lo, 10000, hi))


SUP_K, SUP_STEM = 0.58, 58     # superiors: 58% size, 58-unit stems (about 70% of the main stem)


def lighten(geom, k, stem_w=SUP_STEM):
    """Scale a glyph by k and bring its strokes up to stem_w, so small forms are lighter
    than the text but not spindly."""
    return affinity.scale(geom, k, k, origin=(0, 0)).buffer((stem_w - W * k) / 2, join_style=2, mitre_limit=10)


G = {}      # name -> (unicode or None, shapely geometry)


def g(name, uni, *shapes, lo=None, hi=None):
    geom = unary_union(list(shapes))
    if lo is not None or hi is not None:
        geom = clip(geom, lo if lo is not None else -10000, hi if hi is not None else 10000)
    G[name] = (uni, geom)


# ---------------------------------------------------------------- lowercase
stem = lambda x, y0, y1, w=W: stroke([(x, y0), (x, y1)], w)

g("dotlessi", 0x131, stem(H, 0, XH))
g("i", ord("i"), stem(H, 0, XH), dot(H, 660))
g("l", ord("l"), stem(H, 0, ASC))
g("t", ord("t"), stem(H, 0, ASC - 20), stroke([(8, XH - 40), (180, XH - 40)], WB))
g("r", ord("r"), stroke(path(bz((H, 0), (H, 330), (52, 480), (175, 548)))))
g("c", ord("c"), stroke(bz((215, 540), (40, 480), (10, 120), (205, 20))))
g("j", ord("j"),
  stroke(path((110, XH), bz((110, 60), (110, -70), (80, -140), (0, -180)))),
  dot(110, 660))
g("k", ord("k"), stem(H, 0, ASC),
  stroke(bz((235, 545), (150, 500), (85, 400), (60, 250))),
  stroke([(85, 310), (256, -31)]), lo=0)
bowl_g = bz((205, 550), (0, 560), (5, 170), (200, 170))
g("g", ord("g"), stroke(bowl_g),
  stroke(path((210, XH), bz((210, 60), (210, -90), (150, -170), (15, -190)))))
bowl_a = bz((205, 550), (-5, 560), (-5, 20), (205, 40))
FOOT = box(210 - H, -50, 210 + H, 0)   # under the a/d stem: keep the bowl overshoot off the stem foot
g("a", ord("a"), unary_union([stroke(bowl_a), stem(210, 0, XH)]).difference(FOOT))
g("d", ord("d"), unary_union([stroke(bowl_a), stem(210, 0, ASC)]).difference(FOOT))
g("q", ord("q"), stroke(bowl_a), stem(210, DSC, XH))
bowl_b = bz((H + 5, 545), (265, 580), (265, -20), (H + 5, 30))
g("b", ord("b"), stem(H, 0, ASC), stroke(path(bz((H + 5, 545), (265, 580), (275, H), (W, H)), (H, H))))
g("p", ord("p"), stem(H, DSC, XH), stroke(bowl_b))


def taper_stroke(pts, widths):
    """A stroke whose width varies along its centreline, with flat ends."""
    L, R = [], []
    n = len(pts)
    for k, (p, w) in enumerate(zip(pts, widths)):
        a, b = pts[max(k - 1, 0)], pts[min(k + 1, n - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        l = math.hypot(dx, dy) or 1
        nx, ny = -dy / l, dx / l
        L.append((p[0] + nx * w / 2, p[1] + ny * w / 2))
        R.append((p[0] - nx * w / 2, p[1] - ny * w / 2))
    return Polygon(L + R[::-1]).buffer(0)


def _ease(t):
    return t * t * (3 - 2 * t)


def _shoulder(x0, x1, yc, ys, r, w0, wtop, bow, k=0.45):
    """Centreline: a gently bowed, steep diagonal from inside the left stem, then a
    smooth turn down into the next stem. The width tapers: thin where it leaves the
    stem, lighter over the crown, full stem weight where it becomes the stem."""
    P0, C = (x0, ys), (x1, yc)
    d = math.dist(P0, C)
    ux, uy = (C[0] - P0[0]) / d, (C[1] - P0[1]) / d
    nx, ny = -uy, ux
    a = (C[0] - ux * r, C[1] - uy * r)
    diag = bz(P0, (P0[0] + (a[0] - P0[0]) / 3 + nx * bow, P0[1] + (a[1] - P0[1]) / 3 + ny * bow),
              (P0[0] + 2 * (a[0] - P0[0]) / 3 + nx * bow * 0.7, P0[1] + 2 * (a[1] - P0[1]) / 3 + ny * bow * 0.7),
              a, n=20)
    turn = bz(a, (C[0] - ux * r * k, C[1] - uy * r * k), (x1, yc - r * k), (x1, yc - r), n=28)
    pts = diag[:-1] + turn
    cum = [0.0]
    for p, q in zip(pts, pts[1:]):
        cum.append(cum[-1] + math.dist(p, q))
    crown, T = cum[len(diag) - 1 + 10], cum[-1]
    ws = [w0 + (wtop - w0) * _ease(c / crown) if c <= crown
          else wtop + (W - wtop) * _ease((c - crown) / (T - crown)) for c in cum]
    return taper_stroke(pts, ws), yc - r


def arch(x0, x1, top=XH, ys=270, r=85, w0=58, wtop=72, bow=10, ov=OV // 2):
    """The sketch's m shoulder: it branches from the stem about halfway up, rises
    as a steep diagonal and curves smoothly over into the next stem. The rounded
    top reaches x-height plus a little overshoot, like the other round tops."""
    yc = top - H
    for _ in range(3):
        s, _end = _shoulder(x0, x1, yc, ys, r, w0, wtop, bow)
        yc += (top + ov) - s.bounds[3]
    s, end = _shoulder(x0, x1, yc, ys, r, w0, wtop, bow)
    return unary_union([s, stroke([(x1, 0), (x1, end + 1)])])


def arched(stems_x, left_top, ws=62, ys=310, rad=10):
    """n, h, m: a stem plus a shoulder to each following stem. The shoulder keeps
    an even stroke width ws all the way over: each counter is the letter's outer
    silhouette pulled in by ws, so its underside runs parallel to the top of the
    shoulder, with only a small radius where it meets the stems."""
    shape = unary_union([stem(stems_x[0], 0, left_top)] +
                        [arch(a, b, ys=ys, w0=ws, wtop=ws, bow=0) for a, b in zip(stems_x, stems_x[1:])])
    for a, b in zip(stems_x, stems_x[1:]):
        raw = box(a + H, -300, b - H, XH).difference(shape)
        counter = min(getattr(raw, "geoms", [raw]), key=lambda q: q.bounds[1])
        filled = unary_union([shape, counter, box(-1000, -1000, 2000, 0)])
        inner = filled.buffer(-ws, join_style="mitre", mitre_limit=10).intersection(box(a + H, -300, b - H, XH))
        inner = max(getattr(inner, "geoms", [inner]), key=lambda q: q.area)
        inner = inner.buffer(-rad, join_style="round").buffer(rad, join_style="round")
        shape = filled.difference(inner)
    out = clip(shape, lo=0)
    return unary_union([q for q in getattr(out, "geoms", [out]) if q.geom_type == "Polygon" and q.area > 1])


g("n", ord("n"), arched([H, 230], XH))
g("h", ord("h"), arched([H, 230], ASC))
g("m", ord("m"), arched([H, 210, 378], XH))
g("u", ord("u"), stroke(path((H, XH), bz((H, 130), (57, -10), (215, -10), (230, 130)))),
  stem(230, 0, XH))
g("f", ord("f"), stroke(path((H, 0), bz((H, 560), (H, 760), (80, 800), (185, 805)))),
  stroke([(5, XH - 40), (175, XH - 40)], WB), hi=ASC + 40)
g("f.ss01", None,
  stroke(path(bz((205, 790), (80, 790), (75, 640), (75, 480)), (75, 40),
              bz((75, 40), (75, -100), (50, -170), (0, -210)))),
  stroke([(75, 300), (190, 300)], WB))
g("o", ord("o"), ring(125, 280, 83, 238 + OV))
g("e", ord("e"), stroke(path((H, 300), (210, 300),
                              bz((210, 300), (215, 614), (H - 5, 614), (H - 5, 290)),
                              bz((H - 5, 290), (H - 5, 30), (120, -10), (215, 50)))))
g("s", ord("s"), stroke(path(bz((168, 505), (125, 560), (40, 545), (45, 425)),
                              bz((45, 425), (50, 300), (172, 295), (172, 160)),
                              bz((172, 160), (172, 15), (65, 0), (25, 60)))))
g("v", ord("v"), stroke([(15, XH + 20), (125, 0), (235, XH + 20)]), lo=0, hi=XH)
g("w", ord("w"), stroke([(15, XH + 20), (105, 0), (190, 430), (275, 0), (365, XH + 20)]), lo=0, hi=XH)
g("x", ord("x"), stroke([(10, XH + 20), (240, -20)]),
  stroke(bz((240, XH + 20), (150, 360), (100, 180), (10, -20))), lo=0, hi=XH)
g("y", ord("y"), stroke(path((H, XH), bz((H, 160), (57, 30), (215, 30), (230, 160)))),
  stroke(path((230, XH), bz((230, 60), (230, -90), (170, -170), (25, -190)))))
g("z", ord("z"), stroke([(10, XH - 40), (225, XH - 40), (35, 40), (240, 40)], WB + 6), lo=0, hi=XH)

# ---------------------------------------------------------------- capitals
TC = CAP - 42
BAR = WB + 10                 # weight of the E/F/L/T/Z bars
BT, BB = CAP - BAR / 2, BAR / 2   # bar centres that sit flush with cap height and baseline
g("A", ord("A"), stroke([(10, -20), (150, CAP + 40), (290, -20)]),
  stroke([(70, 250), (230, 250)], WB), lo=0, hi=CAP)
g("B", ord("B"), stem(H, 0, CAP),
  stroke(path((H, TC), bz((W, TC), (265, TC), (255, 400), (H, 410)))),
  stroke(path(bz((H, 410), (310, 420), (310, H), (W, H)), (H, H))))
g("C", ord("C"), stroke(bz((290, 725), (20, 700), (0, 50), (290, 25))))
g("D", ord("D"), stem(H, 0, CAP), stroke(path((H, TC), bz((W, TC), (345, TC), (345, H), (W, H)), (H, H))))
g("E", ord("E"), stem(H, 0, CAP), stroke([(H, BT), (245, BT)], BAR),
  stroke([(H, 400), (215, 400)], WB), stroke([(H, BB), (255, BB)], BAR))
g("F", ord("F"), stem(H, 0, CAP), stroke([(H, BT), (245, BT)], BAR),
  stroke([(H, 400), (215, 400)], WB))
# G: the C's arch, ending where its outer edge meets the baseline at the left side of
# the vertical stroke, which stands on its own square foot
g("G", ord("G"), unary_union([stroke(bz((295, 725), (20, 700), (0, 50), (285, 36.5))), stroke([(285, 0), (285, 330)]),
  stroke([(175, 330), (300, 330)], WB)]).difference(box(285 - H, -100, 400, 0)))
g("H", ord("H"), stem(H, 0, CAP), stem(270, 0, CAP), stroke([(H, 400), (270, 400)], WB))
g("I", ord("I"), stem(H, 0, CAP))
g("J", ord("J"), stroke(path((200, CAP), bz((200, 140), (200, -20), (60, -30), (10, 70)))))
g("K", ord("K"), stem(H, 0, CAP),
  stroke(bz((300, 745), (200, 680), (90, 520), (H, 330))),
  stroke([(95, 430), (320, -41)]), lo=0, hi=CAP)
g("L", ord("L"), stem(H, 0, CAP), stroke([(H, BB), (250, BB)], BAR))
g("M", ord("M"), stem(H, 0, CAP), stem(380, 0, CAP),
  stroke([(H, CAP + 40), (211, 230), (380, CAP + 40)]), lo=0, hi=CAP)
g("N", ord("N"), stem(H, 0, CAP), stem(285, 0, CAP),
  stroke([(30, CAP + 30), (297, -30)]).intersection(box(0, -1e4, 285 + H, 1e4)), lo=0, hi=CAP)
g("O", ord("O"), ring(165, 380, 123, 338 + OV))
g("P", ord("P"), stem(H, 0, CAP), stroke(path((H, TC), bz((W, TC), (310, TC), (300, 330), (H, 345)))))
g("Q", ord("Q"), ring(165, 380, 123, 338 + OV),
  stroke(bz((195, 40), (195, -60), (225, -120), (305, -150))))   # tail: the j's curve, mirrored
g("R", ord("R"), stem(H, 0, CAP), stroke(path((H, TC), bz((W, TC), (310, TC), (300, 330), (H, 345)))),
  stroke([(140, 360), (311, -36)]), lo=0)
g("S", ord("S"), stroke(path(bz((215, 690), (160, 755), (45, 740), (48, 585)),
                              bz((48, 585), (52, 420), (222, 410), (222, 215)),
                              bz((222, 215), (222, 25), (80, 10), (30, 75)))))
g("T", ord("T"), stroke([(0, BT), (300, BT)], BAR), stem(150, 0, CAP))
g("U", ord("U"), stroke(path((H, CAP), (H, 200), bz((H, 200), (H, -25), (270, -25), (270, 200)),
                              (270, CAP))))
g("V", ord("V"), stroke([(10, CAP + 30), (150, -10), (290, CAP + 30)]), lo=0, hi=CAP)
g("W", ord("W"), stroke([(10, CAP + 30), (115, -10), (210, 560), (305, -10), (410, CAP + 30)]),
  lo=0, hi=CAP)
g("X", ord("X"), stroke([(15, CAP + 20), (295, -20)]), stroke([(295, CAP + 20), (15, -20)]),
  lo=0, hi=CAP)
g("Y", ord("Y"), stroke([(10, CAP + 30), (155, 360), (300, CAP + 30)]), stem(155, 0, 380),
  lo=0, hi=CAP)
g("Z", ord("Z"), stroke([(15, BT), (280, BT), (40, BB), (295, BB)], BAR), lo=0, hi=CAP)

# ---------------------------------------------------------------- figures
TF = FIG - 42
g("zero", ord("0"), ring(145, 360, 103, 318 + OV))
g("one", ord("1"), stem(160, 0, FIG), stroke([(160, FIG - 25), (40, 580)], WB), hi=FIG)
g("two", ord("2"), stroke(path(bz((30, 590), (60, 735), (265, 735), (255, 560)),
                                bz((255, 560), (245, 380), (40, 220), (40, H)))),
  stroke([(15, BAR / 2), (280, BAR / 2)], WB + 10))
g("three", ord("three") if False else ord("3"),
  stroke(path(bz((30, 620), (90, 735), (265, 715), (255, 560)),
              bz((255, 560), (245, 430), (150, 400), (115, 400)))),
  stroke(path(bz((115, 400), (310, 400), (310, -85), (25, 50)))))
g("four", ord("4"), stroke([(215, -20), (215, FIG), (25, 250), (290, 250)]), lo=0, hi=FIG)
g("five", ord("5"), stroke(path((265, TF), (60, TF), (52, 430),
                                 bz((52, 430), (290, 480), (310, -70), (25, 40)))))
g("six", ord("six") if False else ord("6"), ring(150, 215, 105, 173 + OV),
  stroke(bz((250, 697), (80, 642), (H + 3, 420), (H + 3, 215))))


def rot180(geom, w, h):
    return affinity.rotate(geom, 180, origin=(w / 2, h / 2))


g("nine", ord("9"), rot180(G["six"][1], 297, FIG))
g("seven", ord("7"), stroke([(15, TF), (285, TF), (100, -20)], W), lo=0, hi=FIG)
g("eight", ord("8"), ring(150, 545, 92, 133 + OV // 2), ring(150, 200, 108, 158 + OV // 2))

# ---------------------------------------------------------------- punctuation
g("space", 0x20)
g("period", ord("."), dot(60, 0))
g("comma", ord(","), dot(60, 0),
  stroke(bz((60, 20), (62, -60), (45, -120), (5, -160)), 70))
g("colon", ord(":"), dot(60, 0), dot(60, 400))
g("semicolon", ord(";"), dot(60, 400), dot(60, 0),
  stroke(bz((60, 20), (62, -60), (45, -120), (5, -160)), 70))
g("exclam", ord("!"), stroke([(60, 230), (60, CAP)]), dot(60, 0))
g("question", ord("?"), stroke(path(bz((25, 610), (45, 775), (265, 770), (255, 580)),
                                     bz((255, 580), (245, 430), (150, 420), (150, 230)))),
  dot(150, 0))
g("hyphen", ord("-"), stroke([(15, 280), (205, 280)], WB))
g("endash", 0x2013, stroke([(0, 280), (420, 280)], WB))
g("emdash", 0x2014, stroke([(0, 280), (840, 280)], WB))
g("quotesingle", ord("'"), dot(60, 560, h=200, wb=54, wt=96))
g("quotedbl", ord('"'), dot(60, 560, h=200, wb=54, wt=96), dot(180, 560, h=200, wb=54, wt=96))
q_shape = lambda x, y: unary_union([dot(x, y + 60, h=100, wb=74, wt=110),
                                    stroke(bz((x, y + 80), (x + 2, y), (x - 15, y - 50), (x - 50, y - 90)), 70)])
qr = lambda x: q_shape(x, 640)
ql = lambda x: rot180(q_shape(x, 640), 2 * x, 2 * 680)
g("quoteright", 0x2019, qr(70))
g("quoteleft", 0x2018, ql(70))
g("quotedblright", 0x201D, qr(70), qr(190))
g("quotedblleft", 0x201C, ql(70), ql(190))
g("parenleft", ord("("), stroke(bz((185, 830), (20, 650), (20, -40), (185, -210))))
g("parenright", ord(")"), stroke(bz((15, 830), (180, 650), (180, -40), (15, -210))))
g("bracketleft", ord("["), stroke([(170, 790), (H, 790), (H, -170), (170, -170)], W, "mitre"))
g("bracketright", ord("]"), stroke([(0, 790), (128, 790), (128, -170), (0, -170)], W, "mitre"))
g("slash", ord("/"), stroke([(0, -140), (260, 820)]), lo=-140, hi=800)
g("plus", ord("+"), stroke([(10, 300), (270, 300)], WB), stroke([(140, 170), (140, 430)], WB))
g("equal", ord("="), stroke([(10, 380), (270, 380)], WB), stroke([(10, 220), (270, 220)], WB))
g("asterisk", ord("*"), *[stroke([(120, 600), (120 + 110 * math.sin(a), 600 + 110 * math.cos(a))], 60)
                          for a in [0, 2 * math.pi / 5, 4 * math.pi / 5, 6 * math.pi / 5, 8 * math.pi / 5]])
STERLING_CUT = 10
# The bowl-to-baseline corner is sliced off parallel to the j's tail cut
# (perpendicular to the j's final stroke direction, (-80, -40)).
_J_CUT = (-2, -1)
def _slice(geom, through, normal=_J_CUT):
    nx, ny = normal
    px, py = through
    far = 3000
    # half-plane on the outward side of the line through `through`
    dx, dy = -ny, nx
    half = Polygon([(px + dx * far, py + dy * far), (px - dx * far, py - dy * far),
                    (px - dx * far + nx * far, py - dy * far + ny * far),
                    (px + dx * far + nx * far, py + dy * far + ny * far)])
    return geom.difference(half)
g("sterling", 0xA3, _slice(unary_union([
    stroke(path(bz((265, 660), (240, 760), (100, 760), (100, 560)), (100, 280),
                bz((100, 280), (100, 150), (60, 80), (10, H)), (290, H)), W),
    stroke([(15, 400), (220, 400)], WB)]), (STERLING_CUT, 0)))
g("Euro", 0x20AC, stroke(bz((300, 690), (60, 720), (40, 40), (300, 40))),
  stroke([(0, 450), (220, 450)], WB - 10), stroke([(0, 300), (200, 300)], WB - 10))
g("periodcentered", 0xB7, dot(60, 250))
g("ellipsis", 0x2026, dot(60, 0), dot(210, 0), dot(360, 0))
g("ampersand", ord("&"),
  stroke(path((300, 330), bz((300, 330), (300, 140), (235, H), (150, H)),
              bz((150, H), (70, H), (40, 110), (60, 200)),
              (210, 470), bz((210, 470), (265, 560), (235, CAP - H), (145, CAP - H)),
              bz((145, CAP - H), (55, CAP - H), (30, 590), (95, 480)))),
  clip(stroke([(73, 534), (305, -40)]), 0))
g("percent", ord("%"), ring(80, 600, 45, 110, 64), ring(260, 140, 45, 110, 64),
  clip(stroke([(11, -32), (329, 752)], 64), 0, FIG))
g("numbersign", ord("#"), stroke([(90, 60), (130, 640)], WB), stroke([(210, 60), (250, 640)], WB),
  stroke([(20, 450), (310, 450)], WB), stroke([(10, 250), (300, 250)], WB))
g("at", ord("@"), ring(220, 300, 180, 330, 60),
  stroke(path((300, 420), (300, 200), bz((300, 200), (300, 120), (340, 100), (380, 120))), 60),
  ring(240, 300, 55, 115, 60))
g("underscore", ord("_"), stroke([(0, -110), (400, -110)], WB))

# ---------------------------------------------------------------- accents
def acute(cx, y):
    return stroke([(cx - 35, y), (cx + 55, y + 120)], 74)


def grave(cx, y):
    return stroke([(cx + 35, y), (cx - 55, y + 120)], 74)


def circ(cx, y):
    return stroke([(cx - 85, y), (cx, y + 115), (cx + 85, y)], 66)


def diaer(cx, y):
    return unary_union([dot(cx - 58, y, h=95, wb=52, wt=82), dot(cx + 58, y, h=95, wb=52, wt=82)])


def cedilla(cx):
    return stroke(bz((cx, 20), (cx + 5, -60), (cx + 70, -80), (cx + 50, -150)) +
                  bz((cx + 50, -150), (cx + 30, -220), (cx - 30, -215), (cx - 60, -200))[1:], 56)


MARKS = {"acute": acute, "grave": grave, "circumflex": circ, "dieresis": diaer}
UNI = {
    ("a", "grave"): 0xE0, ("a", "circumflex"): 0xE2, ("a", "dieresis"): 0xE4,
    ("e", "acute"): 0xE9, ("e", "grave"): 0xE8, ("e", "circumflex"): 0xEA, ("e", "dieresis"): 0xEB,
    ("dotlessi", "circumflex"): 0xEE, ("dotlessi", "dieresis"): 0xEF,
    ("o", "circumflex"): 0xF4, ("o", "dieresis"): 0xF6, ("o", "acute"): 0xF3,
    ("u", "grave"): 0xF9, ("u", "circumflex"): 0xFB, ("u", "dieresis"): 0xFC, ("u", "acute"): 0xFA,
    ("a", "acute"): 0xE1,
    ("A", "grave"): 0xC0, ("A", "circumflex"): 0xC2, ("A", "dieresis"): 0xC4, ("A", "acute"): 0xC1,
    ("E", "acute"): 0xC9, ("E", "grave"): 0xC8, ("E", "circumflex"): 0xCA, ("E", "dieresis"): 0xCB,
    ("I", "circumflex"): 0xCE, ("I", "dieresis"): 0xCF,
    ("O", "circumflex"): 0xD4, ("O", "dieresis"): 0xD6, ("O", "acute"): 0xD3,
    ("U", "grave"): 0xD9, ("U", "circumflex"): 0xDB, ("U", "dieresis"): 0xDC, ("U", "acute"): 0xDA,
}
for (base, mark), cp in list(UNI.items()):
    bgeom = G[base][1]
    minx, _, maxx, _ = bgeom.bounds
    cx = (minx + maxx) / 2
    y = 640 if base.islower() or base == "dotlessi" else 820
    name = (base if base != "dotlessi" else "i") + mark
    g(name, cp, bgeom, MARKS[mark](cx, y))
for base, cp in (("c", 0xE7), ("C", 0xC7)):
    bgeom = G[base][1]
    minx, _, maxx, _ = bgeom.bounds
    g(base + "cedilla", cp, bgeom, cedilla((minx + maxx) / 2 + 10))
g("oe", 0x153, ring(125, 280, 83, 238 + OV),
  affinity.translate(G["e"][1], 175, 0))
g("OE", 0x152, ring(165, 380, 123, 338 + OV), affinity.translate(G["E"][1], 250, 0))
_e_in_ae = affinity.translate(G["e"][1], 170, 0)
# the a stem's foot runs flat until the e's outer curve crosses the baseline, so they meet cleanly
_hits = _e_in_ae.exterior.intersection(LineString([(210 + H - 5, 0), (420, 0)]))
_cross = min(q.x for q in getattr(_hits, "geoms", [_hits]))
_ae = unary_union([G["a"][1], _e_in_ae]).difference(box(210 - H, -50, _cross, 0))
_notch = box(210 + H - 1, 0, _cross, 12).difference(_ae)     # sliver between stem foot and e curve
g("ae", 0xE6, unary_union([_ae, _notch]))

# ================================================================ v1.5: Latin-1 / Windows-1252
def tilde_m(cx, y):
    return stroke(bz((cx - 95, y + 10), (cx - 50, y + 175), (cx + 50, y - 55), (cx + 95, y + 110)), 62)


def ring_m(cx, y):
    return ring(cx, y + 62, 46, 52, 42)


def caron(cx, y):
    return stroke([(cx - 85, y + 115), (cx, y + 8), (cx + 85, y + 115)], 66, "bevel")


def macron_m(cx, y):
    return stroke([(cx - 85, y + 50), (cx + 85, y + 50)], 66)


MARKS.update({"tilde": tilde_m, "ring": ring_m, "caron": caron})
MORE = {
    ("a", "tilde"): 0xE3, ("a", "ring"): 0xE5, ("o", "tilde"): 0xF5, ("o", "grave"): 0xF2,
    ("n", "tilde"): 0xF1, ("dotlessi", "grave"): 0xEC, ("dotlessi", "acute"): 0xED,
    ("A", "tilde"): 0xC3, ("A", "ring"): 0xC5, ("O", "tilde"): 0xD5, ("O", "grave"): 0xD2,
    ("N", "tilde"): 0xD1, ("I", "grave"): 0xCC, ("I", "acute"): 0xCD,
    ("y", "acute"): 0xFD, ("y", "dieresis"): 0xFF, ("Y", "acute"): 0xDD, ("Y", "dieresis"): 0x178,
    ("s", "caron"): 0x161, ("S", "caron"): 0x160, ("z", "caron"): 0x17E, ("Z", "caron"): 0x17D,
}
for (base, mark), cp in MORE.items():
    bgeom = G[base][1]
    minx, _, maxx, _ = bgeom.bounds
    cx = (minx + maxx) / 2
    y = 640 if base.islower() or base == "dotlessi" else 820
    if base == "A" and mark == "ring":
        y = 800
    name = (base if base != "dotlessi" else "i") + mark
    g(name, cp, bgeom, MARKS[mark](cx, y))

# --- new letters
g("oslash", 0xF8, G["o"][1], stroke([(20, -40), (230, 600)], 60))
g("Oslash", 0xD8, G["O"][1], stroke([(25, -50), (305, 810)], 66))
g("germandbls", 0xDF, stroke(path((H, 0), (H, 590), bz((H, 590), (H, 810), (232, 810), (232, 630)),
                                  bz((232, 630), (232, 500), (150, 470), (120, 452)))),
  stroke(bz((120, 452), (300, 430), (300, 15), (110, 35))))
g("AE", 0xC6, stroke([(10, -20), (225, CAP + 30)]), stem(225, 0, CAP),
  stroke([(80, 250), (225, 250)], WB), stroke([(225, BT), (420, BT)], BAR),
  stroke([(225, 400), (385, 400)], WB), stroke([(225, BB), (430, BB)], BAR), lo=0, hi=CAP)
g("Eth", 0xD0, G["D"][1], stroke([(0, 380), (140, 380)], WB))
g("eth", 0xF0, ring(125, 260, 83, 218 + OV),
  stroke(bz((205, 330), (215, 560), (150, 720), (60, 790)), 74),
  stroke([(80, 690), (210, 750)], 60))
g("Thorn", 0xDE, stem(H, 0, CAP), stroke(bz((H, 600), (300, 610), (300, 170), (H, 185))))
g("thorn", 0xFE, stem(H, DSC, ASC), stroke(bowl_b))
g("mu", 0xB5, G["u"][1], stem(H, DSC, 200))
g("florin", 0x192, G["f.ss01"][1])

# --- ASCII symbols
g("dollar", ord("$"), G["S"][1], stroke([(132, -90), (132, CAP + 90)], 60))
g("less", ord("<"), stroke([(250, 520), (30, 300), (250, 80)]))
g("greater", ord(">"), stroke([(30, 520), (250, 300), (30, 80)]))
g("backslash", ord("\\"), stroke([(0, 820), (260, -140)]), lo=-140, hi=800)
g("asciicircum", ord("^"), stroke([(10, 480), (130, 740), (250, 480)], 70), hi=760)
g("grave", ord("`"), grave(70, 640))
g("braceleft", ord("{"), stroke(path(bz((190, 820), (90, 820), (100, 700), (100, 560)),
                                       bz((100, 560), (100, 380), (80, 310), (20, 310)))),
  stroke(path(bz((20, 310), (80, 310), (100, 240), (100, 60)),
              bz((100, 60), (100, -80), (90, -200), (190, -200)))))
g("braceright", ord("}"), affinity.scale(G["braceleft"][1], -1, 1, origin=(105, 0)))
g("bar", ord("|"), stem(60, -200, 820, 70))
g("asciitilde", ord("~"), affinity.scale(tilde_m(140, 240), 1.35, 1.35, origin=(140, 290)))

# --- Latin-1 punctuation and signs
g("exclamdown", 0xA1, rot180(G["exclam"][1], 120, 760 - 200))
g("questiondown", 0xBF, rot180(G["question"][1], 280, 760 - 200))
g("cent", 0xA2, G["c"][1], stroke([(135, -80), (135, 640)], 56))
g("currency", 0xA4, ring(150, 300, 95, 95, 64),
  *[stroke([(150 + 95 * math.cos(a), 300 + 95 * math.sin(a)), (150 + 165 * math.cos(a), 300 + 165 * math.sin(a))], 60)
    for a in (math.pi / 4, 3 * math.pi / 4, 5 * math.pi / 4, 7 * math.pi / 4)])
g("yen", 0xA5, G["Y"][1], stroke([(40, 300), (270, 300)], WB - 10), stroke([(40, 160), (270, 160)], WB - 10))
g("brokenbar", 0xA6, stem(60, -200, 260, 70), stem(60, 360, 820, 70))
g("section", 0xA7, affinity.translate(affinity.scale(G["s"][1], 1, 0.82, origin=(0, 0)), 0, 330),
  affinity.translate(affinity.scale(G["s"][1], 1, 0.82, origin=(0, 0)), 0, -100), lo=-120, hi=820)
g("dieresis", 0xA8, diaer(110, 640))
g("copyright", 0xA9, ring(380, 380, 330, 330, 56),
  affinity.translate(affinity.scale(G["C"][1], 0.5, 0.5, origin=(0, 0)), 300, 190).buffer(10, join_style=2))
g("registered", 0xAE, ring(380, 380, 330, 330, 56),
  affinity.translate(affinity.scale(G["R"][1], 0.5, 0.5, origin=(0, 0)), 295, 190).buffer(10, join_style=2))
g("logicalnot", 0xAC, stroke([(10, 380), (260, 380), (260, 220)], WB))
g("macron", 0xAF, macron_m(110, 640))
g("degree", 0xB0, ring(110, 640, 72, 72, 52))
g("plusminus", 0xB1, stroke([(10, 360), (270, 360)], WB), stroke([(140, 230), (140, 490)], WB),
  stroke([(10, 100), (270, 100)], WB))
g("acute", 0xB4, acute(90, 640))
_bowl = affinity.translate(affinity.scale(Point(0, 0).buffer(1, 64), 100, 190, origin=(0, 0)), 135, 570)
g("paragraph", 0xB6, stem(170, -150, CAP, 70), stem(290, -150, CAP, 70),
  _bowl.intersection(box(-1000, -1000, 140, 2000)))
g("cedilla", 0xB8, cedilla(90))
g("ordfeminine", 0xAA, affinity.translate(lighten(G["a"][1], 0.6), 20, 420),
  stroke([(20, 370), (190, 370)], 44))
g("ordmasculine", 0xBA, affinity.translate(lighten(G["o"][1], 0.6), 20, 420),
  stroke([(20, 370), (190, 370)], 44))
g("guillemotleft", 0xAB, stroke([(140, 480), (30, 300), (140, 120)], 66), stroke([(270, 480), (160, 300), (270, 120)], 66))
g("guillemotright", 0xBB, stroke([(30, 480), (140, 300), (30, 120)], 66), stroke([(160, 480), (270, 300), (160, 120)], 66))
g("guilsinglleft", 0x2039, stroke([(140, 480), (30, 300), (140, 120)], 66))
g("guilsinglright", 0x203A, stroke([(30, 480), (140, 300), (30, 120)], 66))
g("multiply", 0xD7, stroke([(30, 170), (250, 430)], WB), stroke([(30, 430), (250, 170)], WB))
g("divide", 0xF7, stroke([(10, 300), (270, 300)], WB), dot(140, 400, h=95, wb=70, wt=96), dot(140, 105, h=95, wb=70, wt=96))


def sup(name, dx=0, y=400, k=SUP_K):
    gm = lighten(G[name][1], k)
    minx = gm.bounds[0]
    return affinity.translate(gm, -minx + dx, y)


g("onesuperior", 0xB9, sup("one"))
g("twosuperior", 0xB2, sup("two"))
g("threesuperior", 0xB3, sup("three"))
_fs = stroke([(40, -20), (330, 740)], 56)
g("onequarter", 0xBC, sup("one", 0), _fs, sup("four", 250, 0))
g("onehalf", 0xBD, sup("one", 0), _fs, sup("two", 250, 0))
g("threequarters", 0xBE, sup("three", 0), affinity.translate(_fs, 40, 0), sup("four", 290, 0))
g("uni00A0", 0xA0)

# --- Windows-1252 extras
g("quotesinglbase", 0x201A, affinity.translate(qr(70), 0, -640))
g("quotedblbase", 0x201E, affinity.translate(unary_union([qr(70), qr(190)]), 0, -640))
g("dagger", 0x2020, stem(130, -150, CAP), stroke([(10, 560), (250, 560)], WB))
g("daggerdbl", 0x2021, stem(130, -150, CAP), stroke([(10, 560), (250, 560)], WB), stroke([(10, 120), (250, 120)], WB))
g("bullet", 0x2022, Point(110, 300).buffer(90, 64))
g("perthousand", 0x2030, G["percent"][1], ring(420, 140, 45, 110, 64))
g("trademark", 0x2122, affinity.translate(affinity.scale(G["T"][1], 0.45, 0.45, origin=(0, 0)), 0, 420).buffer(14, join_style=2),
  affinity.translate(affinity.scale(G["M"][1], 0.45, 0.45, origin=(0, 0)), 170, 420).buffer(14, join_style=2))
g("circumflex", 0x2C6, circ(110, 640))
g("tilde", 0x2DC, tilde_m(120, 640))

# ================================================================ v2.0: Google Fonts Latin Core
def breve(cx, y):
    return stroke(bz((cx - 82, y + 118), (cx - 72, y + 8), (cx + 72, y + 8), (cx + 82, y + 118)), 62)


def dotabove(cx, y):
    return dot(cx, y, h=100, wb=72, wt=108)


def hungarumlaut(cx, y):
    return unary_union([stroke([(cx - 80, y), (cx - 15, y + 125)], 62),
                        stroke([(cx + 15, y), (cx + 80, y + 125)], 62)])


_comma_small = affinity.scale(unary_union([dot(60, 0), stroke(bz((60, 20), (62, -60), (45, -120), (5, -160)), 70)]),
                              0.78, 0.78, origin=(60, 110))


def commabelow(cx):
    return affinity.translate(_comma_small, cx - 60, -160)


def commaturned(cx, y):
    return affinity.translate(affinity.rotate(_comma_small, 180, origin=(60, 0)), cx - 60, y + 20)


def ogonek(x):
    return stroke(bz((x, 35), (x - 58, -40), (x - 52, -175), (x + 48, -188)), 62)


def apostrophe_caron(x, y):
    """A tapered wedge: wide at the top like the font's dots, narrowing as it leans left."""
    return Polygon([(x - 36, y + 165), (x + 44, y + 165), (x + 6, y + 5), (x - 24, y + 5)])


MARKS.update({"macron": macron_m, "breve": breve, "dotaccent": dotabove, "hungarumlaut": hungarumlaut})
ASCENDER_BASES = {"l", "d", "h", "k", "b", "t", "f"}


def _cx(name):
    minx, _, maxx, _ = G[name][1].bounds
    return (minx + maxx) / 2


def _top_y(base):
    if base in ASCENDER_BASES:
        return 860
    return 640 if (base.islower() or base in ("dotlessi", "dotlessj")) else 820


g("dotlessj", 0x237, stroke(path((110, XH), bz((110, 60), (110, -70), (80, -140), (0, -180)))))

ABOVE = [  # (base, mark, codepoint)
    ("A", "macron", 0x100), ("a", "macron", 0x101), ("A", "breve", 0x102), ("a", "breve", 0x103),
    ("C", "acute", 0x106), ("c", "acute", 0x107), ("C", "dotaccent", 0x10A), ("c", "dotaccent", 0x10B),
    ("C", "caron", 0x10C), ("c", "caron", 0x10D), ("D", "caron", 0x10E),
    ("E", "macron", 0x112), ("e", "macron", 0x113), ("E", "dotaccent", 0x116), ("e", "dotaccent", 0x117),
    ("E", "caron", 0x11A), ("e", "caron", 0x11B), ("G", "breve", 0x11E), ("g", "breve", 0x11F),
    ("G", "dotaccent", 0x120), ("g", "dotaccent", 0x121),
    ("I", "macron", 0x12A), ("dotlessi", "macron", 0x12B), ("I", "dotaccent", 0x130),
    ("L", "acute", 0x139), ("l", "acute", 0x13A),
    ("N", "acute", 0x143), ("n", "acute", 0x144), ("N", "caron", 0x147), ("n", "caron", 0x148),
    ("O", "hungarumlaut", 0x150), ("o", "hungarumlaut", 0x151),
    ("R", "acute", 0x154), ("r", "acute", 0x155), ("R", "caron", 0x158), ("r", "caron", 0x159),
    ("S", "acute", 0x15A), ("s", "acute", 0x15B), ("T", "caron", 0x164),
    ("U", "macron", 0x16A), ("u", "macron", 0x16B), ("U", "ring", 0x16E), ("u", "ring", 0x16F),
    ("U", "hungarumlaut", 0x170), ("u", "hungarumlaut", 0x171),
    ("W", "circumflex", 0x174), ("w", "circumflex", 0x175), ("Y", "circumflex", 0x176), ("y", "circumflex", 0x177),
    ("Z", "acute", 0x179), ("z", "acute", 0x17A), ("Z", "dotaccent", 0x17B), ("z", "dotaccent", 0x17C),
    ("W", "grave", 0x1E80), ("w", "grave", 0x1E81), ("W", "acute", 0x1E82), ("w", "acute", 0x1E83),
    ("W", "dieresis", 0x1E84), ("w", "dieresis", 0x1E85), ("Y", "grave", 0x1EF2), ("y", "grave", 0x1EF3),
]
for base, mark, cp in ABOVE:
    name = ("i" if base == "dotlessi" else base) + mark
    g(name, cp, G[base][1], MARKS[mark](_cx(base), _top_y(base)))

BELOW = [  # (base, kind, codepoint, glyph name)
    ("G", "comma", 0x122, "Gcommaaccent"), ("K", "comma", 0x136, "Kcommaaccent"), ("k", "comma", 0x137, "kcommaaccent"),
    ("L", "comma", 0x13B, "Lcommaaccent"), ("l", "comma", 0x13C, "lcommaaccent"),
    ("N", "comma", 0x145, "Ncommaaccent"), ("n", "comma", 0x146, "ncommaaccent"),
    ("S", "cedilla", 0x15E, "Scedilla"), ("s", "cedilla", 0x15F, "scedilla"),
    ("S", "comma", 0x218, "Scommaaccent"), ("s", "comma", 0x219, "scommaaccent"),
    ("T", "comma", 0x21A, "Tcommaaccent"), ("t", "comma", 0x21B, "tcommaaccent"),
    ("T", "cedilla", 0x162, "Tcedilla"), ("t", "cedilla", 0x163, "tcedilla"),
]
for base, kind, cp, name in BELOW:
    cx = _cx(base) + (25 if base == "t" else 0)
    if kind == "cedilla" and base == "t":
        cx = H        # ţ: the cedilla hangs from the stem, as on Ţ
    g(name, cp, G[base][1], commabelow(cx) if kind == "comma" else cedilla(cx + 10))
_tc = commaturned(_cx("g"), 0)     # ģ: the turned comma floats clear of the bowl, like the other accents on g
g("gcommaaccent", 0x123, G["g"][1], affinity.translate(_tc, 0, G["g"][1].bounds[3] + 50 - _tc.bounds[1]))


def _ogonek_x(base):
    minx, _, maxx, _ = G[base][1].bounds
    return {"a": maxx - 40, "e": maxx - 75, "i": (minx + maxx) / 2 + 5, "u": maxx - 40,
            "A": maxx - 55, "E": maxx - 95, "I": (minx + maxx) / 2 + 5, "U": maxx - 80}[base]


for base, cp_up, cp_lo in (("A", 0x104, 0x105), ("E", 0x118, 0x119), ("I", 0x12E, 0x12F), ("U", 0x172, 0x173)):
    g(base + "ogonek", cp_up, G[base][1], ogonek(_ogonek_x(base)))
    lo = base.lower()
    g(lo + "ogonek", cp_lo, G[lo][1], ogonek(_ogonek_x(lo)))

# apostrophe-style carons on ascenders
g("dcaron", 0x10F, G["d"][1], apostrophe_caron(300, 640))
g("lcaron", 0x13E, G["l"][1], apostrophe_caron(140, 640))
g("tcaron", 0x165, G["t"][1], apostrophe_caron(165, 640))
g("Lcaron", 0x13D, G["L"][1], apostrophe_caron(160, 600))
SELF_SPACED = {"dcaron", "lcaron", "tcaron"}

# stroked letters
g("Dcroat", 0x110, G["Eth"][1])
g("dcroat", 0x111, G["d"][1], stroke([(118, 690), (300, 690)], WB))
g("Hbar", 0x126, G["H"][1], stroke([(-34, 595), (346, 595)], WB))
g("hbar", 0x127, G["h"][1], stroke([(-10, 690), (165, 690)], WB))
g("Lslash", 0x141, G["L"][1], stroke([(-10, 300), (175, 470)], WB))
g("lslash", 0x142, G["l"][1], stroke([(-45, 320), (130, 490)], WB))
g("uni1E9E", 0x1E9E, stroke(path((H, 0), (H, 590), bz((H, 590), (H, 735), (110, TC), (180, TC)), (285, TC), (160, 445))),
  stroke(bz((160, 445), (330, 450), (330, 15), (120, 40))))
g("minus", 0x2212, stroke([(10, 300), (270, 300)], WB))

# spacing accents
g("caron", 0x2C7, caron(110, 640))
g("breve", 0x2D8, breve(110, 640))
g("dotaccent", 0x2D9, dotabove(70, 640))
g("ring", 0x2DA, ring_m(80, 640))
g("ogonek", 0x2DB, ogonek(120))
g("hungarumlaut", 0x2DD, hungarumlaut(110, 640))

# combining accents: zero width, drawn about x = 0, attached through anchors
COMBINING = {
    "gravecomb": (0x300, lambda: grave(0, 640), "top"), "acutecomb": (0x301, lambda: acute(0, 640), "top"),
    "uni0302": (0x302, lambda: circ(0, 640), "top"), "tildecomb": (0x303, lambda: tilde_m(0, 640), "top"),
    "uni0304": (0x304, lambda: macron_m(0, 640), "top"), "uni0306": (0x306, lambda: breve(0, 640), "top"),
    "uni0307": (0x307, lambda: dotabove(0, 640), "top"), "uni0308": (0x308, lambda: diaer(0, 640), "top"),
    "uni030A": (0x30A, lambda: ring_m(0, 640), "top"), "uni030B": (0x30B, lambda: hungarumlaut(0, 640), "top"),
    "uni030C": (0x30C, lambda: caron(0, 640), "top"), "uni0326": (0x326, lambda: commabelow(0), "bottom"),
    "uni0327": (0x327, lambda: cedilla(0), "bottom"), "uni0328": (0x328, lambda: ogonek(0), "ogonek"),
}
for name, (cp, fn, _) in COMBINING.items():
    g(name, cp, fn())


g("iogonek.dotless", None, G["dotlessi"][1], ogonek(_ogonek_x("i")))
g("uni25CC", 0x25CC, *[Point(170 + 150 * math.cos(2 * math.pi * k / 12), 300 + 150 * math.sin(2 * math.pi * k / 12)).buffer(20, 16)
                        for k in range(12)])


def anchors_for(name):
    """Anchors for mark attachment, in the glyph's own drawing coordinates."""
    if name in COMBINING:
        kind = COMBINING[name][2]
        return {"_" + kind: (0, 560 if kind == "top" else 0)}
    if name == "uni25CC":
        return {"top": (170, 560), "bottom": (170, 0), "ogonek": (230, 0)}
    uni = G[name][0]
    ch = chr(uni) if uni else ""
    if not (name in ("dotlessi", "dotlessj") or (ch.isalpha() and len(name) == 1)):
        return {}
    minx, _, maxx, _ = G[name][1].bounds
    cx = (minx + maxx) / 2
    top = 780 if name in ASCENDER_BASES else (560 if (name.islower() or name.startswith("dotless")) else 740)
    out = {"top": (cx, top), "bottom": (cx, 0)}
    if name in ("a", "e", "i", "u", "A", "E", "I", "U"):
        out["ogonek"] = (_ogonek_x(name), 0)
    return out

# margins (lsb, rsb) — tighter for diagonals and open shapes
SPACING = {k: (40, 40) for k in G}
for k in "vwxyzAVWXYZT7kKr":
    pass
for name in ["v", "w", "x", "y", "A", "V", "W", "X", "Y", "T", "seven"]:
    SPACING[name] = (18, 18)
for name in ["r", "c", "f", "k", "K", "t", "C", "G", "E", "F", "L", "P", "parenleft", "j"]:
    SPACING[name] = (SPACING[name][0], 22)
for name in ["o", "e", "O", "zero", "six", "nine", "eight", "s", "S", "a", "d", "q", "g"]:
    SPACING[name] = (30, 34)
for name in ["periodcentered", "period", "comma", "colon", "semicolon", "exclam", "quoteright", "quoteleft",
             "quotedblright", "quotedblleft", "quotesingle", "quotedbl", "ellipsis"]:
    SPACING[name] = (25, 25)
SPACING["f.ss01"] = (28, 22)
SPACE_WIDTH = 210

# ---------------------------------------------------------------- all-caps forms (case feature)
# Dashes, guillemets and the middle dot are centred on the x-height for lowercase;
# these copies are centred on the cap height for text set in capitals.
CASE = ["hyphen", "endash", "emdash", "guillemotleft", "guillemotright", "guilsinglleft",
        "guilsinglright", "periodcentered", "bullet"]
for _n in CASE:
    if _n in G:
        _b = G[_n][1].bounds
        g(_n + ".case", None, affinity.translate(G[_n][1], 0, CAP / 2 - (_b[1] + _b[3]) / 2))
