# Verification record

Release: Gear Studio 0.1.0

Date: 2026-09-16

Status: Evaluation build. Native Fusion acceptance is pending.

## Completed in the development environment

- **133 Python unittest checks passed.** They cover numeric and geometric validation, expression dimensions, bounded dependency resolution, persistence and independent templates, controller lifecycle, candidate cleanup, document update and rollback logic, and selected upstream mathematical invariants.
- **Chromium interface checks passed.** These exercise stale validation responses, invalid-input build guards, expression drafts, edit identity, cancellation, and the browser preview's refusal to claim native geometry creation. The bridge is a controlled test substitute for Fusion.
- **Visual review completed** for the desktop panel and a narrow panel. Both fit their viewport without horizontal document overflow. Desktop panels scroll while build controls remain visible. The included screenshot shows the interface preview and its checked default spur profile.
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
