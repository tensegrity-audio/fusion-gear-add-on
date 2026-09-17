# Live Fusion acceptance checklist

**Status: incomplete.** Windows reports include the command-ID failure, preview/connection failure and a later commit failure saying the design is not parametric. The 2026-09-17 screenshot shows real User Parameter rows with legacy names. It does not show the solid or establish native acceptance of creation, editing or the new 0.2.0 rename action. The remaining checklist is pending live execution. Host-independent Python tests and browser rendering checks cannot establish that Fusion's modeling kernel, palettes, document transactions or installation paths work on a specific release.

## Reported failure and retest

- 2026-09-16, Griffin, Windows, directly linked extracted repository: Fusion loaded the entry point, then command registration failed with `RuntimeError: 3 : invalid id`. Full Fusion and OS versions were not supplied.
- 0.1.1 changes the dotted command/palette IDs to letters, digits and underscores. Retest startup, toolbar reopening, stop/start and Run on Startup using the updated copy. Native retest result: **Pending**.

- Subsequent Windows screenshot: the panel opens with Interface preview and the native unsupported-action error; installed revision was not provided. Version 0.1.2 isolates preview mode and ignores host acknowledgements. Live handshake and default Spur creation retest: **Pending**.

- Later Windows screenshot: commit fails with `3 : this is not a parametric design`. Version 0.1.3 moves parameter writes outside Base Feature editing. Retest creation, panel editing and Update from Parameters in a history-enabled Part and Hybrid design: **Pending**. Record the installed version and the full stage-specific message/log if it fails again.

Run this checklist on both supported desktop platforms before calling a release host-verified. Use disposable designs and keep the tested release ZIP and checksum with the results.

## Test record

| Item | Windows | macOS |
| --- | --- | --- |
| Tester and date | Pending | Pending |
| Fusion version / build | Pending | Pending |
| OS version | Pending | Pending |
| Release ZIP SHA-256 | Pending | Pending |
| Install method | Pending | Pending |
| Overall outcome | Not run | Not run |

Record **Pass**, **Fail**, or **Not run** for each case, with the design file and reproduction steps for failures. Do not mark a source-level substitute as a native Fusion pass.

## Installation and interface

- [ ] A beginner follows START_HERE.html from an extracted ZIP without a terminal or installer. Confirm the exact Documents folder, linked inner GearStudio folder, first solid and first edit.
- [ ] Getting started shows the actual loaded version and folder, is usable while disconnected, and closes without replacing an expression draft. Compare the olive/lime interface at desktop and narrow Fusion palette sizes.
- [ ] Close Fusion, put the repository in Documents/FusionAddins, link its inner GearStudio folder and run it without administrator access. Separately check the optional installer-managed layout if distributing those scripts.
- [ ] Confirm the native panel changes from Connecting to Fusion to Autodesk Fusion, never Interface preview; default Spur validates and Create gear produces a B-rep in the active design.
- [ ] Confirm startup and subsequent field edits do not produce unsupported `response` errors. If the bridge cannot connect, verify the bounded timeout and Retry connection control.
- [ ] Confirm the panel opens, closes and reopens from its toolbar command.
- [ ] Restart Fusion with Run on Startup enabled; confirm one working command and panel, without duplicate handlers.
- [ ] Resize the panel at narrow and wide widths; labels, expressions, validation and build/cancel controls remain usable.
- [ ] Confirm the normal host panel does not display a browser-demo state, and the standalone interface preview does not claim to build Fusion solids.
- [ ] Update an existing installation using the script; verify the backup can be restored and last-used settings/presets survive.
- [ ] Stop and uninstall the add-in. Confirm saved B-reps remain in a reopened design.

## Geometry matrix

For **every row**, first build the catalog default and confirm **one valid closed B-rep solid**, positive volume, expected bore/ring/backing, orientation and dimensions. Save the design, then reopen and edit that gear. Change tooth count where available and one other geometry-driving dimension. Confirm the body actually changes and remains one solid. Record measured values, time, and any kernel messages.

