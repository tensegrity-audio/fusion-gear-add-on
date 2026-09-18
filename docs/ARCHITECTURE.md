# Gear Studio architecture

Gear Studio separates expression validation and isolated native preflight from target construction. Version 0.3.0 creates ordinary Fusion sketches and features inside a movable gear component. The component owns the saved definition and short named parameters. New gears require Hybrid design intent; older releases without intents use a normal history-enabled Design. Existing Base Feature records keep their legacy update path. No Custom Features preview API is used.

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
| `GearStudio/fusion/builder.py` | Shared native construction, isolated preflight, solid and tooth-space verification |
| `GearStudio/fusion/history.py` | Native history commits, component ownership, dependency checks and update staging |
| `GearStudio/vendor/study_gears/` | Adapted MIT geometry algorithms with bounded numerical work |
| `tests/` | Host-independent checks; host substitutes are not Fusion kernel certification |
| `tools/package.py` | Standard-library release packaging and checksums |

## Palette connection

The native palette opens `index.html?host=fusion`. Its incoming HTML handler is
registered before the palette becomes visible. JavaScript waits up to 15 seconds
for the injected `adsk.fusionSendData` bridge and a `state` reply to its `ready`
request. Missing or lost startup messages trigger only another read-only `ready`
request, at 500 ms intervals. Creation stays disabled until that handshake and
input validation succeed. On timeout, polling stops and a visible Retry
connection action starts another bounded attempt.

Ready replies carry the request ID. Late duplicate startup replies are ignored
after connection so they cannot reset a draft or active build. Build, update and
other mutating actions are never replayed by the connection loop.

The explicit browser preview (`?preview=1`) uses `gearStudioPreview.send`, not a
fake `adsk` object. A native session takes precedence over that flag. The native
page never loads sample preview data or falls back to preview because Fusion is
slow to inject its bridge.

