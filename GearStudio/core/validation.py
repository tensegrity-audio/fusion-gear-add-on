"""Bounded, dependency-free preflight for the native B-rep generators.

The envelope below is a supported modeling range, not a strength rating or proof
of mating-pair compatibility. No Fusion operation is needed to reject these inputs.
Reference conventions: KHK Gear Technical Reference, Calculation of Gear
Dimensions; Study Gears gear_curve.py and gear_bevel.py (see third-party notices).
"""
import math
from numbers import Real

from .catalog import FAMILY_BY_ID

MAX_TEETH = 160
MAX_RACK_TEETH = 80
MAX_DIAMETER = 500.0
MAX_COST = 6000
MAX_EXPRESSION_LENGTH = 256
MAX_PREVIEW_POINTS = 12000
# Finite limits also prevent overflows in dependent calculations.
RANGES = {
    "module": (0.1, 20.0), "teeth": (6, MAX_TEETH), "pressure_angle": (14.5, 30.0),
    "width": (0.2, 150.0), "bore": (0.0, MAX_DIAMETER), "backlash": (0.0, 10.0),
    "profile_shift": (-0.25, 0.5), "addendum": (0.8, 1.2), "dedendum": (1.05, 1.6),
    "root_fillet": (0.05, 0.35), "helix_angle": (-45.0, 45.0),
    "outside_diameter": (1.0, MAX_DIAMETER), "rack_height": (0.5, 150.0),
    "worm_diameter": (1.0, 150.0), "worm_starts": (1, 4), "worm_hand": (-1, 1), "mate_teeth": (6, MAX_TEETH),
    "shaft_angle": (30.0, 120.0), "spiral_angle": (-35.0, 35.0), "crown_base": (0.5, 50.0),
}
COUNT_FIELDS = {"teeth", "mate_teeth", "worm_starts", "worm_hand"}
CYLINDRICAL = {"spur", "helical", "herringbone", "internal_spur", "internal_helical", "internal_herringbone"}
RACKS = {"rack", "helical_rack"}
BEVELS = {"bevel", "spiral_bevel"}


def _inv(alpha):
    return math.tan(alpha) - alpha