| Variant | Initial B-rep | Edit/rebuild | Parameter-table update | Reopen/edit |
| --- | --- | --- | --- | --- |
| Spur | Not run | Not run | Not run | Not run |
| Helical | Not run | Not run | Not run | Not run |
| Herringbone | Not run | Not run | Not run | Not run |
| Internal spur | Not run | Not run | Not run | Not run |
| Internal helical | Not run | Not run | Not run | Not run |
| Internal herringbone | Not run | Not run | Not run | Not run |
| Straight rack | Not run | Not run | Not run | Not run |
| Helical rack | Not run | Not run | Not run | Not run |
| Worm | Not run | Not run | Not run | Not run |
| Worm wheel | Not run | Not run | Not run | Not run |
| Straight bevel | Not run | Not run | Not run | Not run |
| Spiral bevel | Not run | Not run | Not run | Not run |
| Crown / face | Not run | Not run | Not run | Not run |

Additional family checks:

- [ ] Spur: measure pitch-related dimensions against the selected module and tooth count; compare positive tooth thinning against zero thinning.
- [ ] Helical: test positive and negative helix angles and measure handedness; normal/transverse conventions produce the expected diameter.
- [ ] Herringbone: confirm joined opposed halves with one solid, correct total face width and no unintended central opening.
- [ ] Internal families: confirm the selected ring diameter and positive rim; teeth point into the ring. Check assembly access for an internal herringbone pair.
- [ ] Racks: verify tooth-pitch count, back height, length direction and helical tooth trace.
- [ ] Worm and wheel: use matching module, pressure angle, starts and worm diameter. Verify axial orientation and wheel envelope; do not infer pair contact from a successful individual solid build.
- [ ] Bevel families: generate an unequal-tooth-count pair using exchanged counts, align cone apexes and inspect contact/clearance. Test spiral hand changes and confirm expected outer-normal-module convention.
- [ ] Crown: use the specified generating pinion, confirm radial face width, backing thickness and bore, then verify pair placement and usable face extent.

## Expressions and actual parameter use

- [ ] Create the default Spur in both Part and Hybrid designs with history enabled. In 0.2.0, confirm one B-rep and names such as `Module_G1` and `Teeth_G1`. Edit teeth from 24 to 30 in the panel, then change the generated teeth parameter to 32 and use **Update from Parameters**. Confirm geometry follows each change, editing ends normally and design history stays enabled.
- [ ] Create two gears with the same display name and one unrelated native parameter ending in `_G1`. Confirm all generated names are unique, use one suffix per gear, and remain stable after renaming the gear and reopening the design.
- [ ] Open a pre-0.2.0 gear with `GS_...` names. Confirm ordinary editing works before using Shorten parameter names. Add an external expression and another gear referencing its module, then shorten the selected gear's names. Verify both native expressions and saved gear definitions follow the new names, geometry stays unchanged, and pending table edits remain marked as needing an update.
- [ ] Undo and Redo the name upgrade; confirm names, dependent expressions and saved mappings agree. Save/reopen and update from the renamed parameters. If an upgrade fails, verify complete restoration or explicit Undo guidance.
- [ ] Create external `shaftDiameter` and `boreAllowance` length parameters. Enter `shaftDiameter + boreAllowance` for bore and build. Confirm the generated parameter retains the expression and the measured bore matches it.
- [ ] Change `shaftDiameter` in Fusion's Parameters dialog. Confirm the add-in identifies changed inputs on refresh/edit, and geometry changes only after **Update from Parameters**.
- [ ] Change each family's tooth count or other principal count in the parameter table; explicitly update and measure the resulting geometry.
- [ ] Use compatible explicit unit conversions, including inches for a length and degrees for an angle; verify geometry is not scaled by 10 or by a radians/degrees error.
- [ ] Create a valid dependency between two gears' parameters. Update them in dependency order and confirm expected results without losing expressions.
- [ ] Attempt self-reference and a longer dependency cycle. Confirm an actionable rejection before native preparation and unchanged existing geometry.
- [ ] Rename or remove a generated parameter; confirm the add-in gives the missing-name guidance and does not silently create an unrelated replacement gear.
- [ ] Attempt a dimensional mismatch, unknown parameter and noninteger count. Confirm no solid build starts.
- [ ] Change a referenced parameter while a candidate is preparing, if Fusion allows interaction. Confirm the candidate is rejected if inputs no longer match.

