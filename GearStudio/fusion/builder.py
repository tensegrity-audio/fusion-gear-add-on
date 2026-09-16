"""Native B-rep candidates, isolated from the user's document.

Lengths enter as millimetres and are converted to Fusion centimetres once.
All rotary families use the Z shaft axis. Spur/helical/ring/wheel/herringbone
bodies are centred on XY. Worms run from Z=0 to face width. Bevels retain the
common pitch-cone apex at the origin. Racks run in +X, teeth in +Y, width in Z,
with the reference line at Y=0. Crown reference tooth plane is Z=0.

This module does not create target parameters, attributes, components or features.
Call from the palette bridge before starting the hidden target commit command:
Fusion cannot close documents while a command transaction is active.
"""
from dataclasses import dataclass
from math import asin, atan2, cos, isfinite, pi, radians

from ..core.validation import validate
from ..vendor.study_gears.guard import (
    GeometryBudgetExceeded, GeometryCancelled, bounded, checkpoint,
)

SUPPORTED_KINDS = frozenset({
    "spur", "helical", "herringbone", "internal_spur", "internal_helical",
    "internal_herringbone", "rack", "helical_rack", "worm", "worm_wheel",
    "bevel", "spiral_bevel", "crown",
})


class BuildError(RuntimeError):
    """A recoverable modeling error with the target document unchanged."""


@dataclass
class Candidate:
    """Own a detached temporary body. No scratch document survives success."""
    body: object

    def cleanup(self):
        self.body = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.cleanup()


def _host():
    import adsk.core
    import adsk.fusion
    return adsk, adsk.core.Application.get()


def _check_document(app, scratch):
    if not scratch.isValid:
        raise BuildError("The temporary build document was closed. Build cancelled.")
    if app.activeDocument != scratch:
        raise BuildError(
            "The active document changed during preparation. "
            "Your existing gear was preserved. Return to its document and try again."
        )


def _restore_documents(source, scratch):
    """Attempt both cleanup actions even if closing the scratch fails."""
    errors = []
    if scratch is not None and scratch.isValid:
        try:
            if scratch.close(False) is False:
                errors.append("Fusion did not close the temporary document.")
        except Exception as exc:
            errors.append("Could not close temporary document: " + str(exc))
    if source is not None and source.isValid:
        try:
            if source.activate() is False:
                errors.append("Fusion did not reactivate your original document.")
        except Exception as exc:
            errors.append("Could not reactivate original document: " + str(exc))
    return errors


