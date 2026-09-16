"""Small, bounded expression evaluator for previews and standalone checks.

``evaluate(text, unit, variables)`` returns mm, degrees, or a scalar according to
``unit`` (``mm``, ``deg``, or ``unitless``/````). Bare scalar results adopt the
requested output unit. Explicitly dimensioned results must match that unit.

Named variables are ``Quantity(value, dimension)`` in canonical millimetres and
radians. Dimension is ``scalar``, ``length`` or ``angle``; an internal tuple of
integer (length, angle) powers is also supported. No Python eval is used. This
deliberately supports a subset of Fusion syntax; unsupported syntax fails rather
than silently replacing an expression by a numerical snapshot.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
import io
import math
import re
import tokenize
from typing import Mapping


MAX_EXPRESSION_LENGTH = 512
MAX_AST_NODES = 160
MAX_AST_DEPTH = 24
MAX_ABSOLUTE_VALUE = 1e15
MAX_EXPONENT = 16
_DIMENSIONS = {"scalar": (0, 0), "unitless": (0, 0), "length": (1, 0), "angle": (0, 1)}
_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,79}\Z")


class ExpressionError(ValueError):
    """An expression is unsupported, incompatible, or outside safe bounds."""


@dataclass(frozen=True)
class Quantity:
    """A canonical value in mm/radians and its physical dimension."""

    value: float
    dimension: str | tuple[int, int] = "scalar"


_UNITS = {
    "mm": Quantity(1.0, "length"),
    "cm": Quantity(10.0, "length"),
    "m": Quantity(1000.0, "length"),
    "in": Quantity(25.4, "length"),
    "inch": Quantity(25.4, "length"),
    "inches": Quantity(25.4, "length"),
    "deg": Quantity(math.pi / 180.0, "angle"),
    "rad": Quantity(1.0, "angle"),
}
_FUNCTIONS = {"sin", "cos", "tan", "sqrt", "abs", "min", "max"}


def _dims(quantity: Quantity) -> tuple[int, int]:
    dimension = quantity.dimension
    if isinstance(dimension, str) and dimension in _DIMENSIONS:
        return _DIMENSIONS[dimension]
    if (isinstance(dimension, tuple) and len(dimension) == 2
            and all(type(power) is int and abs(power) <= MAX_EXPONENT for power in dimension)):
        return dimension
    raise ExpressionError("A named parameter has an unsupported physical dimension.")


def _quantity(value, dimension="scalar") -> Quantity:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExpressionError("Values must be real numbers.")
    try:
        value = float(value)
    except (OverflowError, ValueError):
        raise ExpressionError("The expression exceeds the supported numeric range.") from None
    if not math.isfinite(value) or abs(value) > MAX_ABSOLUTE_VALUE:
        raise ExpressionError("Use finite values with magnitude no greater than 10^15.")
    quantity = Quantity(value, dimension)
    _dims(quantity)
    return quantity


def _prepare(expression: str) -> str:
    if not isinstance(expression, str) or not expression.strip():
        raise ExpressionError("Enter a number or parameter expression.")
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise ExpressionError(f"Keep expressions within {MAX_EXPRESSION_LENGTH} characters.")
    if "\n" in expression.strip() or "\r" in expression.strip():
        raise ExpressionError("Use a single-line expression.")
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(expression.strip()).readline))
    except (tokenize.TokenError, IndentationError):
        raise ExpressionError("Check the expression's parentheses and operators.") from None
    output = []
    previous = None
    for token in tokens:
        if token.type in (tokenize.NEWLINE, tokenize.NL, tokenize.ENDMARKER):
            continue
        if token.type not in (tokenize.NUMBER, tokenize.NAME, tokenize.OP):
            raise ExpressionError("Only numbers, named parameters, units and arithmetic are supported.")
        text = token.string
        if token.type == tokenize.NAME:
            if not _NAME.fullmatch(text):
                raise ExpressionError("Parameter names must start with a letter and contain letters, digits or underscores.")
            if text in _UNITS:
                if previous is not None and (previous.type == tokenize.NUMBER or previous.string == ")"):
                    output.append("*")
                text = "__unit_" + text
        output.append(text)
        previous = token
    return " ".join(output)


class _Evaluator:
    def __init__(self, variables: Mapping[str, Quantity] | None):
        self.variables = variables or {}
        if not isinstance(self.variables, Mapping) or len(self.variables) > 1024:
            raise ExpressionError("The named-parameter table is invalid or too large.")

    def visit(self, node, depth=0) -> Quantity:
        if depth > MAX_AST_DEPTH:
            raise ExpressionError("This expression is too deeply nested; split it into named parameters.")
        recurse = lambda child: self.visit(child, depth + 1)
        if isinstance(node, ast.Constant):
            return _quantity(node.value)
        if isinstance(node, ast.Name):
            if node.id.startswith("__unit_"):
                return _UNITS[node.id[7:]]
            if node.id == "pi":
                return Quantity(math.pi)
            if node.id not in self.variables:
                raise ExpressionError(f"Unknown parameter '{node.id}'. Define it in Fusion Parameters or use a literal value.")
            variable = self.variables[node.id]
            if not isinstance(variable, Quantity):
                raise ExpressionError(f"Parameter '{node.id}' must have a value and a physical dimension.")
            return _quantity(variable.value, _dims(variable))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            quantity = recurse(node.operand)
            return _quantity(quantity.value * (-1 if isinstance(node.op, ast.USub) else 1), _dims(quantity))
        if isinstance(node, ast.BinOp):
            left, right = recurse(node.left), recurse(node.right)
            left_dims, right_dims = _dims(left), _dims(right)
            if isinstance(node.op, (ast.Add, ast.Sub)):
                if left_dims != right_dims:
                    raise ExpressionError("Addition and subtraction require matching units. Give offsets explicit units, such as 'shaft + 0.2 mm'.")
                sign = -1 if isinstance(node.op, ast.Sub) else 1
                return _quantity(left.value + sign * right.value, left_dims)
            if isinstance(node.op, ast.Mult):
                return _quantity(left.value * right.value, tuple(a + b for a, b in zip(left_dims, right_dims)))
            if isinstance(node.op, ast.Div):
                if right.value == 0:
                    raise ExpressionError("The expression divides by zero.")
                return _quantity(left.value / right.value, tuple(a - b for a, b in zip(left_dims, right_dims)))
            if isinstance(node.op, ast.Pow):
                if right_dims != (0, 0) or abs(right.value) > MAX_EXPONENT:
                    raise ExpressionError("Exponents must be unitless and between -16 and 16.")
                if left_dims != (0, 0) and not right.value.is_integer():
                    raise ExpressionError("Use integer powers for dimensioned values, or sqrt() for square roots.")
                if left.value < 0 and not right.value.is_integer():
                    raise ExpressionError("A negative number cannot have a fractional real power.")
                if left.value == 0 and right.value < 0:
                    raise ExpressionError("Zero cannot be raised to a negative power.")
                dims = tuple(int(power * right.value) for power in left_dims)
                try:
                    return _quantity(left.value ** right.value, dims)
                except OverflowError:
                    raise ExpressionError("The power exceeds the supported numeric range.") from None
            raise ExpressionError("Use +, -, *, / or ** for arithmetic; this operator is unsupported.")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCTIONS or node.keywords:
                raise ExpressionError("Supported functions are sin, cos, tan, sqrt, abs, min and max, with positional arguments.")
            name = node.func.id
            if not node.args or len(node.args) > 16 or (name not in ("min", "max") and len(node.args) != 1):
                raise ExpressionError(f"{name}() has the wrong number of arguments.")
            args = [recurse(arg) for arg in node.args]
            quantity = args[0]
            dimension = _dims(quantity)
            if name in ("min", "max"):
                if any(_dims(arg) != dimension for arg in args):
                    raise ExpressionError(f"Every {name}() argument must have matching units.")
                return _quantity((min if name == "min" else max)(arg.value for arg in args), dimension)
            if name == "abs":
                return _quantity(abs(quantity.value), dimension)
            if name == "sqrt":
                if quantity.value < 0:
                    raise ExpressionError("sqrt() requires a nonnegative value.")
                if any(power % 2 for power in dimension):
                    raise ExpressionError("sqrt() requires unitless values or even powers of units.")
                return _quantity(math.sqrt(quantity.value), tuple(power // 2 for power in dimension))
            if dimension not in ((0, 0), (0, 1)):
                raise ExpressionError(f"{name}() requires an angle; use deg or rad units.")
            if name == "tan" and abs(math.cos(quantity.value)) < 1e-12:
                raise ExpressionError("tan() is undefined at this angle.")
            return _quantity(getattr(math, name)(quantity.value))
        raise ExpressionError("This syntax is unsupported. Use arithmetic, units, named parameters and supported functions.")


def evaluate(expression: str, unit: str, variables: Mapping[str, Quantity] | None = None) -> float:
    """Resolve a safe expression to display units without mutating its text.

    Bare numbers use the requested display unit; dimensioned arithmetic uses
    strict dimensional analysis. Trigonometric inputs without units are radians.
    Existing parameter values must be supplied as canonical ``Quantity`` objects.
    """
    output_units = {"": ((0, 0), 1.0), "unitless": ((0, 0), 1.0),
                    "mm": ((1, 0), 1.0), "deg": ((0, 1), math.pi / 180.0)}
    if unit not in output_units:
        raise ExpressionError("Output units must be mm, deg or unitless.")
    prepared = _prepare(expression)
    try:
        tree = ast.parse(prepared, mode="eval")
    except (SyntaxError, RecursionError, ValueError):
        raise ExpressionError("Check the expression syntax. Use explicit operators and units such as '2 * module' or '20 deg'.") from None
    if sum(1 for _ in ast.walk(tree)) > MAX_AST_NODES:
        raise ExpressionError("This expression is too complex; split it into named parameters.")
    quantity = _Evaluator(variables).visit(tree.body)
    wanted_dimension, scale = output_units[unit]
    dimension = _dims(quantity)
    if dimension == (0, 0):
        return quantity.value
    if dimension != wanted_dimension:
        raise ExpressionError(f"This field requires {unit or 'unitless'} values; the expression has incompatible units.")
    return _quantity(quantity.value / scale).value