## Invalid inputs, bounded work and cancellation

For each case, compare the existing component, source body, parameters and persisted definition before and after the attempt.

- [ ] Submit zero/negative module, zero/negative width, fractional or excessive tooth counts, nonfinite-looking input and invalid syntax.
- [ ] Try a bore exceeding the available root/web, an undersized internal ring and a rack height that leaves no backing.
- [ ] Try unsupported helix/shaft-angle limits, incompatible bevel width/cone geometry and an impossible worm start/diameter combination.
- [ ] Enter a high-complexity valid-looking case that exceeds the estimated budget. Confirm preflight explains the limit before kernel construction.
- [ ] Rapidly edit fields. Confirm only the newest validation/preview response is displayed and no native build occurs while typing.
- [ ] Start a nontrivial permitted build, press Cancel and verify cancellation at the next supported checkpoint. Record any single native operation that does not yield promptly.
- [ ] Induce an ordinary native modeling failure with an accepted but unbuildable combination, if found. Confirm temporary-document cleanup and preservation of the old gear. Save that combination as a regression case.
- [ ] Switch or close documents during preparation if permitted. Confirm no candidate is committed into the wrong document.
- [ ] After failure/cancel, successfully build a simple gear without restarting Fusion.

## Commit, undo and downstream references

- [ ] Build a new gear, Undo and Redo. Verify body, component, parameter rows and definition agree at each step.
- [ ] Edit an existing gear, Undo and Redo. Verify the prior and updated geometry, parameter expressions and definition agree.
- [ ] Move/place a component and create an assembly reference to its origin/axis/plane. Update tooth count and confirm component identity and placement remain.
- [ ] Create a downstream operation or reference to a tooth face. Change tooth count and inspect reference health. Record limitations; a stable component does not guarantee stable tooth faces.
- [ ] Duplicate using **Duplicate** in Gear Studio and update each independently. Confirm unique identities and parameters, including sources whose own fields reference short aliases and legacy `GS_...` aliases.
- [ ] Copy a component using ordinary Fusion copy/paste. Confirm duplicate identities are detected rather than silently editing both.
- [ ] Try editing an unowned body, linked component or unsupported design mode. Confirm a clear rejection.
- [ ] If a commit failure can be induced without corrupting the test host, confirm recovery restores body, parameters and definition or clearly reports incomplete recovery. Do not mark this case passed based only on candidate-build failure.

## Persistence

- [ ] Successfully build distinct settings for two gear types. Restart Fusion and confirm each type restores its own most recent successful settings.
- [ ] Make an invalid attempt; reopen the panel and confirm it did not replace successful defaults.
- [ ] Save, load, update by same name, and delete a named preset. Confirm expression text survives.
- [ ] Save a preset and last-used defaults from a gear with internal generated-parameter references; create another gear and confirm those source-owned aliases were expanded while external parameter expressions remain intact.
- [ ] Load a preset referencing a missing document parameter. Confirm validation reports it and no native build occurs.
- [ ] Save, close and reopen a Fusion design containing several gears, then edit each definition correctly.
- [ ] With Fusion closed, preserve and deliberately corrupt a test `settings.json`; reopen and confirm the corrupt file is backed up and a usable empty state is offered.
- [ ] Test a read-only preferences location in a controlled environment. Confirm geometry success is distinguished from preference-save failure and existing settings are not discarded.

## Release decision

Record the host-tested subset, unresolved failures and exact Fusion builds. Until the full matrix is executed, describe the package as an implementation for evaluation with live Fusion verification pending. A preview screenshot, passing Python tests or successful creation of one spur gear is not evidence that all 13 variants and both update paths work in Fusion.