def build_candidate(spec, values, progress=None, cancelled=None):
    """Build one validated detached temporary B-rep without touching the target.

    Progress is ``progress(message: str, percent: float)``. Cancellation is
    cooperative: vendor loops and feature boundaries yield, but an individual
    Autodesk modeling-kernel operation cannot be interrupted by Python.
    """
    kind = spec.get("kind")
    if kind not in SUPPORTED_KINDS:
        raise BuildError("This gear family is not implemented by the native builder.")
    result = validate(spec, values)
    if not result["valid"]:
        messages = [i["message"] for i in result["issues"] if i["severity"] == "error"]
        raise BuildError(" ".join(messages))
    if cancelled and cancelled():
        raise GeometryCancelled("Build cancelled before preparation.")

    adsk, app = _host()
    ui = getattr(app, "userInterface", None)
    active_command = getattr(ui, "activeCommand", "") if ui else ""
    if active_command not in ("", "SelectCommand"):
        raise BuildError(
            "Finish or cancel the active Fusion command before generating a gear. "
            "The temporary build requires Fusion to be idle."
        )
    source = app.activeDocument
    if source is None or not source.isValid:
        raise BuildError("Open a Fusion design before generating a gear.")
    scratch = None
    candidate = None
    problem = None
    cleanup_errors = []
    try:
        scratch = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        if scratch is None:
            raise BuildError("Fusion could not create the temporary build document.")
        scratch.name = "Gear Studio temporary build"
        design = adsk.fusion.Design.cast(app.activeProduct)
        if design is None:
            raise BuildError("The temporary document did not contain a Fusion design.")
        # Fusion 2026 can create a Part-intent design by default. The private
        # upstream geometry uses nested calculation components, requiring Hybrid.
        # Older versions have no intent property and already allow components.
        if hasattr(design, "designIntent"):
            intent_types = getattr(adsk.fusion, "DesignIntentTypes", None)
            if intent_types is None:
                raise BuildError("This Fusion version cannot create a Hybrid calculation document.")
            design.designIntent = intent_types.HybridDesignIntentType
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType

        def pump():
            _check_document(app, scratch)
            adsk.doEvents()
            _check_document(app, scratch)

        def report(message, percent):
            _check_document(app, scratch)
            if progress:
                progress(message, percent)
            _check_document(app, scratch)
            checkpoint(force=True)

        iteration_limit = 80000000 if kind in ("crown", "worm_wheel") else 2000000
        with bounded(cancelled=cancelled, pump=pump, seconds=150, iterations=iteration_limit):
            report("Calculating the tooth profile", 12)
            body = _generate(design, kind, dict(values), adsk, report)
            report("Checking the solid", 90)
            _verify_solid(body)
            candidate = Candidate(body)
    except (GeometryCancelled, GeometryBudgetExceeded, BuildError) as exc:
        problem = exc
    except Exception as exc:
        problem = BuildError(
            "Fusion could not build this combination of inputs. "
            "Your existing gear was preserved. Reduce face width, helix angle or tooth count, "
            "or review the tooth and body dimensions. Details: " + str(exc)
        )
    finally:
        cleanup_errors = _restore_documents(source, scratch)

    if cleanup_errors:
        if candidate:
            candidate.cleanup()
        detail = " ".join(cleanup_errors)
        if problem:
            detail = str(problem) + " " + detail
        raise BuildError(detail)
    if problem:
        if candidate:
            candidate.cleanup()
        raise problem
    if candidate is None:
        raise BuildError("The build returned no solid.")
    return candidate


def _verify_solid(body):
    if body is None or not body.isValid or not body.isSolid:
        raise BuildError("The generated geometry is not a valid closed B-rep solid.")
    if body.lumps.count != 1:
        raise BuildError("This input combination produced disconnected pieces instead of one solid.")
    if not isfinite(body.volume) or body.volume <= 1e-10:
        raise BuildError("The generated solid has no usable volume.")
    if body.faces.count > 24000:
        raise BuildError("The generated solid exceeded the supported face-count budget.")


def _solid_in(component):
    solids = [body for body in component.bRepBodies if body.isSolid]
    if len(solids) != 1:
        raise BuildError("The tooth operation did not produce exactly one solid body.")
    return solids[0]


def _only_solid(design):
    solids = []
    for occurrence in design.rootComponent.allOccurrences:
        checkpoint()
        solids.extend(b for b in occurrence.component.bRepBodies if b.isSolid)
    if len(solids) != 1:
        raise BuildError("The temporary design contains an unexpected number of solids.")
    return solids[0]


def _temporary_copy(body, adsk):
    checkpoint(force=True)
    native = body.nativeObject or body
    copy = adsk.fusion.TemporaryBRepManager.get().copy(native)
    if copy is None:
        raise BuildError("Fusion could not detach the temporary solid.")
    return copy


def _cylinder(adsk, radius, low_z, high_z):
    checkpoint(force=True)
    result = adsk.fusion.TemporaryBRepManager.get().createCylinderOrCone(
        adsk.core.Point3D.create(0, 0, low_z), radius,
        adsk.core.Point3D.create(0, 0, high_z), radius,
    )
    if result is None:
        raise BuildError("Fusion could not create the cylindrical body feature.")
    return result


def _boolean(adsk, target, tool, operation):
    checkpoint(force=True)
    if not adsk.fusion.TemporaryBRepManager.get().booleanOperation(target, tool, operation):
        raise BuildError("Fusion could not combine the body features into a valid solid.")
    checkpoint(force=True)
    return target