Fusion can emit a `response` event when `sendInfoToHTML` completes. The handler
ignores this acknowledgement before JSON decoding or application dispatch.
Treating it as an unknown command would report an error back to HTML, producing
another acknowledgement. See [Autodesk's palette sample](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/PaletteSample_Sample.htm).

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
3. On an explicit build/update request, the builder prepares the complete native construction in a disposable Fusion document. The same construction routine is used in preflight and in the target command.
4. Cylindrical tooth spaces use a solid cutter, a circular **body** pattern, and a Boolean cut. Herringbones add native Move, Mirror and Combine features. Rings, bores and crown backing webs use native sketches, Extrude and Combine features. Cutter count is checked before subtraction. Solid checks include connectedness, volume and face count; cylindrical gears also compare material/air samples across up to twelve pitches at three axial sections to reject incomplete tooth patterns.
5. A detached copy of the checked result survives closing the temporary document. The original design is restored, and the controller rechecks document identity, saved definitions and input expressions.
6. Inside the commit command, new gears create a stable outer component with one tagged Construction child. The shared constructor is replayed in that child. It retains actual sketches and features, labels cylindrical steps, enables sketch visibility and creates an expanded timeline group. The root component is activated so those sketches can be seen from the normal Design workspace.
7. Updates stage a new Construction child in the existing outer component. Only after a successful build and health check is the old generated child deleted. Outer occurrence placement and parameter names are preserved. All external features, sketches, datums, joints and occurrences are checked for new errors or cascaded deletion. A failure raises to the controller, which MUST set `executeFailed = True` so Fusion aborts the entire command transaction. Manual edits within Construction are replaced by an update.
8. Legacy Base Feature gears use the previous detached-body update and explicit restoration path. Duplication creates independent native construction; it is not an automatic in-place migration of face references.
9. Only a successful commit updates remembered settings. Native commits have a 150-second cooperative budget and do not pump events during the command transaction. Preflight remains cancellable between operations. A single synchronous Autodesk kernel call cannot be forcibly interrupted by Python.

Native construction is replayed, so successful creation incurs two builds. This cost is explicit: preflight protects the target, and the second build retains ordinary native history. Exact kernel behavior, native rollback, Undo/Redo and downstream references require desktop Fusion acceptance. `CommandEventArgs.executeFailed` is Autodesk's documented transaction-abort mechanism, not a body-copy substitute.

Startup registers command definitions once, then idempotently reconciles promoted controls after startup completion, document activation and workspace activation. Event handlers are removed on stop. Startup loading does not force a palette open. The first `ready` nudges the native palette width by one pixel; after two animation frames, HTML sends `layoutReady` and the host restores the size. This one-time handshake does not replay geometry or reset draft state. SVG 16/32 icons support native high-DPI rendering.

## Parameter updates and identity

The outer component's `GearStudio` / `definition` attribute (or the BaseFeature attribute for legacy gears) stores the gear definition, parameter mapping and previously built evaluated values. Component ownership or the legacy source feature provides the body relationship without relying on tooth-face identifiers. New parameter names use a purpose-first label and a short document-local number, such as `Module_G1` and `Teeth_G1`. Allocation reserves suffixes found in all native parameters and saved managed mappings, including missing rows. The UUID remains the gear's internal identity; its display name and G-number are separate. Expressions remain expressions through edits and updates.

Legacy `GS_<id>_<field>` maps remain readable without migration. **Shorten parameter names** uses the native commit command without preparing geometry. It renames existing parameter objects, checks dependent expression rewrites, rewrites affected saved Gear Studio definitions, and preserves each gear's last-applied values so pending table changes are not falsely marked as built. Failure restores names, expressions and exact metadata snapshots. Native rename/undo behavior still needs Fusion acceptance. The front end rewrites aliases in unsaved family drafts while preserving the drafts themselves.

**Update from Parameters** uses current table expressions, including referenced parameters, as the source of truth. Selection refresh and the edit/update paths check for changed inputs. Dependents that are separate generated gears need their own explicit updates.

From 0.3.2, `_native_cylinder` uses a local-origin coincidence plus a driving diameter, never a Fix constraint on the circle. Target shaft bores bind the dimension's model-parameter expression to the saved `bore` alias. Scratch preflight uses the same diameter as an explicit cm literal because the disposable document does not own those aliases. Ring blanks and backing webs receive constrained numeric diameters. Cylindrical calculated tooth curves and remaining free sketch points are fixed only after deferred computation ends; the shaft line is construction geometry with fixed endpoints. Pitch references have a centered, numeric driving diameter. These calculated snapshots regenerate on explicit Update; they are not an automatically recomputing tooth model. The new helpers require the affected sketches to report `isFullyConstrained`, otherwise construction fails within the existing cleanup/abort boundary.

An existing nonzero shaft bore is the limited live-parameter exception: Fusion recomputes it on parameter-table edits even without the add-in. Such edits occur outside Gear Studio's validation/transaction boundary. The panel remains the path for validating before geometry mutation, adding/removing a bore and coordinated size changes. A pending live bore edit still leaves the stored applied definition stale until explicit Update. Before changing user inputs during a native update, `_freeze_previous_diameters` restores only tagged bore dimensions in the old generated subtree to their last-applied literal sizes. This prevents a bore valid for the new larger gear from breaking the old smaller gear during staging. The new subtree binds the same aliases afresh; failure must abort the native command, including restoring detached expressions. External sketches are never detached. Old untagged gears upgrade by ordinary regeneration.

The resolver checks pending expression changes against the parameter dependency graph to detect cycles and evaluate changes coherently. Changes that occur during candidate construction invalidate the pending commit. Missing or renamed generated parameters and duplicate copied identities are rejected with guidance.

The component identity and placement are the stable assembly handles. Body updates can change individual faces and edges. New gears retain editable sketches and construction features. Gear Studio does not promise permanent generated-body, face or edge identity across regeneration. Keep assembly references on the outer component's datums. It does not silently replace a failed update with a disconnected new component.

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