def dimensions(kind, values):
    """Compute reference dimensions from already validated numeric input.

    Lengths in mm, reported angles in degrees. This helper is intentionally
    separate from expression evaluation. Call validate() before using externally.
    """
    v = values
    m = v["module"]
    z = int(v.get("teeth", 24))
    width = v["width"]
    alpha_n = math.radians(v["pressure_angle"])
    beta = math.radians(v.get("helix_angle", 0)) if kind in CYLINDRICAL | RACKS else 0.0
    if kind == "spiral_bevel":
        beta = math.radians(v["spiral_angle"])
    if kind == "worm_wheel":
        beta = math.asin(v["worm_starts"] * m / v["worm_diameter"]) * v.get("worm_hand", 1)
    cos_beta = math.cos(beta)
    mt = m / cos_beta
    alpha_t = math.atan(math.tan(alpha_n) / cos_beta)
    shift = v.get("profile_shift", 0.0)
    add, ded = v["addendum"], v["dedendum"]
    internal = kind.startswith("internal_")
    sn = math.pi * m / 2 + (-1 if internal else 1) * 2 * shift * m * math.tan(alpha_n) - v["backlash"]
    st = sn / cos_beta
    rp = mt * z / 2
    ra = rp + m * (shift - add if internal else shift + add)
    rf = rp + m * (shift + ded if internal else shift - ded)
    rb = rp * math.cos(alpha_t)
    result = {"pitch_diameter": 2 * rp, "tip_diameter": 2 * ra, "root_diameter": 2 * rf,
              "base_diameter": 2 * rb, "normal_module": m, "transverse_module": mt,
              "transverse_pressure_angle": math.degrees(alpha_t),
              "circular_pitch": math.pi * mt, "normal_tooth_thickness": sn,
              "tooth_thickness": st, "radial_clearance": m * (ded - add),
              "face_width": width}
    if kind in CYLINDRICAL:
        # Informative rack-generated undercut threshold. Actual trochoidal roots
        # are built by the native engine, so below-threshold teeth are warnings.
        equivalent_teeth = z / cos_beta ** 3
        minimum = max(0.0, 2 * (add - shift) / math.sin(alpha_n) ** 2)
        result["virtual_teeth"] = equivalent_teeth
        result["min_teeth_without_undercut"] = math.ceil(minimum * cos_beta ** 3 - 1e-10)
        if beta:
            twist = width * math.tan(beta) / rp
            if "herringbone" in kind:
                twist /= 2
            result["twist_angle"] = math.degrees(twist)
            result["lead"] = 2 * math.pi * rp / abs(math.tan(beta))
        if internal:
            result["ring_rim"] = (v["outside_diameter"] - 2 * rf) / 2
            # Internal tooth gets thinner toward its inward tip.
            if ra >= rb:
                half_tip = st / (2 * rp) - _inv(alpha_t) + _inv(math.acos(rb / ra))
                result["tip_tooth_thickness"] = 2 * ra * half_tip
        elif ra >= rb:
            half_tip = st / (2 * rp) + _inv(alpha_t) - _inv(math.acos(rb / ra))
            result["tip_tooth_thickness"] = 2 * ra * half_tip
        result["bore_ligament"] = rf - v.get("bore", 0) / 2
    if kind in RACKS:
        result = {"rack_length": z * math.pi * mt, "rack_height": v["rack_height"],
                  "tip_height": m * (add + shift), "root_depth": m * (ded - shift),
                  "normal_module": m, "transverse_module": mt,
                  "transverse_pressure_angle": math.degrees(alpha_t),
                  "circular_pitch": math.pi * mt, "normal_tooth_thickness": sn,
                  "tooth_thickness": st, "face_width": width,
                  "radial_clearance": m * (ded - add),
                  "rack_skew": abs(width * math.tan(beta)),
                  "tip_tooth_thickness": st - 2 * m * (add + shift) * math.tan(alpha_t)}
    if kind in ("worm", "worm_wheel"):
        gamma = math.asin(v["worm_starts"] * m / v["worm_diameter"]) * v.get("worm_hand", 1)
        lead = math.pi * m * v["worm_starts"] / math.cos(gamma)
        result["worm_lead_angle"] = math.degrees(gamma)
        result["lead"] = lead
        result["axial_pitch"] = lead / v["worm_starts"]
        if kind == "worm":
            result["pitch_diameter"] = v["worm_diameter"]
            result["tip_diameter"] = v["worm_diameter"] + 2 * m * (add + shift)
            result["root_diameter"] = v["worm_diameter"] - 2 * m * (ded - shift)
            result["bore_ligament"] = (result["root_diameter"] - v.get("bore", 0)) / 2
            result.pop("base_diameter", None)
        else:
            result["centre_distance"] = (result["pitch_diameter"] + v["worm_diameter"]) / 2
    if kind in BEVELS:
        sigma = math.radians(v["shaft_angle"])
        delta = math.atan2(math.sin(sigma), v["mate_teeth"] / z + math.cos(sigma))
        delta_mate = sigma - delta
        cone_distance = rp / math.sin(delta)
        # Match the spherical construction, not the common planar approximation.
        angular_module = math.atan(mt / cone_distance)
        root_delta = delta - ded * cos_beta * angular_module
        tip_delta = delta + add * cos_beta * angular_module
        inner_cone = cone_distance - width
        result.update({"pitch_cone_angle": math.degrees(delta),
                       "mate_pitch_cone_angle": math.degrees(delta_mate),
                       "cone_distance": cone_distance, "inner_cone_distance": inner_cone,
                       "root_cone_angle": math.degrees(root_delta),
                       "tip_diameter": 2 * cone_distance * math.sin(tip_delta),
                       "root_diameter": 2 * cone_distance * math.sin(root_delta),
                       "inner_root_diameter": 2 * inner_cone * math.sin(root_delta),
                       "bore_ligament": inner_cone * math.sin(root_delta) - v.get("bore", 0) / 2})
    if kind == "crown":
        inner = rp - width / 2
        outer = rp + width / 2
        result = {"pitch_diameter": 2 * rp, "inner_face_diameter": 2 * inner,
                  "outside_diameter": 2 * outer, "radial_face_width": width,
                  "generating_pinion_tip_radius": m * (v["mate_teeth"] / 2 + ded),
                  "normal_module": m, "circular_pitch": math.pi * m,
                  "normal_tooth_thickness": sn, "tooth_thickness": sn,
                  "radial_clearance": m * (ded - add),
                  "total_height": v["crown_base"] + m * (add + ded)}
    return result


