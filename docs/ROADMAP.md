# Gear Studio roadmap

This roadmap describes remaining work, not promised dates or implemented features. Version 0.1.0 is an evaluation implementation. The immediate priority is a dependable native Fusion editing cycle across the existing families.

## 1. Verify the implementation in desktop Fusion

Run the [acceptance matrix](ACCEPTANCE.md) on Windows and macOS and attach results to the [verification record](VERIFICATION.md). Record the Fusion build, OS, repository commit, inputs, result and elapsed time.

Exit criteria:

- Every exposed variant creates a valid single B-rep and survives a meaningful edit and explicit parameter-table update.
- Invalid inputs reject before expensive work where possible. Cancellation, candidate cleanup and failed-commit recovery leave a usable design.
- Save/reopen, independent duplicates, presets, last-used defaults and expression dependencies behave as documented.
- Undo/redo and component placement are verified. Changed tooth-face references are identified and handled honestly.
- Install, update, backup and rollback work on both platforms. Any failing family or unsupported Fusion mode is gated or documented with a concrete limitation.

Pure tests and a successful CI run do not satisfy these native-host criteria.

## 2. Quantify geometry quality and performance

Add regression fixtures for actual failed input combinations, measured dimensions, profile deviation and build time. Measure spline/loft/envelope approximation against the underlying mathematical construction. Include small and large modules, signed helix angles, low tooth counts, internal rings and limiting bevel/worm/crown cases.

Use those measurements to choose justified supported ranges, preview fidelity and build budgets. Add alternative detail levels only when their accuracy/performance tradeoffs can be described. Expand useful diagnostics without exposing long implementation traces in ordinary form errors.

Exit criteria: a reproducible fixture set, published measurement method, clear supported ranges, and documented numerical tolerances. A passing solid-kernel check alone does not establish correct gear contact.

## 3. Improve parameter-driven updates

Current behavior is explicit: edit Fusion parameters, then run **Update from Parameters** for the selected gear. Preserve that reliable path while investigating smoother updates.

First add clear document-level detection of stale gears and a bounded **Update affected gears** operation in dependency order. Report the individual successes/failures and prevent expression cycles.

Then evaluate automatic regeneration using APIs suitable for distribution. Recheck Autodesk's Custom Features status at implementation time; it was still documented as preview during the [research refresh](RESEARCH.md). Any experiment with preview functionality should remain separate from the default installed path.

Exit criteria: no rebuild on each keystroke, no event recursion or accidental document switch, coherent undo, saved expression relationships, dependency-aware updates, and preservation/recovery of previous solids when one update fails. Automatic updates must not be advertised before native-host testing demonstrates them.

## 4. Design mating pairs and mechanisms

Here, **mating** means tooth engagement between solid gears. The deliverables remain B-reps.

Start with external spur and helical pairs. Add shared tooth-system inputs, ratio or tooth-count selection, center distance, handedness, profile-shift compatibility and an explicit allocation of total pair backlash. Generate both members with persistent identities and linked definitions.

Extend after verification to internal pairs, rack/pinion systems, worm drives, bevel pairs and crown/pinion systems. Planetary assemblies need additional spacing, phasing and assembly-access checks. Pair geometry must be tested through a complete rotation or representative contact cycle; two individually valid solids are insufficient evidence.

Exit criteria: reproducible compatible pairs, documented limits and assembly placement, pair-level validation, and coordinated edit behavior. Strength ratings and ISO/AGMA grades remain separate engineering work.

## 5. Expand practical coverage

After the shared lifecycle is proven, evaluate shaft interfaces, center relief options, manufacturing presets, cycloidal/noncircular gears and other requested families. Prioritize based on reproducible user cases, available mathematical references and maintenance cost.

Every additional family needs catalog fields, stated units, bounded validation, a preview, a native builder, parameter/edit support, persistence, geometry fixtures and live Fusion acceptance. Do not expose a generation control merely because a family has a name or a 2D illustration.

Track actionable work as [repository issues](https://github.com/tensegrity-audio/fusion-gear-add-on/issues). Each issue should state the user outcome and the evidence needed to call it complete.

## 0.3.0 follow-through

Construction history, cutter-body patterning and startup repairs are implemented but require the native acceptance run. The next optimization is updating generated sketches/features in place where topology is unchanged; current native-history Update rebuilds the generated Construction child and preserves the outer component. Stable downstream generated-body references, quantified tooth-profile error and native cross-platform/DPI acceptance remain open work.
