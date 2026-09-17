# Gear Studio interface conventions

Gear Studio 0.2.0 adopts the visual language of Griffin's Laser Parameter Wizard.
The reference is the repository's `main` tree `9fd15815bbb5735d0dbd97feba3a1854d9ae049a`,
read on 2026-09-17 through GitHub:

- [Shared MADE tokens](https://github.com/tensegrity-audio/LaserCutterParameterWizard/blob/9fd15815bbb5735d0dbd97feba3a1854d9ae049a/packages/made-ui/tokens.css)
- [Application styling](https://github.com/tensegrity-audio/LaserCutterParameterWizard/blob/9fd15815bbb5735d0dbd97feba3a1854d9ae049a/apps/laser-test-grid/src/styles.css)

`GearStudio/ui/tokens.css` contains the shared color, type and radius values as a
local snapshot. It is loaded before `style.css`; no network request, package
manager, remote font or React runtime is required inside Fusion.

| Element | Convention |
| --- | --- |
| Main surfaces | Dark olive paper `#171914`, panels `#20231c`, recessed inputs `#11130e` |
| Text | Warm white `#f0f0e7`, secondary text `#a6aa99` |
| Primary action / selection | Lime `#d9ff48` with dark text |
| Warnings / errors | Orange `#ff8b3d` / coral `#ff716b`, accompanied by text |
| Corners | Shared 2 px radius |
| Typography | System sans-serif stack; monospaced values and compact section labels |
| Structure | Compact header, gear library, configuration and inspection; persistent bottom action bar |
| Parameter groups | Bordered sections with stable two-column inputs, advanced inputs disclosed on demand |
| Narrow panels | Horizontally scrollable family picker, stacked content, visible action bar |

The gear workflow remains one workspace. Choosing a family or opening Getting
started preserves the current draft. A parameter rename rewrites referenced names
in unsaved family drafts without replacing the entered values. Creation and
updating remain deliberate actions. A browser preview cannot create solids.

## Naming and help

New Fusion parameter names put the purpose first and a short gear number last:
`Module_G1`, `Teeth_G1`, `Bore_G1`. The mapping is saved with the gear; changing its
display name does not rename parameters. A selected legacy gear exposes **Shorten
parameter names**, which is an explicit native command with recovery. Existing
names remain supported. Hovering a field of a loaded gear shows its exact native
parameter name.

The panel's **Getting started** dialog explains the first gear, editing, parameter
updates, installation, and create/save/export. Installed version and actual code
folder appear there for update troubleshooting. They do not crowd the working
header. The bundled `START_HERE.html` guide works as a local file before the add-in
is installed; `docs/INSTALL.md` remains the full reference.

## Maintenance and verification

Keep base colors in the token file. Keep Fusion-specific layout and behavior in
the local CSS and JavaScript. The offline setup page is self-contained and uses
the same values; update it alongside the palette if the shared theme changes.
Use semantic buttons, labels, dialogs and disclosure elements. Focus indicators,
text status and reduced-motion behavior are required.

Browser checks exercise narrow layouts, persistent build controls, help/draft
preservation, rename messaging and the existing validation/connection guards.
Screenshots are browser previews, not proof of a native Fusion build. Native
selection, parameter rename, undo and installation remain in the acceptance
checklist.
