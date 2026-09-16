"""Detach a reusable gear template from its source-owned parameter aliases.

Owned aliases are replaced by parenthesized source expressions, recursively.
External Fusion parameter names remain live expressions, never numeric snapshots.
This transformation has no Fusion imports and does not modify its input objects.
"""

from __future__ import annotations

from copy import deepcopy
import re


MAX_EXPRESSION_LENGTH = 256
MAX_PARAMETERS = 64
MAX_EXPANSION_WORK = 4096
MAX_DEPENDENCY_DEPTH = 32
_TOKEN = re.compile(r"\w+", re.UNICODE)
_IDENTIFIER = re.compile(r"[^\W\d]\w*\Z", re.UNICODE)


class TemplateError(ValueError):
    """The expressions cannot safely become a reusable independent template."""


def template_spec(spec, parameter_names=None):
    """Return an independent definition without ``id`` or ``placement``.

    ``parameter_names`` maps source field keys to their managed Fusion aliases.
    If omitted, the Gear Studio UUID-derived naming convention is used when the
    definition has an ID. Only exact Unicode identifier tokens are replaced;
    underscores, Unicode names and larger identifiers retain their boundaries.
    Each resulting expression is limited to 256 characters. Cycles, excessive
    dependency depth, or expansion work fail with an actionable TemplateError.
    """
    if not isinstance(spec, dict):
        raise TemplateError("A reusable gear template needs a gear definition.")
    parameters = spec.get("parameters")
    if not isinstance(parameters, dict) or not parameters or len(parameters) > MAX_PARAMETERS:
        raise TemplateError("A reusable gear template needs between 1 and 64 parameter expressions.")
    for key, expression in parameters.items():
        if not isinstance(key, str) or not _IDENTIFIER.fullmatch(key):
            raise TemplateError("The gear contains an invalid parameter name.")
        if not isinstance(expression, str) or not expression.strip():
            raise TemplateError("Every gear parameter must contain an expression.")
        if len(expression) > MAX_EXPRESSION_LENGTH:
            raise TemplateError("Simplify '%s' to no more than 256 characters before reusing this gear." % key)
    if parameter_names is None:
        identity = spec.get("id")
        if identity:
            prefix = re.sub(r"[^A-Za-z0-9]", "", str(identity))[:12]
            if not prefix:
                raise TemplateError("The gear has an invalid identity. Reload its original definition.")
            parameter_names = {key: "GS_%s_%s" % (prefix, key) for key in parameters}
        else:
            parameter_names = {}
    if not isinstance(parameter_names, dict) or len(parameter_names) > MAX_PARAMETERS:
        raise TemplateError("The gear's managed parameter map is invalid.")
    aliases = {}
    for key, name in parameter_names.items():
        if key not in parameters or not isinstance(name, str) or len(name) > 128 or not _IDENTIFIER.fullmatch(name):
            raise TemplateError("The gear's managed parameter names do not match its definition.")
        if name in aliases:
            raise TemplateError("Two gear fields share a managed parameter name. Restore their original names before reusing this gear.")
        aliases[name] = key

    memo = {}
    active = []
    work = 0

    def spend():
        nonlocal work
        work += 1
        if work > MAX_EXPANSION_WORK:
            raise TemplateError("The gear's expression dependencies are too complex. Simplify them before saving or duplicating this gear.")

    def expand(field):
        spend()
        if field in memo:
            return memo[field]
        if field in active:
            raise TemplateError("Circular gear parameter dependency: %s. Remove this reference loop before reusing the gear." % " -> ".join(active + [field]))
        if len(active) >= MAX_DEPENDENCY_DEPTH:
            raise TemplateError("The gear's parameter dependencies are too deeply nested. Simplify the chain before reusing the gear.")
        active.append(field)
        try:
            expression = parameters[field]
            parts = []
            cursor = 0
            length = 0
            for match in _TOKEN.finditer(expression):
                spend()
                name = match.group(0)
                if name not in aliases:
                    continue
                before = expression[cursor:match.start()]
                replacement = "(" + expand(aliases[name]) + ")"
                length += len(before) + len(replacement)
                if length > MAX_EXPRESSION_LENGTH:
                    raise TemplateError("Expanding '%s' exceeds 256 characters. Simplify the source expressions or use an external named parameter." % field)
                parts.extend((before, replacement))
                cursor = match.end()
            tail = expression[cursor:]
            if length + len(tail) > MAX_EXPRESSION_LENGTH:
                raise TemplateError("Expanding '%s' exceeds 256 characters. Simplify the source expressions or use an external named parameter." % field)
            parts.append(tail)
            memo[field] = "".join(parts)
            return memo[field]
        finally:
            active.pop()

    expanded = {field: expand(field) for field in parameters}
    result = deepcopy(spec)
    result.pop("id", None)
    result.pop("placement", None)
    result["parameters"] = expanded
    return result
