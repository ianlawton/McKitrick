"""Turn dense polygon outlines into clean cubic Bézier contours.

Each closed ring is split at corners (sharp turns such as flat stroke ends and
joins). Straight runs become lines; curved runs are fitted with cubic Béziers
(Philip J. Schneider's algorithm, "An Algorithm for Automatically Fitting
Digitized Curves", Graphics Gems, 1990). Curves are then split at their
horizontal and vertical extremes so every contour has points on its extrema.
"""
import math

CORNER_DEG = 32          # a turn sharper than this is a corner
LINE_TOL = 0.9           # max distance from the chord for a run to count as straight
MIN_BEND = 12            # a short run that turns more than this is a small curve, not a facet
LONG_EDGE = 60           # polygon edges at least this long are kept as straight lines
FIT_TOL = 1.6           # max fitting error, font units


def _sub(a, b): return (a[0] - b[0], a[1] - b[1])
def _add(a, b): return (a[0] + b[0], a[1] + b[1])
def _mul(a, k): return (a[0] * k, a[1] * k)
def _dot(a, b): return a[0] * b[0] + a[1] * b[1]
def _len(a): return math.hypot(a[0], a[1])


def _norm(a):
    L = _len(a)
    return (a[0] / L, a[1] / L) if L else (0.0, 0.0)


def _bez(c, t):
    mt = 1 - t
    return (mt ** 3 * c[0][0] + 3 * mt * mt * t * c[1][0] + 3 * mt * t * t * c[2][0] + t ** 3 * c[3][0],
            mt ** 3 * c[0][1] + 3 * mt * mt * t * c[1][1] + 3 * mt * t * t * c[2][1] + t ** 3 * c[3][1])


def _bez1(c, t):
    mt = 1 - t
    return (3 * mt * mt * (c[1][0] - c[0][0]) + 6 * mt * t * (c[2][0] - c[1][0]) + 3 * t * t * (c[3][0] - c[2][0]),
            3 * mt * mt * (c[1][1] - c[0][1]) + 6 * mt * t * (c[2][1] - c[1][1]) + 3 * t * t * (c[3][1] - c[2][1]))


def _bez2(c, t):
    mt = 1 - t
    return (6 * mt * (c[2][0] - 2 * c[1][0] + c[0][0]) + 6 * t * (c[3][0] - 2 * c[2][0] + c[1][0]),
            6 * mt * (c[2][1] - 2 * c[1][1] + c[0][1]) + 6 * t * (c[3][1] - 2 * c[2][1] + c[1][1]))


def _chord_params(pts):
    u = [0.0]
    for i in range(1, len(pts)):
        u.append(u[-1] + _len(_sub(pts[i], pts[i - 1])))
    total = u[-1] or 1.0
    return [x / total for x in u]


def _generate(pts, u, t1, t2):
    p0, p3 = pts[0], pts[-1]
    C = [[0.0, 0.0], [0.0, 0.0]]
    X = [0.0, 0.0]
    for p, t in zip(pts, u):
        a1 = _mul(t1, 3 * (1 - t) ** 2 * t)
        a2 = _mul(t2, 3 * (1 - t) * t * t)
        C[0][0] += _dot(a1, a1); C[0][1] += _dot(a1, a2); C[1][1] += _dot(a2, a2)
        tmp = _sub(p, _bez((p0, p0, p3, p3), t))
        X[0] += _dot(a1, tmp); X[1] += _dot(a2, tmp)
    C[1][0] = C[0][1]
    det = C[0][0] * C[1][1] - C[0][1] * C[1][0]
    seg = _len(_sub(p3, p0))
    if abs(det) > 1e-12:
        al = (X[0] * C[1][1] - X[1] * C[0][1]) / det
        ar = (C[0][0] * X[1] - C[1][0] * X[0]) / det
    else:
        al = ar = 0
    eps = 1e-6 * seg
    if al < eps or ar < eps:
        al = ar = seg / 3
    return (p0, _add(p0, _mul(t1, al)), _add(p3, _mul(t2, ar)), p3)


def _max_err(pts, c, u):
    worst, idx = 0.0, len(pts) // 2
    for i, (p, t) in enumerate(zip(pts, u)):
        d = _len(_sub(_bez(c, t), p))
        if d > worst:
            worst, idx = d, i
    return worst, idx


def _reparam(pts, c, u):
    out = []
    for p, t in zip(pts, u):
        d = _sub(_bez(c, t), p)
        d1, d2 = _bez1(c, t), _bez2(c, t)
        num = _dot(d, d1)
        den = _dot(d1, d1) + _dot(d, d2)
        out.append(t - num / den if abs(den) > 1e-12 else t)
    return out