def _transform(adsk, body, rotation_y=0, rotation_z=0, translation_z=0):
    checkpoint(force=True)
    matrix = adsk.core.Matrix3D.create()
    if rotation_y:
        matrix.setToRotation(rotation_y, adsk.core.Vector3D.create(0, 1, 0), adsk.core.Point3D.create())
    elif rotation_z:
        matrix.setToRotation(rotation_z, adsk.core.Vector3D.create(0, 0, 1), adsk.core.Point3D.create())
    matrix.translation = adsk.core.Vector3D.create(0, 0, translation_z)
    if not adsk.fusion.TemporaryBRepManager.get().transform(body, matrix):
        raise BuildError("Fusion could not align the generated solid.")
    return body


def _gear_params(v, inner=False):
    from ..vendor.study_gears.gear_curve import GearParams
    return GearParams(
        m=v["module"] / 10, z=int(v.get("teeth", 24)),
        alpha=radians(v["pressure_angle"]), shift=v.get("profile_shift", 0),
        fillet=v.get("root_fillet", 0.25), mf=v["dedendum"], mk=v["addendum"],
        rc=v["dedendum"] - v["addendum"], backlash=v["backlash"] / 10, inner=inner,
    )


def _generate(design, kind, v, adsk, report):
    from ..vendor.study_gears.lib import fusion_helper as fh
    from ..vendor.study_gears.gear_cylindrical import gear_cylindrical
    from ..vendor.study_gears.gear_rack import RackParams, gear_rack
    from ..vendor.study_gears.gear_worm import gear_worm
    from ..vendor.study_gears.gear_worm_wheel import gear_worm_wheel
    from ..vendor.study_gears import gear_bevel, gear_crown

    # Creation-time joints and camera movements in the original study script are
    # unnecessary in a disposable calculation document. No user settings change.
    # This is a private vendored namespace, not another installed add-in's module.
    no_op = lambda *args, **kwargs: None
    fh.comp_joint_revolute = no_op
    fh.comp_built_joint_revolute = no_op
    fh.comp_joint_slider = no_op
    fh.camera_setup = no_op

    m = v["module"] / 10
    width = v["width"] / 10
    inner = kind.startswith("internal_")
    herringbone = kind in ("herringbone", "internal_herringbone")
    beta = radians(v.get("helix_angle", 0)) if "helical" in kind or herringbone else 0
    p = _gear_params(v, inner)
    manager = adsk.fusion.TemporaryBRepManager.get()
    boolean = adsk.fusion.BooleanTypes

    if kind in ("rack", "helical_rack", "worm"):
        rp = RackParams(
            m=m, height=(v.get("rack_height", 6) + m * 10 * v["addendum"]) / 10,
            thickness=v["worm_diameter"] / 10 if kind == "worm" else width,
            length=width if kind == "worm" else int(v["teeth"]) * pi * m / cos(beta),
            angle=beta, worm=int(v.get("worm_starts", 0)) if kind == "worm" else 0,
            mk=p.mk, mf=p.mf, rc=p.rc, alpha=p.alpha, backlash=p.backlash, fillet=p.fillet,
        )
        report("Building the rack profile" if kind != "worm" else "Building the worm thread", 28)
        if kind == "worm":
            gear_worm(rp, 0, int(v.get("worm_hand", 1)))
        else:
            gear_rack(rp, 0)
        body = _temporary_copy(_only_solid(design), adsk)
        if kind != "worm":
            # Upstream rack length runs -Y, teeth +X. Reorient to +X / +Y.
            body = _transform(adsk, body, rotation_z=pi / 2)
    else:
        wrapper = design.rootComponent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        wrapper.isGroundToParent = False
        if kind in ("bevel", "spiral_bevel"):
            first = int(v["teeth"]) >= int(v["mate_teeth"])
            beta_b = radians(v["spiral_angle"]) if kind == "spiral_bevel" else 0
            # The source pair generator reverses the smaller member's twist.
            # Compensate so the signed input consistently controls this member.
            beta_b *= 1 if first else -1
            bp = gear_bevel.Params(
                radians(v["shaft_angle"]), m, int(v["teeth"]), int(v["mate_teeth"]),
                beta_b, p.mk, p.mf, p.alpha, width,
                # Upstream offsets each flank by this amount in the transverse
                # outer section; half the requested full normal tooth thinning.
                p.backlash / (2 * cos(beta_b)),
            )
            if bp.internal:
                raise BuildError("Internal bevel geometry is outside this release's supported range.")
            report("Calculating spherical involute and root curves", 24)
            t1, i1, t2, i2 = gear_bevel.gear_curves(bp)
            axis = bp.axis1 if first else bp.axis2
            n = bp.z1 if first else bp.z2
            grooves = gear_bevel.tooth_groove(bp, t1 if first else t2, i1 if first else i2, axis, n)
            report("Building the bevel tooth surfaces", 40)
            occurrence = gear_bevel.generate_gear(
                wrapper, bp, axis, n, grooves, 1 if first else -1, 0, False, printable=False,
            )
            body = _temporary_copy(_solid_in(occurrence.component), adsk)
            body = _transform(adsk, body, rotation_y=atan2(axis.z, axis.x) - pi / 2)
        elif kind == "crown":
            p.z = int(v["mate_teeth"])
            p.shift = 0
            p.fillet = 0.4
            p.backlash = -p.backlash
            report("Calculating generating-pinion envelopes", 24)
            gear = gear_crown.gear_crown(
                wrapper, p, int(v["teeth"]), width / (2 * m), width / (2 * m), 0,
                base_thickness=v["crown_base"] / 10,
            )
            body = _temporary_copy(_solid_in(gear), adsk)
            body = _transform(adsk, body, translation_z=m * p.z / 2)
            # Add a full backing web below the tooth roots, retaining the annular
            # generating region above it. The requested bore is cut afterwards.
            base = v["crown_base"] / 10
            outer_radius = m * int(v["teeth"]) / 2 + width / 2
            web = _cylinder(adsk, outer_radius, -p.mf * m - base, -p.mf * m)
            body = _boolean(adsk, body, web, boolean.UnionBooleanType)
        else:
            if kind == "worm_wheel":
                beta = int(v.get("worm_hand", 1)) * asin(v["worm_starts"] * v["module"] / v["worm_diameter"])
                report("Building enveloped wheel sections", 28)
                gear_worm_wheel(wrapper, p, v["worm_diameter"] / 10,
                                int(v["worm_starts"]), width, beta)
            else:
                report("Building native tooth surfaces", 28)
                gear_cylindrical(wrapper, p, width / 2 if herringbone else width, beta, 0)
            component = wrapper.component.occurrences.item(0).component
            native = _solid_in(component)
            if herringbone:
                report("Joining the two helical halves", 72)
                fh.comp_move_free(component, native, fh.matrix_translate(z=width / 4))
                reflected = fh.comp_mirror(component, native, component.xYConstructionPlane).bodies.item(0)
                body = _temporary_copy(native, adsk)
                other_half = _temporary_copy(reflected, adsk)
                body = _boolean(adsk, body, other_half, boolean.UnionBooleanType)
            else:
                body = _temporary_copy(native, adsk)
            if inner:
                report("Building the surrounding ring", 79)
                ring = _cylinder(adsk, v["outside_diameter"] / 20, -width / 2, width / 2)
                body = _boolean(adsk, ring, body, boolean.DifferenceBooleanType)

    if not inner and kind not in ("rack", "helical_rack") and v.get("bore", 0) > 0:
        report("Cutting the shaft bore", 85)
        bounds = body.boundingBox
        margin = max(0.1, width / 10)
        bore = _cylinder(adsk, v["bore"] / 20,
                         bounds.minPoint.z - margin, bounds.maxPoint.z + margin)
        body = _boolean(adsk, body, bore, boolean.DifferenceBooleanType)
    return body
