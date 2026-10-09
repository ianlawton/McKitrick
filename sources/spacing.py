"""Optical spacing and kerning for McKitrick, measured from the glyph outlines.

Sidebearings are set from each glyph's profile inside its core zone (x-height for
lowercase, cap height for capitals), not from its bounding box. Overhangs outside
that zone — the j and g hooks, the f's top, descenders — are free to tuck under or
over neighbours. Kerning then corrects pair-level gaps and prevents any collision.
"""
from shapely.geometry import box

STEP = 10
Y0, Y1 = -260, 960
BANDS = list(range(Y0, Y1, STEP))

LOWER_ZONE = (0, 560)
CAP_ZONE = (0, 760)
FIG_ZONE = (0, 720)

# (straight-side sidebearing, depth cap, compensation factor)
PARAMS = {
    "lower": (46, 130, 0.62),
    "cap": (52, 170, 0.62),
    "fig": (42, 150, 0.6),
}


def profile(geom):
    """Per-band (minx, maxx) of the outline, None where the band is empty."""
    L, R = {}, {}
    for y in BANDS:
        part = geom.intersection(box(-5000, y, 5000, y + STEP))
        if part.is_empty or part.area < 1:
            L[y] = R[y] = None
        else:
            mn, _, mx, _ = part.bounds
            L[y], R[y] = mn, mx
    return L, R


def zone_of(name, uni):
    ch = chr(uni) if uni else ""
    if uni in (0xAA, 0xBA, 0x192):
        return None, None
    if name in ("dotlessi", "f.ss01") or (ch and ch.isalpha() and ch.islower()) or name in ("oe", "ae"):
        return "lower", LOWER_ZONE
    if ch and ch.isalpha() and ch.isupper() or name in ("OE",):
        return "cap", CAP_ZONE
    if ch and ch in "0123456789":
        return "fig", FIG_ZONE
    return None, None


def side_mean_depth(prof, zone, side, cap):
    ys = [y for y in BANDS if zone[0] <= y < zone[1] and prof[y] is not None]
    if not ys:
        return 0, None
    vals = [prof[y] for y in ys]
    extreme = min(vals) if side == "L" else max(vals)
    depth = [min(abs(v - extreme), cap) for v in vals]
    # empty bands inside the zone count as fully open
    n_zone = len([y for y in BANDS if zone[0] <= y < zone[1]])
    depth += [cap] * (n_zone - len(ys))
    return sum(depth) / len(depth), extreme


def optical_sidebearings(geom, name, uni):
    kind, zone = zone_of(name, uni)
    if kind is None:
        return None
    sb, cap, k = PARAMS[kind]
    L, R = profile(geom)
    dl, exl = side_mean_depth(L, zone, "L", cap)
    dr, exr = side_mean_depth(R, zone, "R", cap)
    if exl is None or exr is None:
        return None
    lsb = max(sb - k * dl, 4)
    rsb = max(sb - k * dr, 4)
    return exl, exr, lsb, rsb


# ------------------------------------------------------------------ kerning
MIN_GAP = 40          # nothing may come closer than this anywhere
KERN_CAP = 150        # depth cap when judging a pair's optical gap
KERN_GAIN = 0.55
KERN_MIN = 12         # ignore corrections smaller than this


def pair_gap_profile(Ra, adv_a, Lb):
    gaps = {}
    for y in BANDS:
        if Ra[y] is not None and Lb[y] is not None:
            gaps[y] = adv_a - Ra[y] + Lb[y]
    return gaps


def kern_value(Ra, adv_a, Lb, zone, ref_gap):
    gaps = pair_gap_profile(Ra, adv_a, Lb)
    if not gaps:
        return 0
    tightest = min(gaps.values())
    # optical gap: mean over the shared zone, each row's gap measured from the
    # pair's tightest point and capped, with open rows counting as capped
    zone_rows = [y for y in BANDS if zone[0] <= y < zone[1]]
    rows = []
    for y in zone_rows:
        g = gaps.get(y)
        rows.append(min(g - tightest, KERN_CAP) if g is not None else KERN_CAP)
    optical = tightest + sum(rows) / len(rows) * 0.62
    k = (ref_gap - optical) * KERN_GAIN
    if abs(k) < KERN_MIN:
        k = 0
    # never collide
    if tightest + k < MIN_GAP:
        k = MIN_GAP - tightest
    return round(k / 5) * 5