def _fit(pts, t1, t2, tol):
    if len(pts) == 2:
        d = _len(_sub(pts[1], pts[0])) / 3
        return [(pts[0], _add(pts[0], _mul(t1, d)), _add(pts[1], _mul(t2, d)), pts[1])]
    u = _chord_params(pts)
    c = _generate(pts, u, t1, t2)
    err, split = _max_err(pts, c, u)
    if err < tol:
        return [c]
    if err < tol * 4:
        for _ in range(12):
            u2 = _reparam(pts, c, u)
            if any(not (-0.1 <= x <= 1.1) for x in u2):
                break
            u = u2
            c = _generate(pts, u, t1, t2)
            err, split = _max_err(pts, c, u)
            if err < tol:
                return [c]
    split = max(1, min(len(pts) - 2, split))
    tc = _norm(_sub(pts[split - 1], pts[split + 1]))
    return (_fit(pts[:split + 1], t1, tc, tol) +
            _fit(pts[split:], _mul(tc, -1), t2, tol))


def _turn(a, b, c):
    v1, v2 = _norm(_sub(b, a)), _norm(_sub(c, b))
    return math.degrees(math.acos(max(-1.0, min(1.0, _dot(v1, v2)))))


def _angle(u, v):
    return math.degrees(math.acos(max(-1.0, min(1.0, _dot(_norm(u), _norm(v))))))


def _dist_to_chord(p, a, b):
    ab = _sub(b, a)
    L = _len(ab)
    if L == 0:
        return _len(_sub(p, a))
    return abs(ab[0] * (a[1] - p[1]) - ab[1] * (a[0] - p[0])) / L


def _split_extrema(c):
    """Split a cubic at its x and y extrema inside (0, 1)."""
    ts = []
    for k in (0, 1):
        a = -c[0][k] + 3 * c[1][k] - 3 * c[2][k] + c[3][k]
        b = 2 * (c[0][k] - 2 * c[1][k] + c[2][k])
        cc = c[1][k] - c[0][k]
        roots = []
        if abs(a) < 1e-9:
            if abs(b) > 1e-9:
                roots = [-cc / b]
        else:
            disc = b * b - 4 * a * cc
            if disc >= 0:
                s = math.sqrt(disc)
                roots = [(-b + s) / (2 * a), (-b - s) / (2 * a)]
        ts += [t for t in roots if 0.04 < t < 0.96]
    ts = sorted(set(round(t, 4) for t in ts))
    out, rest, prev = [], c, 0.0
    for t in ts:
        tt = (t - prev) / (1 - prev)
        p01 = _add(rest[0], _mul(_sub(rest[1], rest[0]), tt))
        p12 = _add(rest[1], _mul(_sub(rest[2], rest[1]), tt))
        p23 = _add(rest[2], _mul(_sub(rest[3], rest[2]), tt))
        q0 = _add(p01, _mul(_sub(p12, p01), tt))
        q1 = _add(p12, _mul(_sub(p23, p12), tt))
        m = _add(q0, _mul(_sub(q1, q0), tt))
        out.append((rest[0], p01, q0, m))
        rest = (m, q1, p23, rest[3])
        prev = t
    out.append(rest)
    return out


