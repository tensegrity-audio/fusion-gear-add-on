# Gear Studio architecture

Gear Studio separates expressions and preflight checks from expensive native geometry. Each gear has a managed B-rep source body and BaseFeature, a persisted gear definition and real named user parameters. Hybrid designs receive a component for each new gear; Part designs use the root component. Pure Assembly intent is rejected with guidance to use a modelable Part or Hybrid design. The stable API path uses `BaseFeature.updateBody` for explicit updates; no preview Custom Features API is required.

## Modules

| Path | Responsibility |
| --- | --- |
| `GearStudio/GearStudio.py` | Fusion `run` / `stop` entry point and add-in lifetime |
| `GearStudio/GearStudio.manifest` | Add-in identity and Fusion loading metadata |
| `GearStudio/ui/` | Local HTML, CSS and JavaScript palette; no CDN, remote fonts or framework runtime |
| `GearStudio/core/catalog.py` | Gear families, fields, units, defaults and pairing notes |
| `GearStudio/core/validation.py` | Pure bounded dimensional and complexity preflight |
| `GearStudio/core/profiles.py` | Bounded 2D engineering previews in millimeters |
| `GearStudio/core/expressions.py` | Pure expression dependency helpers |
| `GearStudio/core/templates.py` | Independent template expressions for duplicate, preset and last-used settings |
| `GearStudio/core/storage.py` | Atomic preferences, successful defaults, presets and corruption recovery |
| `GearStudio/fusion/controller.py` | Palette protocol, validation, preparation, cancellation and commit command |
| `GearStudio/fusion/document.py` | Fusion expression resolution, parameters, BaseFeature attributes, selection, identity, commit and recovery |
| `GearStudio/fusion/builder.py` | Isolated native candidate preparation and solid verification |
| `GearStudio/vendor/study_gears/` | Adapted MIT geometry algorithms with bounded numerical work |
| `tests/` | Host-independent checks; host substitutes are not Fusion kernel certification |
| `tools/package.py` | Standard-library release packaging and checksums |

## Definition and units

Definitions are versioned JSON-compatible objects. They retain expression text separately from evaluated values:

```json
{
  "schema_version": 1,
  "id": "gear-uuid",
  "name": "Drive gear",
  "kind": "spur",
  "parameters": {
    "module": "1 mm",
    "teeth": "24"
  },
  "placement": {}
}
```

The abbreviated example omits the remaining required spur fields. The catalog supplies the complete field set for each family. Resolution produces millimeters, degrees and dimensionless counts/coefficients. Fusion's internal centimeters and radians are converted at the API boundary. Length and angle expressions are checked against expected units; counts must resolve to supported integers.

Current families use normal tooth-system inputs, except bevel module is defined at the outer normal section. Crown face width is radial. Backlash is stored under the historical key `backlash` and presented as **Tooth thinning**, a per-gear normal-section thickness reduction. Family-specific inputs not used by a native algorithm are excluded from the catalog.

## Build lifecycle

1. The palette sends an expression-only draft. Debounced validation does not modify the target design.
2. The bridge resolves expressions against Fusion parameters, checks dependency cycles and units, and calls pure preflight.
3. On an explicit build/update request, the native builder revalidates and prepares geometry in a disposable Fusion design.
4. Vendor numerical loops and feature boundaries check a cooperative work budget and cancellation. The builder copies the result into a detached temporary B-rep body and checks solidity, connectedness, volume and face count.
5. The temporary design is closed and the original document restored. The controller verifies that the source document, gear definition and resolved inputs have not changed during preparation.
6. A Fusion command commits the candidate, parameter expressions and persisted definition together. New gears receive independent identities and parameter names. Updates retain the existing component and managed source body.
7. Successful commits update last-used settings. Failed preparation does not touch the target. Commit failures attempt explicit restoration and report incomplete restoration instead of claiming success.

The commit command is intended to provide one native undo operation. Exact transaction behavior, undo/redo and the downstream effects of `updateBody` require the live-host acceptance checks. Native kernel calls are synchronous; cooperative deadlines cannot forcibly interrupt a single Autodesk modeling operation.

## Parameter updates and identity

The managed BaseFeature's `GearStudio` / `definition` attribute stores the gear definition, parameter mapping and previously built evaluated values. The owning feature provides the body relationship without relying on tooth-face identifiers. Parameter names are generated with a `GS_` prefix and a gear-specific identifier. Expressions remain expressions through edits and updates.

**Update from Parameters** uses current table expressions, including referenced parameters, as the source of truth. Merely changing a user parameter does not recompute the solid. Selection refresh and the edit/update paths check for changed inputs. Dependents that are separate generated gears need their own explicit updates.

The resolver checks pending expression changes against the parameter dependency graph to detect cycles and evaluate changes coherently. Changes that occur during candidate construction invalidate the pending commit. Missing or renamed generated parameters and duplicate copied identities are rejected with guidance.

The component identity and placement are the stable assembly handles. Body updates can change individual faces and edges. Gear Studio does not promise permanent tooth-face reference identity or an editable timeline feature for every tooth-construction step. It does not silently replace a failed update with a disconnected new component.

## Coordinate conventions

| Family | Builder coordinates |
| --- | --- |
| Spur, helical, herringbone, internal gears, worm wheel | Shaft on Z; body centered on the XY plane |
| Worm | Shaft on Z; width extends from Z = 0 |
| Straight and spiral bevel | Shaft on Z; common pitch-cone apex at the origin |
| Straight and helical rack | Length in +X; teeth in +Y; face width in Z; reference line at Y = 0 |
| Crown / face | Shaft on Z; reference tooth plane at Z = 0 |

The panel creates one gear at a time. Complete pair placement, internal interference, assembly access, contact behavior and manufacturing suitability remain separate checks.

## Persistence and local data

Settings are stored outside the install directory using versioned, size-limited JSON. Writes use a temporary file in the same directory followed by atomic replacement. Corrupt originals are retained when backup succeeds. A failure to back up blocks overwriting rather than discarding the original settings. Presets are capped and copied when returned to callers.

Successful defaults omit the source gear's document identity so they can seed independent gears. Duplicate, preset and last-used templates expand references to source-owned generated aliases while retaining external parameter references, avoiding accidental dependence on the original gear's aliases. Named presets are explicitly saved. Per-gear definitions remain in saved Fusion documents. No runtime network requests or telemetry are implemented.

## Geometry accuracy boundary

The native output is a B-rep solid. Sampled fitted splines approximate mathematical tooth curves, lofts approximate helical surfaces, and generating-tool envelopes for worm wheels and crowns are finitely sampled. The transverse root tool-radius treatment uses a circular approximation. The code does not certify maximum profile error, contact behavior, strength or an ISO/AGMA quality grade. See `GearStudio/vendor/study_gears/UPSTREAM.md` for the precise upstream revisions, local changes and algorithm notes.

## Extension policy

Adding another family requires a synchronized catalog definition, numerical preflight, bounded native builder implementation, preview behavior, pairing notes, source tests and live Fusion creation/update acceptance cases. The palette filters against the native builder's supported kinds. Unsupported geometry must not expose a working Generate action.

Geometry provenance and upstream licensing live beside the vendored files. The full upstream MIT license must remain in every source and installed distribution. Original Gear Studio integration code is covered by the repository `LICENSE`.
