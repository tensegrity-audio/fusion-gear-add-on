# Verification record

Release: Gear Studio 0.3.3

Date: 2026-09-24

Status: Evaluation build. Native Fusion acceptance is pending.

## 0.3.3 coworker build failure and field help

The supplied September 24 screenshot shows a Hybrid design and a Spur build blocked by `The generated diameter or center is still unconstrained`, a check introduced in 0.3.2. It establishes a failure of that build gate, not invalid gear inputs. The exact Fusion build was not supplied. The screenshot does not prove why Fusion returned false, nor which circle was involved. Mixed planar circle/out-of-plane axis geometry was found in the reference sketch and is now separated.

The circle helper now fixes only the center at the local origin and verifies its position, a driving dimension, evaluated diameter and actual radius. Verified circles do not depend on aggregate constraint flags; other geometry remains checked. A regression substitute reproduces false aggregate flags with valid dimensional constraints, and additional tests reject wrong diameters and free points. Error messages distinguish sketch construction failures from invalid inputs. These are boundary tests, not a reproduction of the native solver.

Field information icons are real keyboard/click buttons opening local dialogs. The default view removes repeated descriptions and disabled empty-selection actions, and collapses tooth settings and measurements. Browser checks pass for help, focus restoration, no accidental build, hidden-error disclosure, draft preservation and five responsive widths. Desktop and narrow screenshots were reviewed. 175 Python checks, browser checks, compilation and package verification passed. Native default Spur/Helical/Herringbone builds and live bore drag/recompute checks remain pending.

## 0.3.2 reported loose bore and reference geometry

Griffin reports that a herringbone gear now generates successfully, but its hole diameter and a vertical sketch line are unconstrained and the geometry appears movable in XY. The installed commit/Fusion version and whether the movement is at sketch or component level were not supplied. This confirms a successful native herringbone build in the user's environment; it does not establish a dimensional or constraint acceptance pass.

The native cylinder builder previously added a circle with no center or diameter constraint. The new helper adds local-origin coincidence and a driving diameter; committed bores link that diameter to their saved alias. Cylindrical calculated profiles now lock remaining points as well as curves; the reference shaft line has fixed endpoints. Affected sketches must report fully constrained or construction fails. Tests exercise these API contracts using substitutes, unit conversion, failure rejection, live alias forwarding, outer placement/grounding and detaching old diameters before user inputs change. Direct table edits to a bore invoke Fusion's solver outside Gear Studio's validation boundary; this is documented, with panel editing as the validate-first path.

Native checks of drag resistance, actual expression recomputation, old-gear regeneration, save/reopen and Undo/Redo are **pending**. Fusion is not installed here; the substitutes do not certify its sketch solver or command rollback. See the 0.3.2 checklist in ACCEPTANCE.md.

## 0.3.1 reported entry-point import failure

A Windows traceback shows `from .. import __version__` resolving to the generated `GearStudio.py` package rather than `__init__.py`. The loader regression reproduced that exact ImportError before the change. Importing the dedicated `version.py` module removes the package-initializer dependency. The regression now imports the complete controller dependency chain under the generated name and verifies run/stop delegation using host substitutes. Release versions agree across Python, the Fusion manifest and npm metadata. Actual Fusion startup confirmation remains pending.

## 0.3.0 reported geometry, history and startup defects

Griffin supplied screenshots of default helical and herringbone solids with one apparent full groove and shallow repeated seams, a palette that only rendered correctly after resizing, and a Base Feature timeline icon. These establish native creation with unacceptable tooth geometry and missing construction history. The exact installed commit and Fusion build were not supplied.

The source now patterns solid cylindrical cutters, checks cutter count and samples actual B-rep material/air around multiple pitches and axial sections. New gears retain native construction under a movable component. Toolbar lifecycle handlers, one-time palette size repair and SVG icons address the startup/rendering reports. Tests exercise geometric oracles for all six cylindrical defaults and the single-groove failure, component/placement preservation, dependency-loss rejection, startup timing and bounded palette repair.

**Native verification is pending.** Fusion is not installed here. Passing Python/Chromium tests does not establish correct ACIS lofts/booleans, native command rollback, first paint in Fusion's Qt host or Windows DPI behavior. Run the 0.3.0 regression checklist in ACCEPTANCE.md before treating this as a validated release.

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

## Reported parameter commit failure

