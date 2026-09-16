import math
import unittest

from GearStudio.core.expressions import ExpressionError, Quantity, evaluate


class ExpressionTests(unittest.TestCase):
    def test_physical_unit_conversions(self):
        for expression, unit, expected in [
            ("1 in", "mm", 25.4), ("2inch", "mm", 50.8),
            ("1 cm + 3 mm", "mm", 13), ("0.002 m", "mm", 2),
            ("pi rad", "deg", 180), ("90 deg", "deg", 90),
            ("(1+2) mm", "mm", 3),
        ]:
            with self.subTest(expression=expression):
                # A named scalar needs an explicit multiplication operator.
                expression = expression.replace("pi rad", "pi * rad")
                self.assertAlmostEqual(evaluate(expression, unit), expected)

    def test_bare_values_adopt_requested_unit(self):
        self.assertEqual(evaluate("20 + 5", "deg"), 25)
        self.assertEqual(evaluate("1.5", "mm"), 1.5)
        self.assertEqual(evaluate("24 * 2", "unitless"), 48)

    def test_named_parameters_preserve_dimensions(self):
        variables = {
            "shaftDiameter": Quantity(5, "length"),
            "boreAllowance": Quantity(0.2, "length"),
            "helix": Quantity(math.pi / 6, "angle"),
            "ratio": Quantity(3),
        }
        self.assertAlmostEqual(evaluate("shaftDiameter + boreAllowance", "mm", variables), 5.2)
        self.assertAlmostEqual(evaluate("helix", "deg", variables), 30)
        self.assertAlmostEqual(evaluate("ratio * shaftDiameter", "mm", variables), 15)

    def test_dimensional_calculations_and_functions(self):
        self.assertAlmostEqual(evaluate("sin(30 deg) * 10 mm", "mm"), 5)
        self.assertAlmostEqual(evaluate("sqrt((3 mm)**2 + (4 mm)**2)", "mm"), 5)
        self.assertEqual(evaluate("(10 mm) / (2 mm)", "unitless"), 5)
        self.assertEqual(evaluate("max(1 cm, 12 mm) - abs(-2 mm)", "mm"), 10)
        self.assertEqual(evaluate("min(3, 5, 2)", "unitless"), 2)
        self.assertAlmostEqual(evaluate("cos(pi) + sqrt(4)", "unitless"), 1)

    def test_incompatible_units_fail_instead_of_flattening(self):
        for expression, unit in [("1 mm + 2 deg", "mm"), ("1 mm", "unitless"),
                                 ("1 deg", "mm"), ("sqrt(2 mm)", "mm"),
                                 ("cos(2 mm)", "unitless"), ("min(1 mm, 2)", "mm"),
                                 ("1 mm + 2", "mm")]:
            with self.subTest(expression=expression):
                with self.assertRaises(ExpressionError):
                    evaluate(expression, unit)

    def test_unknown_names_are_actionable(self):
        with self.assertRaisesRegex(ExpressionError, "Unknown parameter 'shaftDiameter'"):
            evaluate("shaftDiameter + 0.2 mm", "mm")

    def test_invalid_math_is_bounded(self):
        for expression in ["1/0", "sqrt(-1)", "(-1)**0.5", "0**-2", "1e999",
                           "10**10000", "tan(90 deg)", "2**(2**16)"]:
            with self.subTest(expression=expression):
                with self.assertRaises(ExpressionError):
                    evaluate(expression, "unitless")

    def test_executable_and_unsupported_syntax_is_rejected(self):
        for expression in ["__import__('os').system('anything')", "(1).__class__", "[1,2]",
                           "True", "lambda: 1", "1 if 2 else 3", "max(x=1)",
                           "sum([1,2])", "1; 2", "1 # comment", "2 << 20", "1j", "2^3",
                           "__unit_mm", "'text'", "sin()"]:
            with self.subTest(expression=expression):
                with self.assertRaises(ExpressionError):
                    evaluate(expression, "unitless")

    def test_complexity_limits(self):
        for expression in ["1" * 513, "+".join(["1"] * 100), "abs(" * 30 + "1" + ")" * 30]:
            with self.subTest(size=len(expression)):
                with self.assertRaises(ExpressionError):
                    evaluate(expression, "unitless")

    def test_variable_values_must_be_finite_and_typed(self):
        for value in [Quantity(float("nan")), Quantity(float("inf")), Quantity(True),
                      Quantity(5, "unsupported"), 5]:
            with self.subTest(value=value):
                with self.assertRaises(ExpressionError):
                    evaluate("foo", "unitless", {"foo": value})

    def test_input_is_not_mutated(self):
        variables = {"module": Quantity(1, "length")}
        expression = "2 * module"
        self.assertEqual(evaluate(expression, "mm", variables), 2)
        self.assertEqual(expression, "2 * module")
        self.assertEqual(variables, {"module": Quantity(1, "length")})


if __name__ == "__main__":
    unittest.main()
