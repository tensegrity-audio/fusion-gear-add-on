# Gear Studio implementation contract

Product: an Autodesk Fusion desktop add-in named `GearStudio`, displayed as Gear Studio. No third-party Python dependencies at runtime. Outputs real B-rep solids. Never use Fusion preview CustomFeatures API. Installation is a folder named GearStudio containing GearStudio.py and GearStudio.manifest.

## Shared data

Gear definition (JSON compatible):
`{"schema_version":1,"id":"uuid", "name":"Drive gear", "kind":"spur", "parameters":{"module":"1 mm","teeth":"24"}, "placement":{}}`

`id` absent for a new gear. Parameters are expressions, retained exactly. Lengths resolve to millimetres; angles resolve to degrees; counts and coefficients are unitless. Core validation and geometry receive a separate `values` dictionary of evaluated floats. No `adsk` imports in core.

Candidate families: spur, helical, herringbone, internal_spur, internal_helical, internal_herringbone, rack, helical_rack, worm, worm_wheel, bevel, spiral_bevel, crown. Family availability must honestly match builder implementation. Do not expose unimplemented Generate controls.

Common parameter keys: module, teeth, width, pressure_angle, backlash, profile_shift, addendum, dedendum, root_fillet, bore, helix_angle, outside_diameter, rack_height, worm_diameter, worm_starts, mate_teeth, shaft_angle, spiral_angle. Additional family keys allowed if synchronized. Backlash is this gear's tooth-thickness reduction at its reference section in mm, not total pair clearance. Root fillet is a module coefficient. Gear pair generation is not required for first build but every individual family must document pairing requirements. All families must support edit and saved defaults.

## Core contract (geometry agent owns)

`core/catalog.py`: `catalog()` -> JSON serializable dict `{families:[{id,label,description,fields:[key,...],...}], fields:{key:{label,unit,default,description,...}}}`; `default_spec(kind='spur')` -> fresh definition with default parameter expressions.

`core/validation.py`: `validate(spec, values)` -> `{valid:bool,issues:[{field,code,severity:'error'|'warning',message}],metrics:{...},cost:{...}}`. Never mutate inputs. Bound numeric complexity; reject invalid numeric types and nonfinite numbers. Pure cheap preflight.

`core/profiles.py`: `preview(spec, values)` -> JSON `{paths:[{points:[[x,y],...],closed:true,role:'outline'|'construction'...}],bounds:[xmin,ymin,xmax,ymax],...}` in mm. Lightweight bounded 2D engineering preview; no triangle mesh. Backend catches preview errors. Label simplified previews honestly. Geometry helpers and tests owned by geometry agent.

## Native geometry contract (Fusion builder agent owns)

`fusion/builder.py`: `SUPPORTED_KINDS` set. `build_candidate(spec, values, progress=None, cancelled=None)` -> object exposing `.body` (one detached temporary adsk.fusion.BRepBody, millimetres converted to cm), `.cleanup()` callable. A contextmanager or Candidate dataclass is fine. Build candidate in disposable scratch Fusion document or staging, preserve/restore active document. Must clean up on failure and honor cancel callbacks between bounded operations. No changes to existing target or parameters. Target solid should include requested bore and ring/rack body. Use proven MIT study-gears algorithms where feasible, retaining complete licensing. Coordinate origin Z shaft axis, XY axial section; document other families orientation. Return B-rep, no mesh output. Do not implement metadata or target commit; root owns those.

## Persistence contract (persistence agent owns)

`core/storage.py`: `SettingsStore(path=None)`; `load()` -> state dict; `last_spec(kind)` -> definition or None; `remember_success(spec)`; `list_presets()` -> [{id,name,spec,updated_at}]; `save_preset(name,spec)` -> item; `delete_preset(id)`. Atomic JSON, schema version, size limits, tolerate corruption with backup and informative status. User prefs outside add-in folder. Must preserve expressions and copy objects. Per-document/per-gear definitions are in Fusion attributes managed by root. Presets saved explicitly may be validated before save. Last used defaults only successful builds.

## UI contract (UI agent owns)

Plain local HTML/CSS/JS under ui/, no network fonts/dependencies. Professional dark neutral engineering panel with restrained warm accent, three regions when wide, responsive narrow palette. Not a website, no Sites hosting. In-app actions use `adsk.fusionSendData(action, JSON.stringify({requestId,...payload}))`. Incoming Python events through `window.fusionJavaScriptHandler.handle(action,jsonString)`, return 'OK'. Local browser demo bridge with same data shapes permitted, clearly identified as interface preview.

Actions:
`ready`; `validate` `{spec}`; `build` `{spec}`; `editSelected`; `duplicateSelected`; `updateSelected`; `loadLast` `{kind}`; `savePreset` `{name,spec}`; `loadPreset` `{id}`; `deletePreset` `{id}`; `cancel`; `openParameters`; `refreshSelection`.

Events:
`state` `{catalog,spec,presets,selection:{id,name}|null,mode:'create'|'edit',supportedKinds,host:'fusion'|'preview'}`
`validation` `{requestId,valid,issues,metrics,cost,preview}`
`progress` `{message,percent,cancellable}`
`result` `{ok,message,spec?,presets?,mode?}`
`error` `{message,details?,requestId?}`
`selection` `{id,name}|null`.

Persist local draft form state across family switching; only backend last-used defaults update on successful builds. UI never fires expensive build on typing. Debounced validate. Ignore stale request IDs. Do not silently clamp expressions or values. Disable build while invalid or running. Submit ordinary editable text expression controls with unit suffixes. Successful result updates editing identity. User can explicitly New (client reset id) or duplicate selected. Current selected gear's expression inputs win over defaults when editing. No misleading claims of live automatic geometry rebuild: named parameters update on Update Gear. App header can say B-rep solids; keep API details out of user flows.

## Root responsibilities

Fusion entry point, commands, HTML palette bridge, expression evaluation, selection resolution, persistent per-gear attributes, namespaced user parameters, safe commit/update through BaseFeature.updateBody, transaction/recovery behavior, packaging, docs, integration and QA.

Must preserve parameter expression references on rebuild. A managed source body inside BaseFeature is updated in place with candidate temporary body; component identity and placement remain. No automatic destructive replacements. Prefer component selection and shaft datums for references; tooth-face references may change. Explicit Update from Parameters performs validation first. Parameter table rows are real inputs to update, not decorative records. Add-in should detect staleness on explicit refresh and before update. Unsupported design modes or selections must fail fast with actionable guidance.