A later Windows screenshot reports: "Fusion could not commit this gear. The
previous geometry and parameters were restored. 3 : this is not a parametric
design." This establishes that execution reached the native commit handler,
past candidate preparation and the history preflight. It does not prove a
successful commit or independently verify the reported recovery.

Inspection found parameter writes inside `BaseFeature.startEdit()` / `finishEdit()`.
Autodesk describes a [Base Feature](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_BaseFeature.htm)
as a direct edit feature within a parametric design. That context mismatch is the
likely cause; the screenshot does not include the exact failing API call.
Version 0.1.3 moves parameter writes before source-feature editing without
changing the design mode, and adds stage-specific messages and chained native
tracebacks to the log. The document substitute now rejects parameter mutations
during source-feature editing: the previous implementation fails that contract,
while the corrected creation, update and recovery paths pass. This substitute
does not establish native API compatibility. Live retest remains pending.

## Completed in the development environment

- **175 Python unittest checks passed.** They cover numeric and geometric validation, expression dimensions, bounded dependency resolution, persistence and independent templates, controller lifecycle, candidate cleanup, document update and rollback logic, and selected upstream mathematical invariants. The 0.1.1 addition exercises command and palette registration, toolbar reopening and shutdown through an API substitute with a conservative identifier restriction.
- Four 0.1.2 Python additions cover response acknowledgements, error-feedback suppression, correlated handshakes and delivery of an HTML build request into the candidate-preparation lifecycle through host substitutes.
- Five 0.1.3 additions cover cleanup after partial parameter creation, parameter recovery after rejected edit entry, stage-specific native failures, chained tracebacks in the log and concise validation errors. All document mutation/recovery tests run with the parameter-mode restriction described above.
- Nine 0.2.0 additions cover short-name allocation/collisions, stable names, family label coverage, legacy editing, native-object identity and pending edits during renaming, cross-gear saved expressions, recovery after partial renaming/metadata/recompute/reference failures, idempotence, and the native-command route without geometry preparation. Native name setters and dependent-reference rewriting are modeled by substitutes, not exercised in Fusion here.
- **Chromium interface checks passed.** These exercise stale validation responses, invalid-input build guards, expression drafts, edit identity, cancellation, and the browser preview's refusal to claim native geometry creation. The 0.1.2 checks also simulate delayed bridge injection, a lost startup message, bounded timeout and retry, a late startup reply during a build, exactly one Create gear request, and explicitly isolated browser preview. The bridge is a controlled test substitute for Fusion.
- **0.2.0 interface checks passed** at widths 1440, 1180, 760, 420 and 320 px without horizontal document overflow or hidden build actions. Help opens/closes without replacing drafts, restores keyboard focus, and parameter renaming preserves unsaved values while rewriting aliases. Desktop, narrow and Getting started screenshots were visually reviewed. The README screenshot is the current browser preview, not a native Fusion build.
- All 13 family defaults pass the pure validation core.
- Independent OpenCascade checks of eight default cylindrical, internal and rack preview outlines produced valid planar faces and extruded B-rep solids. This verifies those default section outlines, not Fusion's generated three-dimensional bodies.
- Python compilation, JavaScript syntax and macOS installer shell syntax passed.
- The publication review added six document tests for name editing and exact name recovery after failed updates. Dedicated gear names update together; Part roots and shared parents are preserved.
- GitHub Actions is configured for five Python/OS combinations, a Chromium interface check and a gated evaluation ZIP artifact. The Actions run is the source of truth for hosted-runner results; local tests do not establish cross-platform host acceptance.
- The release packaging checks required files and licenses, computes SHA-256 checksums and verifies the ZIP archive.

## Not run here

Autodesk Fusion is not installed in this environment. Native B-rep construction, command event ordering and undo behavior, actual parameter table interaction, downstream reference stability, and Windows/macOS installation must be checked in Fusion. The source tests use host substitutes at API boundaries and do not establish native compatibility.

Use [ACCEPTANCE.md](ACCEPTANCE.md) to record those results. Verify at least one creation, edit, parameter update, invalid-input rejection, cancellation, save/reopen and undo cycle before relying on the add-in in a working design. Each gear family has its own pending native geometry acceptance row.

The user's 2026-09-17 screenshot shows actual Fusion User Parameters with the
legacy `GS_...` names and default Spur values. This is evidence that those rows
exist in the user's design. It does not show the solid or establish editing,
undo, save/reopen or the installed build. The 0.2.0 rename operation, including
external references and Undo/Redo, still needs native confirmation.

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