def fit_ring(pts, corner_deg=CORNER_DEG, tol=FIT_TOL):
    """pts: closed ring without the repeated last point. Returns a list of segments:
    ("line", p0, p1) or ("curve", p0, c1, c2, p1), in drawing order."""
    clean = []
    for p in pts:
        if not clean or _len(_sub(p, clean[-1])) > 0.05:
            clean.append(p)
    if len(clean) > 1 and _len(_sub(clean[0], clean[-1])) <= 0.05:
        clean.pop()
    # drop points that sit on the straight line between their neighbours, so a
    # straight edge is seen as one edge (and its true length is known)
    k = 0
    while len(clean) > 3 and k < len(clean):
        a_, b_, c_ = clean[k - 1], clean[k], clean[(k + 1) % len(clean)]
        if _dist_to_chord(b_, a_, c_) < 0.02 and _dot(_sub(b_, a_), _sub(c_, b_)) > 0:
            del clean[k]
        else:
            k += 1
    n = len(clean)
    if n < 3:
        return []
    corners = {i for i in range(n) if _turn(clean[i - 1], clean[i], clean[(i + 1) % n]) > corner_deg}
    # A long edge is a drawn straight (a stem or a diagonal), never a sample of a curve:
    # pin both its ends so a shallow join (N's diagonal, the stem entering an arch)
    # can't be smoothed into one bowed curve.
    for i in range(n):
        if _len(_sub(clean[(i + 1) % n], clean[i])) >= LONG_EDGE:
            corners |= {i, (i + 1) % n}
    corners = sorted(corners)
    smooth_close = not corners
    if smooth_close:  # a smooth closed shape (ring, ellipse): split at its four extremes
        ext = {min(range(n), key=lambda i: (clean[i][0], clean[i][1])),
               max(range(n), key=lambda i: (clean[i][1], -clean[i][0])),
               max(range(n), key=lambda i: (clean[i][0], -clean[i][1])),
               min(range(n), key=lambda i: (clean[i][1], clean[i][0]))}
        corners = sorted(ext)
    segs = []
    for k, ci in enumerate(corners):
        cj = corners[(k + 1) % len(corners)]
        run = [clean[ci]]
        i = ci
        while True:
            i = (i + 1) % n
            run.append(clean[i])
            if i == cj:
                break
        flat = len(run) == 2 or max(_dist_to_chord(p, run[0], run[-1]) for p in run[1:-1]) <= LINE_TOL
        bends = len(run) > 2 and _angle(_sub(run[1], run[0]), _sub(run[-1], run[-2])) > MIN_BEND
        if flat and not bends:
            segs.append(("line", run[0], run[-1]))
            continue
        if smooth_close:
            t1 = _norm(_sub(clean[(ci + 1) % n], clean[ci - 1]))
            t2 = _mul(_norm(_sub(clean[(cj + 1) % n], clean[cj - 1])), -1)
        else:
            # where a curve leaves a straight edge without a real corner, carry the
            # edge's direction into the curve so the join is smooth
            t1 = _norm(_sub(run[1], run[0]))
            t2 = _norm(_sub(run[-2], run[-1]))
            if _turn(clean[ci - 1], clean[ci], clean[(ci + 1) % n]) <= corner_deg:
                t1 = _norm(_sub(clean[ci], clean[ci - 1]))
            if _turn(clean[cj - 1], clean[cj], clean[(cj + 1) % n]) <= corner_deg:
                t2 = _mul(_norm(_sub(clean[(cj + 1) % n], clean[cj])), -1)
        for c in _fit(run, t1, t2, tol):
            for cc in _split_extrema(c):
                segs.append(("curve",) + tuple(cc))
    return segs


def round_segments(segs):
    """Round to integers and drop degenerate segments."""
    out = []
    R = lambda p: (int(round(p[0])), int(round(p[1])))
    for s in segs:
        if s[0] == "line":
            a, b = R(s[1]), R(s[2])
            if a != b:
                out.append(("line", a, b))
        else:
            a, c1, c2, b = map(R, s[1:])
            if a == b:
                continue
            if c1 == a and c2 == b:
                out.append(("line", a, b))
            else:
                out.append(("curve", a, c1, c2, b))
    return _merge_collinear(_drop_stubs(out))


def _drop_stubs(segs):
    """Remove straight stubs under 2 units long (rounding leftovers where two edges
    meet), joining the neighbouring segments at one point."""
    i = 0
    while len(segs) > 3 and i < len(segs):
        s = segs[i]
        if s[0] == "line" and math.hypot(s[2][0] - s[1][0], s[2][1] - s[1][1]) < 2:
            j, h = (i + 1) % len(segs), i - 1
            nxt, prv = segs[j], segs[h]
            if nxt[0] == "line" and prv[0] == "curve":
                # keep the straight line exact: let the curve absorb the stub
                segs[h] = prv[:-1] + (s[2],)
            else:
                segs[j] = (nxt[0], s[1]) + tuple(nxt[2:])
            del segs[i]
        else:
            i += 1
    return segs


def _merge_collinear(segs):
    """Join consecutive straight lines that continue in the same direction, so a
    straight edge is a single line with one node at each end."""
    def straight_on(a, b, c):
        cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        dot = (b[0] - a[0]) * (c[0] - b[0]) + (b[1] - a[1]) * (c[1] - b[1])
        return dot > 0 and abs(cross) <= 0.5 * math.hypot(c[0] - a[0], c[1] - a[1])
    changed = True
    while changed and len(segs) > 2:
        changed = False
        for i in range(len(segs)):
            s, t = segs[i], segs[(i + 1) % len(segs)]
            if s[0] == t[0] == "line" and straight_on(s[1], s[2], t[2]):
                j = (i + 1) % len(segs)
                segs[i] = ("line", s[1], t[2])
                del segs[j]
                changed = True
                break
    return segs


def draw_segments(pen, segs):
    if not segs:
        return
    start = segs[0][1]
    pen.moveTo(start)
    for k, s in enumerate(segs):
        last = k == len(segs) - 1
        if s[0] == "line":
            if not (last and s[2] == start):
                pen.lineTo(s[2])
        else:
            pen.curveTo(s[2], s[3], s[4])
    pen.closePath()
