# Changelog

Changes describe source capabilities. Native Fusion verification is tracked separately in [docs/VERIFICATION.md](docs/VERIFICATION.md).

## 0.3.2 constrained sketches and a parameter-driven bore - 2026-09-18

- Bore sketches now have a local-origin coincidence and a driving diameter linked to the gear's saved bore parameter, such as `Bore_G1`. Ring/web circles receive centered driving dimensions too. Native circle/affected cylindrical sketch checks reject unresolved sketch freedom before committing.
- Cylindrical calculated tooth profiles lock remaining points as well as curves. The shaft reference line is construction geometry with fixed endpoints; the pitch circle uses a centered driving diameter without a redundant Fix constraint. These calculated references and tooth profiles regenerate through Update gear.
- Keep the outer component freely movable while its generated children and sketches stay rigid in local coordinates. Existing native-history gears receive the constraints on their next Update gear, preserving component placement.
- Direct bore-parameter edits now invoke Fusion's native solver immediately. Documented the limited live-bore behavior, explicit full-gear Update requirement, and the panel path for validation before mutation or adding/removing a bore. Before staged updates, detach only tagged old bore dimensions to their last-applied sizes within the abortable native command, so a larger new bore does not invalidate the old smaller gear.
- Added constraint, unit, alias-forwarding, placement and update-order regression checks. The user reports successful herringbone generation; native verification of the new constraints and live diameter remains pending.

## 0.3.1 Fusion entry-point version import - 2026-09-18

- Fixed startup failing with `ImportError: cannot import name '__version__'`. Fusion loads `GearStudio.py` as a generated package and does not run the root `__init__.py`. The controller now imports release metadata from an explicit `version.py` module; the standard package re-exports the same value.
- Added a loader regression that reproduces the reported encoded Windows module name without running the package initializer. It failed with the original traceback before the fix and now imports the controller and exercises entry-point run/stop delegation. Added release-version consistency checks and made the version module required in packages.
- Added instructions for the reported installation path outside Documents, including removing the old Fusion link and linking the intended Documents copy. Native geometry acceptance from 0.3.0 remains pending.

## 0.3.0 construction history, tooth patterns and startup - 2026-09-17

- Replaced cylindrical loft-cut feature patterns with solid cutter-body patterns and a combined subtraction. Added cutter-count and bounded tooth-space checks to reject a mostly cylindrical result. Native confirmation of the reported helical/herringbone defect is still required.
- New gears retain real sketches, Extrude/Loft/Pattern/Mirror/Combine operations and expanded named timeline groups. All families use the shared native constructor in preflight and target commits. Movable outer components own the generated construction, with visible sketches in the normal Design workspace. New creation requires Hybrid design intent.
- Updates preserve the outer component and its placement, stage a replacement Construction child, and abort the native transaction if external features, sketches, datums or joints break or disappear. Manual edits inside generated Construction are replaced. Legacy Base Feature gears remain editable; Duplicate creates independent history.
- Reconcile toolbar controls after Fusion startup, document activation and workspace activation; remove lifecycle handlers on stop. Avoid opening the palette automatically during startup loading.
- Added a bounded, two-message first-layout resize and native SVG toolbar icons. Browser and API-boundary tests do not certify Qt first-paint behavior or display scaling inside Fusion.
- Expanded beginner setup and editing instructions, including moving Components, regenerating old gears, preserving user additions and checking the loaded version/path after a complete Fusion restart.

## 0.2.0 readable parameters, shared interface and beginner setup - 2026-09-17

- New gears use purpose-first parameters such as `Module_G1`, `Teeth_G1`, `FaceWidth_G1` and `Bore_G1`. Suffix allocation checks the design's existing parameters and saved mappings. Names remain stable across gear display-name edits.
- Added **Shorten parameter names** for selected legacy gears. It renames existing native parameter objects, updates affected saved expressions, preserves pending parameter-table edits and restores previous names/definitions if the operation fails. Legacy names remain supported without an automatic migration. Native rename/Undo verification is pending.
- Adopted the Laser Parameter Wizard's shared MADE colors, typography and 2 px corners, with compact headers, bordered groups, lime selection states and stable bottom actions. All assets remain local to Fusion.
- Added a **Getting started** dialog with first-gear and editing guidance plus the actual loaded version and folder. Field tooltips expose actual parameter names; renaming preserves unsaved drafts.
- Added the offline **START_HERE.html** guide and expanded installation documentation with one ZIP-to-Documents route, folder checks, checkpoints, create/save/export distinctions and explicit parameter editing. Packaged releases include the guide and design tokens.
- Added nine Python regression checks and browser checks for alias upgrades, help/draft preservation, keyboard focus and five viewport sizes. Updated the interface screenshot and acceptance checklist.

