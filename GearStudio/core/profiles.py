"""Bounded two-dimensional vector previews, never triangle meshes.

Cylindrical axial sections sample the same generating profile as the B-rep
builder. Native surfaces and interpolating splines are still approximations to
those mathematical curves. Spatial families show labeled envelopes only.
"""
import math

from .validation import CYLINDRICAL, RACKS, BEVELS, MAX_PREVIEW_POINTS, validate

TAU = 2 * math.pi


def polar(radius, angle):
    return [radius * math.cos(angle), radius * math.sin(angle)]


def circle(radius, points=128):
    """Closed-path sample, without a duplicate closing vertex."""
    if not math.isfinite(radius) or radius <= 0:
        raise ValueError("Circle radius must be positive and finite.")
    points = max(12, min(256, int(points)))
    return [polar(radius, TAU * i / points) for i in range(points)]


def involute_point(base_radius, parameter):
    """Analytic involute of a circle, with dimensionless roll parameter."""
    if not (math.isfinite(base_radius) and math.isfinite(parameter)) or base_radius <= 0 or parameter < 0:
        raise ValueError("Involute radius must be positive and roll parameter nonnegative.")
    c, s = math.cos(parameter), math.sin(parameter)
    return [base_radius * (c + parameter * s), base_radius * (s - parameter * c)]


def _append(points, point):
    if not all(math.isfinite(c) for c in point):
        raise ValueError("The preview curve contains a nonfinite coordinate.")
    if not points or math.hypot(point[0] - points[-1][0], point[1] - points[-1][1]) > 1e-8:
        points.append(point)


def _dedupe_closed(points):
    clean = []
    for p in points:
        _append(clean, p)
    if len(clean) > 1 and math.dist(clean[0], clean[-1]) < 1e-8:
        clean.pop()
    return clean


def _arc(points, radius, start, end, steps=3):
    for i in range(1, steps + 1):
        _append(points, polar(radius, start + (end - start) * i / steps))


def _repeat_flank(flank, teeth):
    """Repeat a tip-to-root lower flank around the shaft.

    This also works for internal cavities, whose material is outside the path.
    All joins are short connecting segments or sampled circle arcs.
    """
    root_angle = math.atan2(flank[-1][1], flank[-1][0])
    tip_angle = math.atan2(flank[0][1], flank[0][0])
    root_radius = math.hypot(*flank[-1])
    tip_radius = math.hypot(*flank[0])
    if not (-math.pi / teeth < root_angle < tip_angle <= 1e-8):
        raise ValueError("The flank does not fit into one non-overlapping tooth pitch.")
    single = list(reversed(flank))
    _arc(single, tip_radius, tip_angle, -tip_angle, 3)
    for x, y in flank[1:]:
        _append(single, [x, -y])
    # Close the bottom land to the next tooth's lower flank.
    _arc(single, root_radius, -root_angle, TAU / teeth + root_angle, 3)
    result = []
    for i in range(teeth):
        a = TAU * i / teeth
        c, s = math.cos(a), math.sin(a)
        for x, y in single:
            _append(result, [x * c - y * s, x * s + y * c])
    return _dedupe_closed(result)


def _generated_cylindrical(kind, v):
    # Import only pure math modules. In Fusion GearStudio is imported as a
    # package; local tests may put GearStudio directly on sys.path.
    try:
        from ..vendor.study_gears.gear_curve import GearParams, gear_curve
        from ..vendor.study_gears.guard import bounded
    except ImportError:
        from vendor.study_gears.gear_curve import GearParams, gear_curve
        from vendor.study_gears.guard import bounded
    beta = math.radians(v.get("helix_angle", 0))
    cb = math.cos(beta)
    inner = kind.startswith("internal_")
    params = GearParams(m=v["module"] / cb, z=int(v["teeth"]),
                        alpha=math.atan(math.tan(math.radians(v["pressure_angle"])) / cb),
                        shift=v.get("profile_shift", 0) * cb,
                        fillet=v.get("root_fillet", 0) * cb,
                        mf=v["dedendum"] * cb, mk=v["addendum"] * cb,
                        rc=(v["dedendum"] - v["addendum"]) * cb,
                        backlash=v["backlash"] / cb * (-1 if inner else 1), inner=inner)
    flank = []
    # A preview cannot consume the native build's larger time allowance.
    with bounded(seconds=0.35, iterations=120000):
        for curve, start, end, count in gear_curve(params):
            steps = 12
            for i in range(steps + 1):
                t = start + (end - start) * i / steps
                if callable(curve):
                    p = curve(t)
                    point = [p.x, p.y]
                else:
                    point = [curve.x + count * math.cos(t), curve.y + count * math.sin(t)]
                _append(flank, point)
    return _repeat_flank(flank, int(v["teeth"]))


def _analytic_cylindrical(kind, v, metrics):
    """Fallback involute section with radial root extensions, clearly labeled."""
    teeth = int(v["teeth"])
    internal = kind.startswith("internal_")
    rp, rb = metrics["pitch_diameter"] / 2, metrics["base_diameter"] / 2
    tip = (metrics["root_diameter"] if internal else metrics["tip_diameter"]) / 2
    root = (metrics["tip_diameter"] if internal else metrics["root_diameter"]) / 2
    thickness = metrics["circular_pitch"] - metrics["tooth_thickness"] if internal else metrics["tooth_thickness"]
    alpha = math.radians(metrics["transverse_pressure_angle"])
    start = max(root, rb)
    half_at_base = thickness / (2 * rp) + math.tan(alpha) - alpha
    flank = []
    for i in range(25):
        radius = tip + (start - tip) * i / 24
        a = math.acos(max(-1.0, min(1.0, rb / radius)))
        half = half_at_base - (math.tan(a) - a)
        _append(flank, polar(radius, -half))
    if root < rb:
        _append(flank, polar(root, -half_at_base))
    return _repeat_flank(flank, teeth)


