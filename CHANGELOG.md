# Changelog

Changes describe source capabilities. Native Fusion verification is tracked separately in [docs/VERIFICATION.md](docs/VERIFICATION.md).

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
