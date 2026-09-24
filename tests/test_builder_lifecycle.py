"""Host-boundary tests, not a substitute for Autodesk Fusion solid tests."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from GearStudio.fusion import builder
from GearStudio.vendor.study_gears.guard import bounded, checkpoint, GeometryBudgetExceeded


class FakeDocument:
    def __init__(self, app, name):
        self.app, self.name = app, name
        self.isValid = True
        self.closed_with = None
        self.activated = 0
        self.close_error = None

    def close(self, save):
        self.closed_with = save
        if self.close_error:
            raise self.close_error
        self.isValid = False
        return True

    def activate(self):
        self.activated += 1
        self.app.activeDocument = self
        return True


class BuilderLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.app = SimpleNamespace()
        self.source = FakeDocument(self.app, "Original")
        self.app.activeDocument = self.source
        self.scratch = FakeDocument(self.app, "Scratch")
        self.design = SimpleNamespace()
        self.app.activeProduct = self.design
        self.add_count = 0

        def add(_):
            self.add_count += 1
            self.app.activeDocument = self.scratch
            return self.scratch

        self.app.documents = SimpleNamespace(add=add)
        self.adsk = SimpleNamespace(
            core=SimpleNamespace(DocumentTypes=SimpleNamespace(FusionDesignDocumentType=1)),
            fusion=SimpleNamespace(
                Design=SimpleNamespace(cast=lambda x: x),
                DesignTypes=SimpleNamespace(ParametricDesignType=1),
            ),
            doEvents=lambda: None,
        )
        self.body = SimpleNamespace(
            isValid=True, isSolid=True, lumps=SimpleNamespace(count=1),
            faces=SimpleNamespace(count=150), volume=1.25,
        )
        self.host = patch.object(builder, "_host", return_value=(self.adsk, self.app))
        self.validation = patch.object(builder, "validate", return_value={"valid": True, "issues": []})
        self.host.start()
        self.validation.start()
        self.addCleanup(self.host.stop)
        self.addCleanup(self.validation.stop)

    def build(self, generate=None, **kwargs):
        with patch.object(builder, "_generate", side_effect=generate or (lambda *_: self.body)):
            return builder.build_candidate({"kind": "spur"}, {}, **kwargs)

    def test_success_closes_scratch_without_saving_and_restores_source(self):
        candidate = self.build()
        self.assertIs(candidate.body, self.body)
        self.assertFalse(self.scratch.isValid)
        self.assertIs(self.scratch.closed_with, False)
        self.assertIs(self.app.activeDocument, self.source)
        self.assertEqual(self.source.activated, 1)
        self.assertIsNone(self.source.closed_with)
        candidate.cleanup()
        candidate.cleanup()
        self.assertIsNone(candidate.body)

    def test_kernel_failure_still_closes_scratch_and_restores_source(self):
        def fail(*_):
            raise RuntimeError("ACIS operation failed")
        with self.assertRaisesRegex(builder.BuildError, "ACIS operation failed"):
            self.build(generate=fail)
        self.assertIs(self.scratch.closed_with, False)
        self.assertIs(self.app.activeDocument, self.source)

    def test_sketch_solver_failure_does_not_tell_user_to_change_valid_gear_inputs(self):
        def fail(*_):
            raise builder.SketchConstraintError("Sketch 'Pitch circle': driving diameter failed.")
        with self.assertRaises(builder.BuildError) as raised:
            self.build(generate=fail)
        self.assertIn("Pitch circle", str(raised.exception))
        self.assertNotIn("Reduce face width", str(raised.exception))
        self.assertIs(self.scratch.closed_with, False)
        self.assertIs(self.app.activeDocument, self.source)

    def test_part_intent_scratch_is_changed_to_hybrid_before_generation(self):
        self.design.designIntent = 0
        self.adsk.fusion.DesignIntentTypes = SimpleNamespace(HybridDesignIntentType=2)
        def check_intent(*_):
            self.assertEqual(self.design.designIntent, 2)
            return self.body
        self.build(generate=check_intent)
        self.assertIs(self.app.activeDocument, self.source)

    def test_cancellation_before_build_opens_no_document(self):
        with self.assertRaises(builder.GeometryCancelled):
            self.build(cancelled=lambda: True)
        self.assertEqual(self.add_count, 0)

    def test_active_native_command_blocks_document_creation(self):
        self.app.userInterface = SimpleNamespace(activeCommand="Extrude")
        with self.assertRaisesRegex(builder.BuildError, "active Fusion command"):
            self.build()
        self.assertEqual(self.add_count, 0)

    def test_cancellation_between_geometry_operations_restores_source(self):
        flag = [False]
        def cancel_during_build(*_):
            flag[0] = True
            checkpoint(force=True)
            self.fail("Cancelled calculation must stop before returning geometry")
        with self.assertRaises(builder.GeometryCancelled):
            self.build(generate=cancel_during_build, cancelled=lambda: flag[0])
        self.assertIs(self.scratch.closed_with, False)
        self.assertIs(self.app.activeDocument, self.source)

    def test_document_switch_during_progress_aborts_before_geometry(self):
        def switch(*_):
            self.app.activeDocument = self.source
        with patch.object(builder, "_generate") as generate:
            with self.assertRaisesRegex(builder.BuildError, "active document changed"):
                builder.build_candidate({"kind": "spur"}, {}, progress=switch)
            generate.assert_not_called()
        self.assertIs(self.app.activeDocument, self.source)

    def test_switch_during_event_pump_is_detected(self):
        self.adsk.doEvents = lambda: setattr(self.app, "activeDocument", self.source)
        with self.assertRaisesRegex(builder.BuildError, "active document changed"):
            self.build()
        self.assertIs(self.scratch.closed_with, False)

    def test_invalid_or_disconnected_body_is_not_returned(self):
        self.body.lumps.count = 2
        with self.assertRaisesRegex(builder.BuildError, "disconnected pieces"):
            self.build()
        self.assertFalse(self.scratch.isValid)

    def test_cleanup_failure_prevents_candidate_commit_but_restores_source(self):
        self.scratch.close_error = RuntimeError("close was rejected")
        with self.assertRaisesRegex(builder.BuildError, "close was rejected"):
            self.build()
        self.assertIs(self.app.activeDocument, self.source)

    def test_invalid_inputs_never_create_scratch(self):
        with patch.object(builder, "validate", return_value={
            "valid": False, "issues": [{"severity": "error", "message": "Bore is too large."}],
        }):
            with self.assertRaisesRegex(builder.BuildError, "Bore is too large"):
                self.build()
        self.assertEqual(self.add_count, 0)


class GuardTests(unittest.TestCase):
    def test_iteration_budget_is_a_hard_bound_and_resets_after_failure(self):
        with self.assertRaises(GeometryBudgetExceeded):
            with bounded(iterations=10):
                for _ in range(100):
                    checkpoint()
        with bounded(iterations=10):
            checkpoint()

    def test_expired_deadline_stops_before_work(self):
        with self.assertRaises(GeometryBudgetExceeded):
            with bounded(seconds=-1):
                self.fail("Expired budget must not enter the calculation")


if __name__ == "__main__":
    unittest.main()
