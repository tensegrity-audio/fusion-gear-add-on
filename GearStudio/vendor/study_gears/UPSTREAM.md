# Geometry engine provenance

This directory contains a selected, privately namespaced derivative of:

- [fusion360-study-gears](https://github.com/osamutake/fusion360-study-gears), Osamu Takeuchi, MIT, pinned to `e8d0efcb3ad40e52c1e07b2f82ef4a24112c5094`.
- [fusion360-helper](https://github.com/osamutake/fusion360-helper), Osamu Takeuchi, MIT, pinned submodule `d313728f8d50e2b792385ff7fb6b735037c6aa36`.

The complete original MIT permission notices, including copyright and warranty
terms, are retained in `LICENSE.txt` and `lib/fusion_helper/LICENSE.txt`.

Only geometry and necessary local helpers are included. Original command UI,
preference persistence, translations, pip installer, and unrelated spiral/cam
generators are excluded. There is no third-party package installation or network
requirement at runtime.

## Local changes

- 0.3.3 separates the shaft reference into an XZ sketch and keeps the pitch circle in XY. Wrapper and pitch circles fix only their centers, retain driving diameters, and verify evaluated radius/diameter instead of gating on the aggregate circle constraint flag. Other sketch points/curves remain constrained. This follows a reported 0.3.2 native build failure; native confirmation of the correction is pending.

- Every explicit numerical loop has a cooperative `checkpoint()`. Feature helpers
  also check before entering native operations. The caller applies a wall-clock
  budget and an iteration budget, and pumps cancellation between operations.
- Pure vector routines, cylindrical tooth curves, spherical bevel curves,
  worm-wheel envelopes and crown envelopes can be imported and tested without
  Autodesk libraries. These are the `vector`, `gear_curve`, `math_bevel`,
  `math_worm_wheel`, and `math_crown` modules.
- Deferred cylindrical sketch computation ends before requesting profiles.
- Cylindrical calculated profiles lock remaining curve/point freedom after solving. Shaft reference lines have fixed endpoints and are construction geometry. Pitch circles and wrapper cylinder profiles use origin coincidence plus a driving diameter instead of an unconstrained center or a redundant fixed circle. Shaft bore diameters can bind to the owning gear's named parameter; calculated tooth/pitch geometry still regenerates explicitly. These constraint checks require native Fusion acceptance.
- Rack and worm flank endpoints use the true circular-fillet tangent, avoiding
  inconsistent arc endpoints when the requested tool radius is below its limit.
- Helical section-count estimation handles both signs of helix angle.
- Normal module, normal pressure angle, normal tooth thinning and normal profile
  shift are explicitly converted to the transverse system. Root-tool radius and
  radial-clearance coefficients are also scaled to keep their stated size.
- Wheel outer diameter includes normal profile shift.
- Crown generation accepts an explicit backing thickness. The wrapper adds a
  solid supporting web and an optional shaft bore.
- The wrapper adds cylindrical bores and internal-gear rings using native
  sketch, Extrude and Combine operations. Herringbone solids join a helical half to its mirror.
- Bevel tooth thinning is divided by two when calling the upstream per-flank
  offset, and signed spiral inputs are normalized to the requested member.
- Cylindrical cutters are patterned as B-rep bodies, then subtracted in one Combine feature. Repeating the dependent helical loft-cut feature produced a mostly cylindrical result in a user report. Cutter count and post-build tooth-space checks now guard this path.
- Rack and worm constructors accept an explicit parent component for retained construction history.
- Other feature copies retain the Identical pattern compute option.
- Unneeded creation-time joints and camera motion are disabled only within this
  privately vendored namespace.
- Python 3.12-only `typing.override` decorators are removed from segment helpers;
  these static markers do not affect geometry or runtime behavior.
- Future annotations are used so geometry modules parse in Python 3.10+; the
  original Python 3.12 command framework is not included.

## Accuracy and verification boundary

Outputs are Fusion B-rep solids with curves and surfaces. They are not triangle
meshes. Nonetheless, B-rep does not mean mathematically exact tooth geometry:
the underlying mathematical curves are sampled into fitted splines, helical
sections are lofted, and worm-wheel/crown envelopes use finite sampling. The
transverse root fillet uses a circular tool-radius approximation. No ISO/AGMA
gear quality grade or maximum profile-deviation certification is claimed.

The cylinder engine calculates involute flanks and generated trochoidal roots.
Bevel profiles use spherical involute and spherical trochoid calculations.
Worm wheels and crown gears use generating-tool envelopes. These are individual
solid constructors, not a complete meshing, strength, contact or manufacturing
qualification system. Internal bevel, hypoid, cycloidal, planetary-assembly and
non-circular gear constructors are not included in this release.

Autodesk Fusion is not installed in the build environment. Pure mathematical
tests and lifecycle tests run here; acceptance tests for native kernel geometry,
feature references and installation must run in desktop Fusion. Cooperative
cancellation cannot interrupt one native modeling-kernel call already running.

## Autodesk API references checked

- [Temporary B-rep manager](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_TemporaryBRepManager.htm)
- [Temporary body copy](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_TemporaryBRepManager_copy.htm)
- [Temporary Boolean operation](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_TemporaryBRepManager_booleanOperation.htm)
- [Cylinder creation and centimetre units](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_TemporaryBRepManager_createCylinderOrCone.htm)
- [Temporary body transform](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_TemporaryBRepManager_transform.htm)
- [Document close and command-transaction restriction](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/core_Document_close.htm)
- [Design intent, including Part to Hybrid conversion](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_Design_designIntent.htm)
- [Sketch origin](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_Sketch_originPoint.htm), [coincident constraints](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_GeometricConstraints_addCoincident.htm) and [driving diameter dimensions](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_SketchDimensions_addDiameterDimension.htm)
- [Sketch dimension parameter](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_SketchDimension_parameter.htm), [model parameter expressions](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_ModelParameter_expression.htm) and [dimension attributes](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_SketchDimension_attributes.htm)
- [Fixed sketch points](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_SketchPoint_isFixed.htm) and [fully constrained sketch status](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_Sketch_isFullyConstrained.htm)
