"""Public gear families and unit-aware expression inputs.

All dimensional calculations use millimetres and degrees. Cylindrical gears and
racks use the normal module/pressure-angle convention, including normal backlash.
A family's presence describes a definition; the Fusion bridge additionally filters
families against the native builder's SUPPORTED_KINDS.
"""
from copy import deepcopy

FIELDS = {
    "module": {"label": "Normal module", "unit": "mm", "default": "1 mm", "description": "Tooth size in the normal plane. For spur gears this is also the transverse module.", "group": "Tooth system"},
    "teeth": {"label": "Teeth", "unit": "", "default": "24", "description": "A whole number of teeth. On a rack, the number of full tooth pitches.", "group": "Tooth system", "integer": True},
    "pressure_angle": {"label": "Normal pressure angle", "unit": "deg", "default": "20 deg", "description": "Pressure angle in the normal plane. Use the same value on mating gears.", "group": "Tooth system"},
    "width": {"label": "Face width", "unit": "mm", "default": "8 mm", "description": "Axial gear width. For bevel gears, width along the pitch cone.", "group": "Body"},
    "bore": {"label": "Bore diameter", "unit": "mm", "default": "5 mm", "description": "Straight circular shaft opening. Enter zero for a solid centre.", "group": "Body"},
    "backlash": {"label": "Tooth thinning", "unit": "mm", "default": "0.05 mm", "description": "This gear's tooth-thickness reduction at the normal reference section. Pair clearance includes both gears' reductions; it is not applied twice automatically.", "group": "Tooth system"},
    "profile_shift": {"label": "Profile shift", "unit": "", "default": "0", "description": "Normal profile shift coefficient. Shifted mating gears require a compatible centre distance.", "group": "Advanced"},
    "addendum": {"label": "Addendum coefficient", "unit": "", "default": "1", "description": "Tooth height above the reference surface, expressed in modules.", "group": "Advanced"},
    "dedendum": {"label": "Dedendum coefficient", "unit": "", "default": "1.25", "description": "Tooth depth below the reference surface, expressed in modules.", "group": "Advanced"},
    "root_fillet": {"label": "Root fillet coefficient", "unit": "", "default": "0.25", "description": "Generating tool tip radius divided by normal module. The generated tooth root is a trochoidal profile, not an applied edge fillet.", "group": "Advanced"},
    "helix_angle": {"label": "Helix angle", "unit": "deg", "default": "20 deg", "description": "Signed pitch helix angle. Reverse the sign for the opposite hand. External gears on parallel shafts use opposite hands; internal pairs use the same hand.", "group": "Tooth system"},
    "outside_diameter": {"label": "Ring outside diameter", "unit": "mm", "default": "60 mm", "description": "Outside diameter of the surrounding ring. Must leave material beyond the tooth roots.", "group": "Body"},
    "crown_base": {"label": "Base thickness", "unit": "mm", "default": "2 mm", "description": "Solid face-gear backing below the tooth roots.", "group": "Body"},
    "rack_height": {"label": "Rack height", "unit": "mm", "default": "6 mm", "description": "Distance from the rack reference line to its flat back, including the dedendum.", "group": "Body"},
    "worm_diameter": {"label": "Worm pitch diameter", "unit": "mm", "default": "12 mm", "description": "Reference diameter of this worm or the worm that generates a wheel.", "group": "Tooth system"},
    "worm_hand": {"label": "Thread hand", "unit": "", "default": "1", "description": "Enter 1 for right hand or -1 for left hand. A worm and its wheel must use the same hand setting.", "group": "Tooth system", "integer": True},
    "worm_starts": {"label": "Worm starts", "unit": "", "default": "1", "description": "Number of intertwined worm threads. Must match the mating worm or wheel.", "group": "Tooth system", "integer": True},
    "mate_teeth": {"label": "Mating gear teeth", "unit": "", "default": "24", "description": "Whole tooth count of the mating gear; required to establish the pitch cone or generating pinion.", "group": "Pair geometry", "integer": True},
    "shaft_angle": {"label": "Shaft angle", "unit": "deg", "default": "90 deg", "description": "Angle between intersecting gear axes.", "group": "Pair geometry"},
    "spiral_angle": {"label": "Spiral angle", "unit": "deg", "default": "20 deg", "description": "Signed bevel tooth spiral angle at the reference cone.", "group": "Tooth system"},
}
_COMMON = ["module", "teeth", "pressure_angle", "width", "backlash"]
_ADVANCED = ["profile_shift", "addendum", "dedendum", "root_fillet"]

def _family(key, label, description, extras=(), defaults=None, pairing="", common=None):
    return {"id": key, "label": label, "description": description,
            "fields": list(_COMMON if common is None else common) + list(extras) + list(_ADVANCED),
            "defaults": dict(defaults or {}), "pairing": pairing,
            "moduleConvention": "normal", "output": "B-rep solid"}