def validate(spec, values):
    """Return structured errors and cheap dimensions, never mutate inputs."""
    issues = []
    result = {"valid": False, "issues": issues, "metrics": {}, "cost": {}}

    def issue(field, code, message, severity="error"):
        issues.append({"field": field, "code": code, "severity": severity, "message": message})

    if not isinstance(spec, dict):
        issue("", "definition_type", "The gear definition must be an object.")
        return result
    kind = spec.get("kind")
    if not isinstance(kind, str) or kind not in FAMILY_BY_ID:
        issue("kind", "unknown_family", "Choose an available gear family.")
        return result
    if spec.get("schema_version", 1) != 1:
        issue("", "schema_version", "This gear definition uses an unsupported version.")
        return result
    parameters = spec.get("parameters")
    if not isinstance(parameters, dict):
        issue("", "parameters_type", "The gear parameters must be an object.")
        return result
    if not isinstance(values, dict):
        issue("", "values_type", "The evaluated gear values must be an object.")
        return result
    if len(parameters) > 32 or len(values) > 32:
        issue("", "too_many_parameters", "This definition contains too many parameters.")
        return result
    if not isinstance(spec.get("name", "Gear"), str) or len(spec.get("name", "Gear")) > 120:
        issue("name", "name_length", "Use a gear name of at most 120 characters.")
    fields = FAMILY_BY_ID[kind]["fields"]
    for key in fields:
        expression = parameters.get(key)
        if not isinstance(expression, str) or not expression.strip():
            issue(key, "expression_missing", "Enter a value or Fusion parameter expression.")
        elif len(expression) > MAX_EXPRESSION_LENGTH:
            issue(key, "expression_length", "Keep the expression within 256 characters.")
        value = values.get(key)
        if isinstance(value, bool) or not isinstance(value, Real):
            issue(key, "numeric_type", "This expression must resolve to a number.")
            continue
        try:
            finite = math.isfinite(value)
        except (OverflowError, ValueError):
            finite = False
        if not finite:
            issue(key, "nonfinite", "This expression must resolve to a finite number.")
            continue
        low, high = RANGES[key]
        if kind in RACKS and key == "teeth":
            low, high = 1, MAX_RACK_TEETH
        if value < low or value > high:
            issue(key, "range", "Supported range is %g to %g. Change this input before building." % (low, high))
        if key in COUNT_FIELDS and value != int(value):
            issue(key, "integer", "Use a whole number; fractional tooth and start counts cannot be built.")
    # Reject nonfinite/invalid extras too: do not permit unsafe values to bypass
    # field validation through an imported definition.
    for key in values.keys() - set(fields):
        value = values[key]
        if isinstance(value, bool) or not isinstance(value, Real):
            issue(str(key), "numeric_type", "Extra evaluated values must be numbers.")
        else:
            try:
                if not math.isfinite(value):
                    issue(str(key), "nonfinite", "Extra evaluated values must be finite.")
            except (OverflowError, ValueError):
                issue(str(key), "nonfinite", "Extra evaluated values must be finite.")
    if any(i["severity"] == "error" for i in issues):
        return result
    v = {key: float(values[key]) for key in fields}
    m, add, ded = v["module"], v["addendum"], v["dedendum"]
    shift = v.get("profile_shift", 0)
    if ded - add < 0.05:
        issue("dedendum", "radial_clearance", "Dedendum must exceed addendum by at least 0.05 module to leave generating clearance.")
    if "root_fillet" in fields:
        alpha = math.radians(v["pressure_angle"])
        # Cylindrical and wheel profiles use a transverse circular-tool
        # approximation. Reject the two adjustments upstream would otherwise
        # perform silently, so the requested fillet remains an actual input.
        beta = 0.0
        if kind in CYLINDRICAL and "helix_angle" in fields:
            beta = math.radians(v["helix_angle"])
        if kind == "worm_wheel":
            ratio = v["worm_starts"] * m / v["worm_diameter"]
            if ratio < 1:
                beta = math.asin(ratio)
        cb = math.cos(beta)
        at = math.atan(math.tan(alpha) / cb)
        fillet_limit = (ded - add) / (1 - math.sin(at))
        if v["root_fillet"] > fillet_limit + 1e-10:
            issue("root_fillet", "fillet_clearance", "Reduce the root fillet coefficient to at most %.3g, or increase dedendum clearance." % fillet_limit)
        fc_y = v["backlash"] / (2 * cb) - m * ded * math.tan(at) - m * v["root_fillet"] / math.tan((math.pi / 2 + at) / 2)
        if fc_y <= -math.pi * m / (4 * cb) + 1e-7:
            issue("root_fillet", "fillet_centreline", "This generating fillet reaches the tooth-space centreline. Reduce fillet radius, dedendum or pressure angle.")
    if v["backlash"] > 0.35 * m:
        issue("backlash", "backlash_limit", "Tooth thinning exceeds 0.35 module. Reduce thinning or increase module.")
    if "helix_angle" in fields and abs(v["helix_angle"]) < 1:
        issue("helix_angle", "zero_helix", "Use a helix magnitude of at least 1 degree, or choose the straight-tooth family.")
    if kind == "spiral_bevel" and abs(v["spiral_angle"]) < 1:
        issue("spiral_angle", "zero_spiral", "Use a spiral magnitude of at least 1 degree, or choose Straight bevel.")
    if kind in ("worm", "worm_wheel"):
        if v["worm_hand"] not in (-1, 1):
            issue("worm_hand", "thread_hand", "Enter 1 for right hand or -1 for left hand.")
        ratio = v["worm_starts"] * m / v["worm_diameter"]
        if ratio >= math.sin(math.radians(35)):
            issue("worm_diameter", "worm_lead_limit", "Increase worm pitch diameter or reduce module/starts. The supported worm lead angle is below 35 degrees.")
        if v["worm_diameter"] - 2 * m * (ded - shift) <= max(0.4, m):
            issue("worm_diameter", "worm_root", "The worm root is too small. Increase its pitch diameter or reduce tooth size.")
    if any(i["severity"] == "error" for i in issues):
        return result
    try:
        metrics = dimensions(kind, v)
    except (ValueError, ZeroDivisionError, OverflowError):
        issue("", "geometry_domain", "These inputs do not define a supported finite gear geometry.")
        return result
    if not all(math.isfinite(value) for value in metrics.values()):
        issue("", "geometry_nonfinite", "The resulting dimensions are not finite. Reduce the input range.")
        return result
    result["metrics"] = metrics
    min_ligament = max(0.25, 0.4 * m)
    if metrics.get("tip_diameter", 1) > MAX_DIAMETER or metrics.get("outside_diameter", 1) > MAX_DIAMETER:
        issue("module", "diameter_budget", "The generated diameter exceeds the 500 mm modeling envelope. Reduce module or teeth.")
    if metrics.get("root_diameter", 1) <= max(0.2, 0.2 * m):
        issue("teeth", "root_radius", "The tooth roots reach the gear centre. Increase tooth count or reduce dedendum/negative shift.")
    if "bore" in fields and kind != "crown":
        if 0 < v["bore"] < 0.2:
            issue("bore", "tiny_bore", "Use a bore of at least 0.2 mm, or zero for no bore.")
        if metrics.get("bore_ligament", (metrics.get("root_diameter", 0) - v["bore"]) / 2) < min_ligament:
            issue("bore", "bore_clearance", "The bore leaves less than %.3g mm below the tooth roots. Reduce the bore or increase the gear size." % min_ligament)
    if metrics.get("normal_tooth_thickness", m) < 0.15 * m:
        issue("backlash", "tooth_thickness", "Tooth thinning and profile shift leave too little tooth thickness at the reference section.")
    if metrics.get("tip_tooth_thickness", m) < max(0.02, 0.04 * m):
        issue("addendum", "pointed_teeth", "These teeth become pointed or cross at their tips. Reduce addendum or thinning, or increase tooth count.")
    if kind in CYLINDRICAL:
        if kind.startswith("internal_"):
            if metrics["tip_diameter"] <= metrics["base_diameter"] + 0.02:
                issue("teeth", "internal_base_circle", "The internal tooth tips reach the base circle. Increase teeth or pressure angle, or reduce addendum.")
            if metrics["ring_rim"] < max(0.5, m):
                issue("outside_diameter", "ring_rim", "Increase the ring outside diameter to leave at least %.3g mm beyond its tooth roots." % max(0.5, m))
            issue("teeth", "pair_interference", "This validates the ring itself. Check involute, trochoidal and assembly interference with the actual mating pinion.", "warning")
        elif v["teeth"] < metrics["min_teeth_without_undercut"]:
            issue("teeth", "undercut", "Rack generation is expected to undercut these teeth. The root is generated, but tooth strength and pair contact require review.", "warning")
        if abs(metrics.get("twist_angle", 0)) > 90:
            issue("width", "twist_budget", "The tooth trace twists more than 90 degrees across a helical section. Reduce width or helix angle, or increase diameter.")
        if "herringbone" in kind:
            issue("width", "herringbone_assembly", "Opposed halves meet without a relief groove. Check machining and mating-gear assembly access.", "warning")
    if kind in RACKS:
        if metrics["rack_length"] > 500:
            issue("teeth", "rack_length_budget", "The rack exceeds the 500 mm supported length. Reduce tooth count or module.")
        if v["rack_height"] - metrics["root_depth"] < min_ligament:
            issue("rack_height", "rack_back", "Increase rack height to leave at least %.3g mm of backing below the tooth roots." % min_ligament)
        if metrics["rack_skew"] >= metrics["rack_length"] * 0.5:
            issue("helix_angle", "rack_skew", "The tooth trace shifts over half the rack length across its width. Reduce width/helix angle or increase rack length.")
    if kind == "worm":
        if v["width"] < 1.5 * metrics["axial_pitch"]:
            issue("width", "worm_length", "Use a worm length of at least 1.5 axial tooth pitches for this generator.")
        turns = v["width"] / metrics["lead"]
        if turns > 20:
            issue("width", "worm_turns", "This worm requires more than 20 turns. Shorten it or increase module/starts.")
    if kind == "worm_wheel":
        if v["width"] > v["worm_diameter"] * 0.6:
            issue("width", "wheel_face_width", "Wheel face width must be at most 60% of the generating worm pitch diameter in the supported envelope.")
        issue("worm_diameter", "generated_pair", "Use a mating worm with exactly these module, pressure angle, diameter and start values.", "warning")
    if kind in BEVELS:
        if not (5 <= metrics["pitch_cone_angle"] <= 85 and 5 <= metrics["mate_pitch_cone_angle"] <= 85):
            issue("shaft_angle", "pitch_cone", "Both external pitch-cone angles must be between 5 and 85 degrees. Adjust tooth ratio or shaft angle.")
        if v["width"] > metrics["cone_distance"] / 3:
            issue("width", "bevel_face_width", "Reduce face width to at most one third of the outer cone distance (%.3g mm)." % (metrics["cone_distance"] / 3))
        if metrics["root_cone_angle"] <= 1:
            issue("teeth", "bevel_root_cone", "The root cone collapses toward the shaft. Increase tooth count or reduce dedendum.")
        issue("mate_teeth", "bevel_pair", "Match the mating definition and align both pitch-cone apexes. The individual solid is not a complete interference check.", "warning")
    if kind == "crown":
        if metrics["inner_face_diameter"] / 2 <= metrics["generating_pinion_tip_radius"] + m * 0.25:
            issue("mate_teeth", "crown_pinion_clearance", "The generating pinion is too large for the inner face radius. Increase crown teeth, reduce radial width or reduce pinion teeth.")
        if v["width"] > min(8 * m, metrics["pitch_diameter"] * 0.2):
            issue("width", "crown_radial_width", "Reduce radial face width to at most 8 modules and 20% of pitch diameter.")
        if v["bore"] >= metrics["inner_face_diameter"] - 2 * min_ligament:
            issue("bore", "crown_bore", "The bore reaches the face-gear teeth. Reduce its diameter.")
        if 0 < v["bore"] < 0.2:
            issue("bore", "tiny_bore", "Use a bore of at least 0.2 mm, or zero for no bore.")
        issue("mate_teeth", "crown_pair", "Face teeth are generated by the specified pinion. Inspect the complete pair for contact across the radial face.", "warning")
    # These are relative work units, deliberately not promised seconds. Native
    # kernel calls have their own guards and cannot be interrupted arbitrarily.
    sections = 1
    if kind in CYLINDRICAL and "helix_angle" in fields:
        sections = 9 if "herringbone" not in kind else 18
    if kind in BEVELS:
        sections = 9 if kind == "spiral_bevel" else 2
    if kind == "worm":
        sections = max(9, math.ceil(v["width"] / metrics["lead"] * 12))
    if kind == "worm_wheel":
        sections = 15
    if kind == "crown":
        sections = 21
    work = int(v.get("teeth", v.get("worm_starts", 1)) * sections)
    if kind in ("worm_wheel", "crown"):
        work *= 3
    result["cost"] = {"units": work, "limit": MAX_COST, "sections": sections,
                      "level": "high" if work > 2000 else "medium" if work > 400 else "low",
                      "label": "Relative geometry workload", "bounded": True}
    if work > MAX_COST:
        issue("teeth", "complexity_budget", "This definition exceeds the bounded build budget. Reduce teeth, face width or geometric complexity.")
    elif work > 2000:
        issue("", "complexity_warning", "This is an expensive geometry build. Use the explicit Build button when ready; the preview remains lightweight.", "warning")
    result["valid"] = not any(i["severity"] == "error" for i in issues)
    return result
