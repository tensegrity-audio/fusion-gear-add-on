# Vendored from Osamu Takeuchi, MIT. See LICENSE.txt and UPSTREAM.md.
from __future__ import annotations
from ...guard import checkpoint
import adsk.core, adsk.fusion


def curve3d_point(curve: adsk.core.Curve3D, t: float):
    """
    Get the point on the curve at the specified parameter (0 <= t <= 1).
    """
    extents = curve.evaluator.getParameterExtents()
    p = extents[1] + (extents[2] - extents[1]) * t
    return curve.evaluator.getPointAtParameter(p)[1]