FAMILIES = [
    _family("spur", "Spur", "Straight external involute teeth for parallel shafts.", ["bore"], pairing="Match normal module and pressure angle. Check centre distance and total pair tooth thinning."),
    _family("helical", "Helical", "External teeth with a continuous helical twist.", ["helix_angle", "bore"], pairing="Match normal module, normal pressure angle and helix magnitude. Parallel external shafts require opposite helix hands."),
    _family("herringbone", "Herringbone", "Two opposed helical halves meeting at the centre plane.", ["helix_angle", "bore"], pairing="Match both helix halves, normal module and pressure angle. This design has no centre relief groove."),
    _family("internal_spur", "Internal spur", "Involute teeth on the inside of a ring.", ["outside_diameter"], {"teeth": "48"}, "A mating external pinion requires a separate interference and assembly check. Tooth-count difference alone is insufficient."),
    _family("internal_helical", "Internal helical", "Helical internal teeth with a surrounding ring.", ["helix_angle", "outside_diameter"], {"teeth": "48"}, "Match normal module, pressure angle and the same helix hand for parallel shafts. Check internal-gear interference."),
    _family("internal_herringbone", "Internal herringbone", "Opposed helical tooth traces inside a ring.", ["helix_angle", "outside_diameter"], {"teeth": "48"}, "Check tooth compatibility and assembly access: a closed herringbone ring may prevent insertion of the mating pinion."),
    _family("rack", "Straight rack", "Linear involute-system rack with straight tooth traces.", ["rack_height"], {"teeth": "12"}, "Match the pinion's normal module and pressure angle. Set the pinion axis at the required reference height."),
    _family("helical_rack", "Helical rack", "Linear rack with angled tooth traces.", ["helix_angle", "rack_height"], {"teeth": "12"}, "Match the pinion's normal module, pressure angle and compatible tooth-trace direction."),
    _family("worm", "Worm", "Screw gear generated from the normal rack profile.", ["worm_diameter", "worm_starts", "worm_hand", "bore"], {"width": "16 mm", "bore": "4 mm"}, "Use an enveloped wheel generated for this exact module, pressure angle, pitch diameter and start count.", common=["module", "pressure_angle", "width", "backlash"]),
    _family("worm_wheel", "Worm wheel", "Enveloped wheel generated by a matching worm.", ["worm_diameter", "worm_starts", "worm_hand", "bore"], {"teeth": "36", "width": "5 mm"}, "The generating worm diameter and starts are part of this wheel's definition. Use a matching worm at the documented centre distance."),
    _family("bevel", "Straight bevel", "Spherical-involute teeth for intersecting shafts.", ["mate_teeth", "shaft_angle", "bore"], {"width": "4 mm", "bore": "4 mm"}, "Generate the mate with exchanged tooth counts and the same shaft angle, module and pressure angle. Align their cone apexes."),
    _family("spiral_bevel", "Spiral bevel", "Spherical-involute bevel teeth with a spiral trace.", ["mate_teeth", "shaft_angle", "spiral_angle", "bore"], {"width": "4 mm", "bore": "4 mm"}, "Generate both gears as a compatible pair with exchanged tooth counts and appropriate opposite spiral hands. Not a hypoid generator."),
    _family("crown", "Crown / face", "Face gear generated by a matching cylindrical pinion.", ["mate_teeth", "bore", "crown_base"], {"teeth": "48", "width": "5 mm", "bore": "8 mm"}, "Use the specified generating pinion. Verify face-gear radial limits and shaft placement for the complete pair."),
]
# Do not expose inputs that the selected native algorithm does not consume.
for _item in FAMILIES:
    if _item["id"] in ("rack", "helical_rack", "worm"):
        _item["fields"].remove("profile_shift")
    if _item["id"].startswith("internal_"):
        _item["fields"].remove("root_fillet")
    if _item["id"] in ("bevel", "spiral_bevel", "crown"):
        for _key in ("profile_shift", "root_fillet"):
            _item["fields"].remove(_key)
    if _item["id"] in ("bevel", "spiral_bevel"):
        _item["moduleConvention"] = "outer normal"
    if _item["id"] == "crown":
        _item["fieldOverrides"] = {"width": {"label": "Radial face width", "description": "Radial tooth-face width, centred on the crown's pitch radius."}}
FAMILY_BY_ID = {family["id"]: family for family in FAMILIES}


def catalog():
    """Return a detached, JSON-compatible catalogue."""
    return {"families": deepcopy(FAMILIES), "fields": deepcopy(FIELDS)}


def default_spec(kind="spur"):
    """Fresh successful-candidate defaults, with expression text retained."""
    if kind not in FAMILY_BY_ID:
        raise ValueError("Unknown gear family: %s" % kind)
    family = FAMILY_BY_ID[kind]
    return {"schema_version": 1, "name": family["label"] + " gear", "kind": kind,
            "parameters": {key: family["defaults"].get(key, FIELDS[key]["default"])
                           for key in family["fields"]}, "placement": {}}