def _rack(v, metrics):
    pitch = metrics["circular_pitch"]
    count = int(v["teeth"])
    length = pitch * count
    tip = metrics["tip_height"]
    root = -metrics["root_depth"]
    pa = math.radians(metrics["transverse_pressure_angle"])
    half_tip = metrics["tooth_thickness"] / 2 - tip * math.tan(pa)
    half_root = min(pitch / 2, metrics["tooth_thickness"] / 2 - root * math.tan(pa))
    points = [[-length / 2, -v["rack_height"]], [length / 2, -v["rack_height"]], [length / 2, root]]
    for i in range(count - 1, -1, -1):
        x = -length / 2 + (i + 0.5) * pitch
        for p in ([x + half_root, root], [x + half_tip, tip], [x - half_tip, tip], [x - half_root, root]):
            _append(points, p)
    _append(points, [-length / 2, root])
    return _dedupe_closed(points)


def preview(spec, values):
    """Produce cheap engineering vectors after pure preflight.

    Invalid definitions return an empty explicit preview; they cannot accidentally
    proceed through the more involved generating-profile calculations.
    """
    checked = validate(spec, values)
    if not checked["valid"]:
        return {"paths": [], "bounds": [-1, -1, 1, 1], "valid": False,
                "label": "Correct the highlighted inputs to preview.", "simplified": True}
    kind = spec["kind"]
    v = {k: float(values[k]) for k in spec["parameters"] if k in values}
    metrics = checked["metrics"]
    paths = []
    simplified = False

    def path(points, role="outline", closed=True):
        clean = _dedupe_closed(points) if closed else points
        if len(clean) >= (3 if closed else 2):
            paths.append({"points": clean, "closed": closed, "role": role})

    if kind in CYLINDRICAL:
        try:
            outline = _generated_cylindrical(kind, v)
            label = "Axial section: sampled generated tooth profile."
        except (ImportError, RuntimeError, ValueError, ArithmeticError, IndexError):
            outline = _analytic_cylindrical(kind, v, metrics)
            label = "Axial involute preview with simplified roots. Full generated roots appear after build."
            simplified = True
        if kind.startswith("internal_"):
            path(circle(v["outside_diameter"] / 2))
            path(outline, "cutout")
        else:
            path(outline)
            if v.get("bore", 0) > 0:
                path(circle(v["bore"] / 2, 64), "cutout")
        path(circle(metrics["pitch_diameter"] / 2), "construction")
        if "helical" in kind or "herringbone" in kind:
            label += " Helical trace is not shown in this section."
    elif kind in RACKS:
        path(_rack(v, metrics))
        path([[-metrics["rack_length"] / 2, 0], [metrics["rack_length"] / 2, 0]], "construction", False)
        label = "Rack reference section; root fillets and tooth-trace skew are simplified."
        simplified = True
    elif kind == "worm":
        w = v["width"] / 2
        r = metrics["tip_diameter"] / 2
        rf = metrics["root_diameter"] / 2
        path([[-w, -r], [w, -r], [w, r], [-w, r]])
        for y in (-rf, rf, 0):
            path([[-w, y], [w, y]], "construction", False)
        label = "Worm side envelope. Generated helical threads appear after build."
        simplified = True
    elif kind in BEVELS:
        delta = math.radians(metrics["pitch_cone_angle"])
        cone = metrics["cone_distance"]
        inner = cone - v["width"]
        outer_radius = metrics["tip_diameter"] / 2
        inner_radius = outer_radius * inner / cone
        z0 = -cone * math.cos(delta)
        z1 = -inner * math.cos(delta)
        path([[z0, -outer_radius], [z1, -inner_radius], [z1, inner_radius], [z0, outer_radius]])
        path([[z0, -cone * math.sin(delta)], [0, 0], [z0, cone * math.sin(delta)]], "construction", False)
        label = "Pitch-cone side envelope. Spherical tooth profiles appear after build."
        simplified = True
    elif kind == "crown":
        path(circle(metrics["outside_diameter"] / 2))
        path(circle(metrics["inner_face_diameter"] / 2), "construction")
        path(circle(metrics["pitch_diameter"] / 2), "construction")
        if v["bore"] > 0:
            path(circle(v["bore"] / 2, 64), "cutout")
        label = "Crown face envelope. Generated tooth surfaces appear after build."
        simplified = True
    else:  # worm_wheel
        path(circle(metrics["tip_diameter"] / 2))
        path(circle(metrics["pitch_diameter"] / 2), "construction")
        if v.get("bore", 0) > 0:
            path(circle(v["bore"] / 2, 64), "cutout")
        label = "Worm-wheel axial envelope. The generated throat and teeth appear after build."
        simplified = True
    all_points = [p for item in paths for p in item["points"]]
    if len(all_points) > MAX_PREVIEW_POINTS:
        raise ValueError("The vector preview exceeded its bounded point budget.")
    bounds = [min(p[0] for p in all_points), min(p[1] for p in all_points),
              max(p[0] for p in all_points), max(p[1] for p in all_points)] if all_points else [-1, -1, 1, 1]
    return {"paths": paths, "bounds": bounds, "valid": True, "label": label,
            "simplified": simplified, "units": "mm", "pointCount": len(all_points),
            "representation": "2D vector preview of B-rep design"}