## 0.1.3 parameter commit fix - 2026-09-16

- Move user-parameter creation, expression updates and value verification before `BaseFeature.startEdit()`. Editing a Base Feature uses a direct-modeling context; writing parameters there was the likely cause of the reported `3 : this is not a parametric design` commit failure even with design history enabled.
- Preserve the design's history setting and keep parameter recovery outside source-feature editing. A parameter failure prevents any source-body replacement.
- Include the failing commit stage in native error messages and preserve chained native tracebacks in `GearStudio.log`.
- Strengthen document tests to reject parameter writes during source-feature editing, and add coverage for partial parameter creation, rejected edit entry, native-error context and logging. Native confirmation of this fix remains pending.

## 0.1.2 palette connection fix - 2026-09-16

- Fixed the native panel entering interface-preview mode when Fusion's asynchronous bridge was not ready during page load. Preview is now explicit (`?preview=1`) and uses its own transport without creating or replacing `window.adsk`.
- Added a bounded native handshake, a visible Retry connection action, and correlated startup replies. Only the read-only handshake retries; builds are never automatically replayed and late startup replies cannot reset a build.
- Ignore Fusion's `response` acknowledgement before parsing request JSON, preventing the unsupported-action/error feedback loop. Unknown user actions now include their action name in diagnostics.
- Register the incoming handler before showing the native palette, and mark its URL as a Fusion session.
- Added regression checks for acknowledgements, invalid-message feedback, delayed bridge injection, lost ready messages, connection timeout/retry, preview isolation and Create gear message delivery. Native B-rep creation still requires confirmation in Fusion.

## Installation guide clarification - 2026-09-16

- Made Documents/FusionAddins/fusion-gear-add-on the default repository location and direct Fusion folder linking the recommended installation route.
- Added step-by-step ZIP instructions, Documents-aware Windows Git commands, migration from Downloads or the user-profile root, update/rollback instructions, and current/older Fusion dialog guidance.
- Documented the reported System32 permissions problem, hidden file extensions, missing PowerShell menu actions, failed clones and stale duplicate add-in copies. Existing installer scripts remain optional alternatives using Fusion's default AddIns directory.

## 0.1.1 startup compatibility fix - 2026-09-16

- Replaced dotted toolbar command and palette identifiers with ASCII letters, digits and underscores after a Windows user reported `RuntimeError: 3 : invalid id` in `addButtonDefinition` during startup.
- Added a startup/shutdown regression check covering both command registrations, toolbar attachment, palette creation, reopening and cleanup through an API substitute that rejects dotted identifiers.
- Recorded the native startup failure and documented how to replace the exact copy Fusion loads. Existing gear definitions, named parameters and local preferences retain their identities.
- Native confirmation of this correction remains pending; passing source tests does not establish Fusion startup or geometry compatibility.

## Repository publication - 2026-09-16

- Prepared the repository for GitHub distribution with clone, Code ZIP and packaged-artifact installation instructions.
- Added the source-backed alternatives review, implementation roadmap and contribution guide.
- Added locked interface-test dependencies, cross-platform GitHub Actions checks and a gated evaluation package artifact.
- Removed a Python 3.12-only typing dependency found by the Python 3.10 CI job; the geometry code retains standard-library-only runtime support.
- Fixed gear name edits to update managed Fusion body and timeline names, plus dedicated component names, with exact name restoration on failed updates. Part roots and shared parents keep their names.

## 0.1.0 evaluation implementation - 2026-09-11

- Added 13 individual gear variants using native Fusion B-rep construction paths: external/internal spur, helical and herringbone; straight/helical rack; worm and worm wheel; straight/spiral bevel; crown/face.
- Added a local responsive panel with expression inputs, bounded validation and lightweight engineering previews.
- Added editable saved definitions, unique Fusion user parameters and explicit **Update from Parameters** regeneration.
- Added independent duplication, per-family successful defaults, named presets and atomic local settings.
- Added isolated candidate preparation, cooperative cancellation, work budgets, source-body update and commit recovery paths.
- Added Windows/macOS installers, deterministic ZIP packaging, upstream license/provenance notices, source tests and a live Fusion acceptance checklist.

Known boundaries: native Fusion acceptance is pending; changing user parameters does not automatically regenerate solids; a native kernel call cannot be forcibly interrupted; complete mating-pair solving and certified geometric accuracy are not included.
