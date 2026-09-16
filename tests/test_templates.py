from copy import deepcopy
import unittest
from unittest import mock

from GearStudio.core.templates import TemplateError, template_spec


def gear(parameters):
    return {"schema_version": 1, "id": "12345678-1234-1234-1234-123456789012", "kind": "spur",
            "name": "Drive gear", "parameters": parameters, "placement": {"x": 12}}


class TemplateTests(unittest.TestCase):
    def test_owned_dependencies_expand_and_external_references_remain_live(self):
        source = gear({"module": "SharedModule", "width": "GS_source_module * 10",
                       "bore": "GS_source_width / 2 + shaftAllowance"})
        names = {"module": "GS_source_module", "width": "GS_source_width", "bore": "GS_source_bore"}
        result = template_spec(source, names)
        self.assertEqual(result["parameters"]["width"], "(SharedModule) * 10")
        self.assertEqual(result["parameters"]["bore"], "((SharedModule) * 10) / 2 + shaftAllowance")
        self.assertNotIn("id", result)
        self.assertNotIn("placement", result)

    def test_default_owned_names_follow_gear_id_convention(self):
        source = gear({"module": "1 mm", "width": "GS_123456781234_module * 10"})
        self.assertEqual(template_spec(source)["parameters"]["width"], "(1 mm) * 10")

    def test_token_boundaries_preserve_underscores_and_unicode_names(self):
        source = gear({"module": "外径 / 24", "width": "GS_owned + _GS_owned + GS_owned_extra + αGS_owned + GS_ownedα + 日本語"})
        result = template_spec(source, {"module": "GS_owned"})
        self.assertEqual(result["parameters"]["width"],
                         "(外径 / 24) + _GS_owned + GS_owned_extra + αGS_owned + GS_ownedα + 日本語")

    def test_unicode_owned_aliases_are_supported_as_whole_identifiers(self):
        source = gear({"module": "ShaftDiameter", "width": "_歯車径 * 2"})
        self.assertEqual(template_spec(source, {"module": "_歯車径"})["parameters"]["width"], "(ShaftDiameter) * 2")

    def test_unrelated_external_gear_aliases_remain_references(self):
        source = gear({"module": "GS_other_module", "width": "GS_this_module * 10"})
        self.assertEqual(template_spec(source, {"module": "GS_this_module"})["parameters"]["width"],
                         "(GS_other_module) * 10")

    def test_original_definition_and_map_are_unchanged(self):
        source = gear({"module": "  sharedModule  ", "width": "sourceModule*10"})
        names = {"module": "sourceModule"}
        original = deepcopy(source)
        result = template_spec(source, names)
        self.assertEqual(source, original)
        self.assertEqual(names, {"module": "sourceModule"})
        self.assertEqual(result["parameters"]["module"], "  sharedModule  ")
        result["parameters"]["module"] = "5 mm"
        self.assertEqual(source, original)

    def test_cycle_and_self_reference_fail_helpfully(self):
        for parameters in [{"module": "moduleAlias"},
                           {"module": "widthAlias", "width": "moduleAlias"}]:
            names = {key: key + "Alias" for key in parameters}
            with self.assertRaisesRegex(TemplateError, "Circular"):
                template_spec(gear(parameters), names)

    def test_expansion_cannot_grow_exponentially(self):
        parameters = {"p0": "ExternalDiameter"}
        for index in range(1, 16):
            parameters["p%d" % index] = "a%d+a%d" % (index - 1, index - 1)
        names = {key: "a" + key[1:] for key in parameters}
        with self.assertRaisesRegex(TemplateError, "exceeds 256 characters"):
            template_spec(gear(parameters), names)

    def test_deep_dependencies_are_bounded(self):
        parameters = {"p%d" % index: "a%d" % (index + 1) for index in range(34)}
        parameters["p34"] = "1"
        names = {key: "a" + key[1:] for key in parameters}
        with self.assertRaisesRegex(TemplateError, "deeply nested"):
            template_spec(gear(parameters), names)

    def test_work_budget_is_enforced(self):
        with mock.patch("GearStudio.core.templates.MAX_EXPANSION_WORK", 5):
            with self.assertRaisesRegex(TemplateError, "too complex"):
                template_spec(gear({"module": "A + B + C + D + E"}), {})

    def test_plain_new_definition_stays_independent(self):
        source = {"kind": "spur", "parameters": {"module": "shaftDiameter / 12"}}
        self.assertEqual(template_spec(source), source)

    def test_invalid_alias_maps_are_rejected(self):
        source = gear({"module": "1 mm", "width": "10 mm"})
        for names in [{"missing": "GS_missing"}, {"module": "same", "width": "same"},
                      {"module": "has spaces"}]:
            with self.subTest(names=names):
                with self.assertRaises(TemplateError):
                    template_spec(source, names)


if __name__ == "__main__":
    unittest.main()
