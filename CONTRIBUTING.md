# Contributing to Gear Studio

Start with the [architecture](docs/ARCHITECTURE.md), [roadmap](docs/ROADMAP.md) and [verification record](docs/VERIFICATION.md). Gear Studio is an evaluation implementation with desktop Fusion acceptance still pending. Improvements should make the existing generation and editing lifecycle dependable before expanding its advertised scope.

## Development setup

The default checkout location is **Documents/FusionAddins/fusion-gear-add-on**. On Windows, use the [Documents-aware Git commands](docs/INSTALL.md#windows-git-alternative); on macOS, use the [macOS setup](docs/INSTALL.md#macos). Keep future user-facing installation examples consistent with this location. Avoid bare clone commands that depend on the terminal starting in a writable folder.

From that repository directory:

```sh
python -m unittest discover -s tests -v
python tools/package.py --check
```

Use Python 3.10 or newer for local source checks. Core code and packaging use the standard library. The `adsk` API is supplied by Fusion; installing an unrelated Python package named `adsk` is not a substitute for testing in the host.

For the interface suite, use Node.js and the locked development dependencies:

```sh
npm ci
npx playwright install chromium
npm run check:ui
npm run test:ui
```

On a Linux development machine, Playwright may also require its documented browser system dependencies. `PLAYWRIGHT_CHROMIUM_EXECUTABLE` can point the test at an existing compatible Chromium executable. The Fusion add-in does not need Node, npm, Playwright or any network-installed dependency.

Use the [installation guide](docs/INSTALL.md) to install the inner `GearStudio` folder. Close Fusion before replacing installed files. If you install a copy, rerun the installer after changes; if you register the checkout directly, remember that Fusion loads its current files.

## Make a focused change

1. Create a branch and keep one user-visible problem per pull request where practical.
2. Add a regression test for a real failure or numerical invariant when the change affects calculations, persistence, dependency handling or recovery.
3. Run the relevant source and interface checks. For native modeling or lifecycle changes, execute the corresponding [Fusion acceptance cases](docs/ACCEPTANCE.md) and record the actual host results.
4. Update affected user instructions, known limitations and the changelog. Describe unrun checks as unrun.
5. Explain the problem, resulting behavior, validation evidence and remaining limitations in the pull request.

Preserve these requirements:

- Native B-rep output, explicit unit conventions and real expression-based parameter inputs.
- No expensive geometry work while typing. Validation and cancellation remain bounded; previous successful geometry must stay recoverable.
- No silent clamping, accidental parameter-reference loss or unimplemented Generate actions.
- Stored gear identities, independent template semantics and saved preferences remain compatible, or receive an explicit schema migration.
- Original and upstream license notices remain intact. Describe changes to vendored geometry in its `UPSTREAM.md`; do not silently replace the pinned source.

Do not add caches, local logs, generated distributions, credentials or private Fusion designs to source control. Packaging is reproducible with `python tools/package.py`; build output belongs in artifacts, not source commits.

## Report a useful bug

Open a [repository issue](https://github.com/tensegrity-audio/fusion-gear-add-on/issues) containing:

- Repository commit or package version, Fusion version/build and OS.
- Gear type and exact parameter expressions, including units and referenced parameter values.
- Whether the action was Create, Edit, Duplicate or Update from Parameters.
- Minimal steps, expected outcome and actual outcome, including the error message and whether Undo/recovery worked.
- A screenshot or minimal shareable design when needed, with unrelated private content removed.

For a slow build, include the elapsed time and the last progress message. For a geometry error, include a measurement or contact/clearance observation rather than only stating that the gear looks wrong. Relevant log excerpts can help; review them before sharing.

A passing browser test, host substitute or independent solid-kernel experiment must not be reported as a passing native Fusion test. Use [docs/ACCEPTANCE.md](docs/ACCEPTANCE.md) to separate those outcomes.
