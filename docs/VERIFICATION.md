# Verification record

Release: Gear Studio 0.1.2

Date: 2026-09-16

Status: Evaluation build. Native Fusion acceptance is pending.

## Reported native startup failure

On 2026-09-16, Griffin reported that Fusion on Windows found the directly linked
`GearStudio` folder and entered `GearStudio.py`, but failed in
`CommandDefinitions.addButtonDefinition` with `RuntimeError: 3 : invalid id`.
The command being registered used the dotted ID `griffin.gearstudio.open.v1`.
The full Fusion version and Windows version were not supplied.

Version 0.1.1 replaces all three UI identifiers with a conservative ASCII
letters/digits/underscores convention and adds a startup regression test at the
API boundary. Native confirmation of the correction is pending. No gear
construction or editing result can be inferred from this startup report.

## Reported preview/connection failure

A subsequent Windows screenshot showed an interactive panel labelled Interface
preview together with the native controller error, "This action is not available
in this version of Gear Studio." The screenshot establishes that the panel can
open, but does not identify its exact installed revision or prove a gear build.

Inspection found two defects: demo.js assigned a fake `window.adsk` whenever the
real bridge was not yet available, and the native HTML handler treated Fusion's
`response` acknowledgement as an application request. Version 0.1.2 isolates the
explicit preview transport, waits for the live connection and filters those
acknowledgements. Native confirmation of the correction and the first B-rep
build remains pending.

## Completed in the development environment

- **138 Python unittest checks passed.** They cover numeric and geometric validation, expression dimensions, bounded dependency resolution, persistence and independent templates, controller lifecycle, candidate cleanup, document update and rollback logic, and selected upstream mathematical invariants. The 0.1.1 addition exercises command and palette registration, toolbar reopening and shutdown through an API substitute with a conservative identifier restriction.
- Four 0.1.2 Python additions cover response acknowledgements, error-feedback suppression, correlated handshakes and delivery of an HTML build request into the candidate-preparation lifecycle through host substitutes.
- **Chromium interface checks passed.** These exercise stale validation responses, invalid-input build guards, expression drafts, edit identity, cancellation, and the browser preview's refusal to claim native geometry creation. The 0.1.2 checks also simulate delayed bridge injection, a lost startup message, bounded timeout and retry, a late startup reply during a build, exactly one Create gear request, and explicitly isolated browser preview. The bridge is a controlled test substitute for Fusion.
- **Earlier interface visual review completed** for the desktop panel and a narrow panel. Both fit their viewport without horizontal document overflow. Desktop panels scroll while build controls remain visible. The included screenshot shows the interface preview and its checked default spur profile.
- All 13 family defaults pass the pure validation core.
- Independent OpenCascade checks of eight default cylindrical, internal and rack preview outlines produced valid planar faces and extruded B-rep solids. This verifies those default section outlines, not Fusion's generated three-dimensional bodies.
- Python compilation, JavaScript syntax and macOS installer shell syntax passed.
- The publication review added six document tests for name editing and exact name recovery after failed updates. Dedicated gear names update together; Part roots and shared parents are preserved.
- GitHub Actions is configured for five Python/OS combinations, a Chromium interface check and a gated evaluation ZIP artifact. The Actions run is the source of truth for hosted-runner results; local tests do not establish cross-platform host acceptance.
- The release packaging checks required files and licenses, computes SHA-256 checksums and verifies the ZIP archive.

## Not run here

Autodesk Fusion is not installed in this environment. Native B-rep construction, command event ordering and undo behavior, actual parameter table interaction, downstream reference stability, and Windows/macOS installation must be checked in Fusion. The source tests use host substitutes at API boundaries and do not establish native compatibility.

Use [ACCEPTANCE.md](ACCEPTANCE.md) to record those results. Verify at least one creation, edit, parameter update, invalid-input rejection, cancellation, save/reopen and undo cycle before relying on the add-in in a working design. Each gear family has its own pending native geometry acceptance row.

There is no certified maximum profile deviation, pair-interference guarantee, ISO/AGMA grade or strength rating. Supported input bounds and cancellation checkpoints reduce avoidable failures; an individual Fusion modeling-kernel operation cannot be forcibly interrupted by the add-in.

## Reproduce the automated checks

From the extracted release root:

```sh
python -m unittest discover -s tests -v
python -m compileall -q GearStudio tests tools
npm ci
npx playwright install chromium
npm run check:ui
npm run test:ui
python tools/package.py --check
```

The browser test requires Playwright and a Chromium browser as development dependencies. `PLAYWRIGHT_CHROMIUM_EXECUTABLE` may specify an existing compatible Chromium executable. These development dependencies are not required by the Fusion add-in and are not included in the release.
