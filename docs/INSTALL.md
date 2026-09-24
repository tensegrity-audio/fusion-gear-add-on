# Install Gear Studio

**Recommended location: `Documents\FusionAddins\fusion-gear-add-on`.** Keep the files there and tell Fusion where to find the inner `GearStudio` folder. This is the default for our installation instructions and future setup examples.

For first-time Windows users, follow **Windows: download and install** below. You need Autodesk Fusion desktop and a ZIP download. Git, PowerShell installers, a separate Python installation and administrator access are not required for this route.

After extracting the ZIP, you can double-click **START_HERE.html** to read a formatted setup guide in your browser. It opens as a normal local file and needs no server. Follow one installation route from start to finish; the Git and legacy-installer sections are alternatives.

| Term | What it means here |
| --- | --- |
| Project folder | The outer `fusion-gear-add-on` folder with the documentation and code |
| Add-in folder | The inner `GearStudio` folder that you select in Fusion |
| Add-in | A tool that stays loaded in Fusion to provide the panel and editing commands |
| Script | A task that runs and finishes; Gear Studio is registered as an add-in |
| Installer (`.ps1` / `.command`) | Optional file-copy helpers for a different installation layout; not part of the recommended route |

Already have a copy in Downloads or directly inside your user folder? Follow [Move an existing installation into Documents](#move-an-existing-installation-into-documents).

- [Windows: download and install](#windows-download-and-install)
- [Windows: Git alternative](#windows-git-alternative)
- [Move an existing installation](#move-an-existing-installation-into-documents)
- [Update an installation](#update-an-installation)
- [macOS](#macos)
- [Optional legacy installers](#optional-legacy-installers)
- [Troubleshooting](#troubleshooting)

## Windows: download and install

### 1. Download and extract

1. Save your designs and close Fusion.
2. Open the [Gear Studio repository](https://github.com/tensegrity-audio/fusion-gear-add-on).
3. Click the green **Code** button, then **Download ZIP**.
4. In File Explorer, right-click the downloaded ZIP and choose **Extract All**, then **Extract**. Wait for extraction to finish. Work from the extracted folder, not the compressed ZIP.
5. Open the extracted folders until you can see `README.md`, `docs`, and a folder named `GearStudio` together. This is the repository folder. Windows can create an extra outer folder with the same name; use the one that actually contains those files.

**Checkpoint:** you are looking at ordinary extracted files, not browsing inside the ZIP. Double-click `START_HERE.html` if you would like to keep the instructions open beside Fusion.

### 2. Put the repository in Documents

1. Open **Documents** from File Explorer's sidebar. Use this Documents location even if Windows stores it under OneDrive or another redirected path.
2. Create a folder inside Documents named **FusionAddins**.
3. Move the repository folder identified above into **FusionAddins**.
4. Rename that repository folder from `fusion-gear-add-on-main` to **fusion-gear-add-on**.
5. Open its inner **GearStudio** folder and confirm that `GearStudio.py` and `GearStudio.manifest` are directly inside it.

Your final locations should be:

| What | Location within Documents |
| --- | --- |
| Entire repository, including instructions | `FusionAddins\fusion-gear-add-on` |
| Folder to select in Fusion | `FusionAddins\fusion-gear-add-on\GearStudio` |
| Python entry point | `FusionAddins\fusion-gear-add-on\GearStudio\GearStudio.py` |
| Add-in manifest | `FusionAddins\fusion-gear-add-on\GearStudio\GearStudio.manifest` |

A typical full path is `C:\Users\<your-name>\Documents\FusionAddins\fusion-gear-add-on\GearStudio`. The part before `FusionAddins` depends on your configured Documents location. Keep these files available locally if Documents is synchronized by a cloud service.

If the destination already exists, use [Update an installation](#update-an-installation) instead of merging two extracted folders. Keep the inner folder named exactly `GearStudio`.

**Checkpoint:** the selected folder ends in `fusion-gear-add-on\GearStudio`, and its contents include `GearStudio.py` and `GearStudio.manifest`. If file extensions are hidden, turn on **View > Show > File name extensions** in File Explorer.

### 3. Add the folder to Fusion

1. Start Fusion and open a new design in the **Design** workspace.
2. Open **Utilities > Add-Ins > Scripts and Add-Ins**. If the toolbar placement differs, search Fusion's commands for **Scripts and Add-Ins**.
3. Select **All scripts and add-ins** to clear any filters that could hide Gear Studio.
4. Click **+**, then **Script or add-in from device**. If you have the older dialog, select the **Add-Ins** tab and click its **+ / Add** button.
5. Browse through **Documents > FusionAddins > fusion-gear-add-on > GearStudio** and select that **GearStudio folder**. The outer repository folder, `.py` file and `.ps1` file are not the folder Fusion needs.
6. Select **GearStudio** in the list and click its **Run** icon or button.
7. Enable **Run on Startup** if you want it available whenever Fusion opens.

Fusion remembers the linked folder and loads its files in place. This is a supported installation method; leave the folder in Documents after adding it. See [Autodesk's folder-linking instructions](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/WritingDebugging_UM.htm).

### 4. Confirm it opened and prepare a design

The **Gear Studio** panel should open. Its **Gear Studio** toolbar command reopens the panel after you close it. At a normal panel width, the connection label changes to **Autodesk Fusion**. An **Interface preview** banner means you are not using the native creation flow. If an error appears, keep the entire message and see [Troubleshooting](#troubleshooting).

Click **Getting started** in the panel. The bottom of that guide shows the installed version and folder. This is the copy Fusion is actually running; use that location when updating or reporting a problem.

Use a **Hybrid** design with **Capture Design History** enabled. In Fusion's **File > New Design** options, choose the Hybrid design type when a type choice is offered. Part designs cannot contain the movable component structure used by new gears; Assembly-only designs do not permit this modeling. Gear Studio does not silently convert an existing design. Older Fusion releases without design types use a normal new Design.

Start with a new disposable design. Check that the timeline is visible at the bottom of Fusion. If history is disabled, right-click the top design component in Fusion's Browser and choose **Capture Design History**. Finish any active sketch, Base Feature edit or command before creating a gear. In older Fusion releases, a normal new Design is the appropriate starting point.

**Checkpoint:** the panel has loaded, a modelable design is active, and design history is enabled. Continue with the first-gear steps below. Native Fusion acceptance is still incomplete; the [verification record](VERIFICATION.md) distinguishes observed results from automated checks.

## First gear and subsequent edits

### Create your first solid

1. Choose **Spur** in the left gear list. Enter a name such as **Drive gear**.
2. Use **Module 1 mm**, **Teeth 24**, **Pressure angle 20 deg**, **Face width 8 mm**, **Bore 5 mm** and **Tooth thinning 0.05 mm**. In Advanced, the starter values are profile shift 0, addendum 1, dedendum 1.25 and root fillet 0.25. These explicit values also work when a previous session remembered different settings.
3. Wait for validation. If Create gear is disabled, read the highlighted fields and the status at the bottom.
4. Click **Create gear** once and wait for the result. Look for the new body in Fusion's canvas and Browser. It is inside a new named gear component. Expand its Construction branch to see the body and visible sketches, and expand the Gear Studio group in the timeline to see the operations. Use Fusion's Fit view and check body visibility if it is off-screen.
5. **Save the Fusion design.** This preserves the B-rep and its editable Gear Studio definition.

**Checkpoint:** there is a solid body in Fusion, and **Modify > Change Parameters** contains rows such as `Module_G1` and `Teeth_G1`. A 2D outline in the panel alone is only a preview. **Create gear** makes the solid; **Save** preserves the design; use Fusion's **Export** command separately when you need a format such as STEP. Keep the original Fusion design for future Gear Studio edits.

### Edit through the Gear Studio panel

1. Select the generated **body** in Fusion's canvas or Browser. The outer named component selects the whole gear, including its construction sketches.
2. Click the **refresh arrow** in the panel's selection box and confirm the gear's name appears.
3. Click **Edit**, change Teeth to **30**, wait for validation, then click **Update gear**. The existing body should change.

### Edit through Fusion's parameter table

1. Click **Parameters** at the bottom of Gear Studio, or open **Modify > Change Parameters**.
2. Find `Teeth_G1` under User Parameters and change it to **32**. Your gear may use G2 or another number if other parameters already exist. The Comments column identifies the gear.
3. Close the dialog, select the gear body and refresh the selection in Gear Studio.
4. Click **Update from Parameters** in the Fusion parameters box below the input fields. Wait for the update, then save the design.
5. Close and reopen the saved design; select the body, refresh selection and choose **Edit** to reload it.

New names put the setting first (`Bore_G1`, `FaceWidth_G1`) so they remain distinct in narrow columns. The number is reserved per design and stays stable when the gear is renamed. For existing `GS_...` names, select the gear, refresh selection and click **Shorten parameter names**. This upgrades native names and saved references without rebuilding the solid. Long names still work until you use the upgrade. Use this action instead of manually renaming managed rows.

The upgrade applies to the active Fusion design. External text files and presets that reference another gear's old names may need those expressions updated when reused. Presets already expand their source gear's own names into independent expressions. Use version 0.2.0 or later to edit a design with short parameter names; older add-in versions do not understand those saved mappings.

Both edit paths rebuild and validate the complete B-rep solid. In 0.3.2, an existing shaft bore also responds directly to its `Bore_G1` parameter through a centered, diameter-constrained sketch. Tooth profiles and the other generated operations still require **Update from Parameters**. Finish table edits with this action so the full definition is checked and saved.

For validation before geometry changes, use **Gear Studio > Edit > Update gear**. Fusion applies direct parameter-table edits immediately to the bore, before Gear Studio can check them. If an impossible diameter produces a failed feature, Undo the table edit or restore a valid diameter. Use the Gear Studio panel when adding/removing the bore (0 mm), or changing tooth size and bore size together.

## Circle build error and parameter help

If a build reports **"The generated diameter or center is still unconstrained"**, update to **0.3.3**. This is a 0.3.2 construction-check regression; reducing tooth count or changing the default dimensions is not the remedy. Save your designs, fully quit Fusion, update the exact folder shown in Scripts and Add-Ins, and restart. Open Gear Studio > Getting started and verify **0.3.3** and the intended Documents path. Test a default Spur in a new Hybrid design first. If it still fails, send the complete new message, Fusion version, gear family/settings and loaded add-in path.

Click an **i** button for parameter help; Enter/Space also opens it. Close or Escape returns to the input area without changing values. **Tooth settings**, **Advanced tooth geometry** and **Geometry measurements** are expandable. Invalid hidden fields open automatically, so a collapsed section cannot hide an input error.

## Move a gear with its sketches

1. Finish any active sketch or feature edit. Activate the top-level design using the radio button next to its name in the Browser.
2. Expand the named gear component, then **Construction**, then its child components. The **Gear body and sketches** component contains the solid and its actual input sketches. Their visibility is enabled after creation.
3. Choose **Modify > Move/Copy**. Set **Move Object** to **Components** and select the outer named gear component in the Browser. Do not select only the body when you want the sketches to travel with it.
4. Move or rotate it and confirm the body and sketches move together. Capture the component position when Fusion offers it.
5. Select the gear again and use Gear Studio **Edit > Update gear**. The outer component and its placement stay in place; the generated Construction child is rebuilt.

Keep your own sketches and downstream modifications outside the generated Construction child. Edits inside it are replaced by Update gear. References to generated faces or bodies may prevent an update; references to the outer component's origin and axes are more stable. Use Fusion Undo to undo the complete Gear Studio command.

### Upgrade loose sketches in an existing gear

1. Save the design and **fully close Fusion**. Replace the loaded add-in folder using the update instructions below.
2. Restart Fusion. In Gear Studio's **Getting started**, confirm **0.3.3** and your Documents installation path.
3. Select the existing gear, refresh selection, choose **Edit**, then **Update gear**. This rebuilds its generated sketches with constraints and preserves the outer component's placement. Simply restarting does not rewrite old geometry.
4. Expand **Construction > ... > Gear body and sketches > Sketches**. Edit **Shaft bore cutter profile**. Its center should stay on the local origin, its diameter expression should reference `Bore_G1` (or your gear's alias), and it should resist center/radius dragging. Finish Sketch.
5. Inspect **Pitch circle**, **Shaft axis** and **Tooth groove profile** for a cylindrical gear. The shaft line is construction geometry with locked endpoints, and generated profiles should not drag or stretch. Their calculated shape changes through Gear Studio inputs and Update gear.
6. Move the **outer component**, not individual sketch entities or the body. The component is intentionally free to position within the assembly even though the sketches inside it are constrained to their local origin.

### Existing gears with only a Base Feature

They remain editable through the legacy update path. Their discarded construction steps cannot be recovered from the old body. To rebuild one with history, select it, refresh Gear Studio's selection, choose **Duplicate**, then **Create gear** in a Hybrid design. Inspect and position the new independent gear before removing the old one. Duplicate creates new parameter names; it does not transfer downstream face references. In a Part design, you can reuse the same settings in a new Hybrid design instead.

### Update to the construction-history version

1. Save your Fusion designs and close Fusion completely so Python modules and cached icons unload.
2. Follow the update instructions below for your existing Documents installation. Keep only one linked GearStudio copy; do not accidentally run an older copy from Downloads or the optional installer directory.
3. Start Fusion, run GearStudio, and open **Getting started**. Confirm **Gear Studio 0.3.3** and the intended Documents path.
4. Create a new Hybrid design and a new default Helical gear, then a Herringbone gear. Check for full tooth spaces all around, a shaft bore, visible sketches and an expanded timeline group.
5. Close the palette and reopen it from **Design > Solid > Create > Gear Studio**. It is also registered under **Utilities > Add-Ins**. Restart with Run on Startup enabled and check the command reappears without toggling the add-in. The palette need not open automatically on startup.

The new palette performs a bounded first-layout resize automatically. If it is still blank on 0.3.0, record the loaded path, Fusion version, Windows display scaling and whether a manual resize restores it. This needs native-host verification; browser tests cannot reproduce Fusion's Qt window lifecycle.

## Windows: Git alternative

Use this route if you already have Git and want to update with `git pull`. It creates the same Documents location as the ZIP instructions. You only need to follow one download route.

1. Save your designs and close Fusion.
2. Open **Windows PowerShell** normally from Start. No administrator window is needed.
3. Run `git --version`. If Git is not recognized, use the ZIP instructions above.
4. Paste the complete block below. It uses Windows' configured Documents location and an explicit clone destination, so PowerShell's starting directory does not matter.

```powershell
& {
    $gearStudioDocuments = [Environment]::GetFolderPath('MyDocuments')
    if ([string]::IsNullOrWhiteSpace($gearStudioDocuments)) {
        throw 'Documents could not be located. Use the File Explorer ZIP instructions.'
    }
    $gearStudioParent = Join-Path $gearStudioDocuments 'FusionAddins'
    $gearStudioRepo = Join-Path $gearStudioParent 'fusion-gear-add-on'
    if (Test-Path -LiteralPath $gearStudioRepo) {
        throw 'The Documents destination already exists. Follow the update or move instructions.'
    }
    Get-Command git -ErrorAction Stop | Out-Null
    New-Item -ItemType Directory -Path $gearStudioParent -Force -ErrorAction Stop | Out-Null
    git clone https://github.com/tensegrity-audio/fusion-gear-add-on.git "$gearStudioRepo"
    if ($LASTEXITCODE -ne 0) { throw 'Git clone failed. Read the error above before continuing.' }
    Set-Location -LiteralPath $gearStudioRepo -ErrorAction Stop
    Write-Host ('Folder to select in Fusion: ' + (Join-Path $gearStudioRepo 'GearStudio'))
}
```

5. Copy the **Folder to select in Fusion** path printed on success.
6. Follow [Add the folder to Fusion](#3-add-the-folder-to-fusion), selecting that path.

The Documents lookup uses [.NET's special-folder API](https://learn.microsoft.com/en-us/dotnet/api/system.environment.getfolderpath). It avoids assuming Documents is always directly under the user profile.

## Move an existing installation into Documents

For an existing repository in Downloads or directly under your user folder, move the whole repository. This preserves a Git checkout and any local changes.

1. In Fusion's **Scripts and Add-Ins**, select the existing **GearStudio** entry. Record its folder location, stop it if running, disable **Run on Startup**, and use **Unlink** (the broken-link icon) for that linked copy. Unlinking does not delete its files.
2. Save your designs and fully close Fusion.
3. In File Explorer, open **Documents** and create **FusionAddins** if needed.
4. Move the repository folder containing both `README.md` and `GearStudio` into **Documents\FusionAddins**. Rename it **fusion-gear-add-on** if necessary. If that destination already exists, stop and identify which copy you want to keep; do not overwrite local work.
5. Reopen Fusion and follow [Add the folder to Fusion](#3-add-the-folder-to-fusion) for the new inner `GearStudio` folder.
6. Confirm the path displayed in Fusion is under Documents. Then run the add-in and re-enable **Run on Startup** if desired.

For example, an existing `C:\Users\griff\fusion-gear-add-on` checkout moves to `Documents\FusionAddins\fusion-gear-add-on`. Use File Explorer's Documents location so this also works with redirected Documents folders.

If the old entry points to `API\AddIns\GearStudio`, it is an installer-managed copy that Fusion discovers automatically. After stopping it and closing Fusion, move that old **GearStudio** folder to a backup location outside `API\AddIns`. Then obtain the repository in Documents using the ZIP or Git route and link it. This prevents Fusion from loading two copies. Keep the backup until the Documents copy works.

Settings and presets live outside the add-in folder; moving the code does not reset them. Existing gear definitions remain in saved Fusion designs.

## Update an installation

**Always save your designs and fully close Fusion before replacing files or pulling updates.** Fusion can retain old Python modules until it exits. Check the location shown in Scripts and Add-Ins so you update the copy Fusion actually loads.

### If you downloaded a ZIP

1. Download the latest repository ZIP and extract it separately.
2. Locate the new repository folder containing `README.md` and `GearStudio`.
3. Move the current `Documents\FusionAddins\fusion-gear-add-on` folder to a backup location, or rename it to an unused backup name.
4. Put the new repository folder in its place and name it exactly **fusion-gear-add-on**.
5. Restart Fusion and run GearStudio. Because the inner folder's path is unchanged, the existing link should continue to work. Re-add it if necessary.
6. Keep the backup until the updated add-in starts and you have checked a disposable design.

If you edited source files yourself, preserve and reconcile those changes before replacing the repository. To roll back, close Fusion, move the new copy aside and restore the backup at the original path.

### If you cloned with Git

In File Explorer, open **Documents > FusionAddins > fusion-gear-add-on**, type `powershell` in the address bar and press Enter. Then run:

```powershell
git pull --ff-only
```

If Git reports local changes, conflicts or a failure, stop and preserve your work before proceeding. After a successful pull, restart Fusion. With the recommended Documents link, there is no installer to rerun. A downloaded ZIP is not a Git checkout; update ZIP installations using the previous section.

## macOS

The recommended approach is also to keep the repository in Documents and link its inner folder.

1. Save your designs and quit Fusion.
2. Download the repository ZIP and extract it in Finder.
3. Find the folder that directly contains `README.md` and `GearStudio`. Move it into **Documents/FusionAddins** and rename it **fusion-gear-add-on**.
4. Start Fusion and follow [Add the folder to Fusion](#3-add-the-folder-to-fusion), selecting **Documents/FusionAddins/fusion-gear-add-on/GearStudio**.
5. Keep the linked files available locally. Updates use the same ZIP replacement or Git pull approach described above, with Fusion closed.

For a new Git checkout, open Terminal and run each line only after the previous one succeeds:

```sh
mkdir -p "$HOME/Documents/FusionAddins"
cd "$HOME/Documents/FusionAddins"
git clone https://github.com/tensegrity-audio/fusion-gear-add-on.git
cd fusion-gear-add-on
```

## Optional legacy installers

**These scripts use Fusion's default AddIns directory, rather than the recommended Documents location.** They remain available for users who deliberately prefer that layout or are updating an existing installer-managed copy. Do not run them as an additional step after linking the Documents copy.

The `.ps1` file is a Windows file-copy installer. The Fusion add-in is the **GearStudio folder**. Running the installer does not start the add-in inside Fusion.

| Platform | Installer | Copied add-in location |
| --- | --- | --- |
| Windows | `install_windows.ps1` | `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\GearStudio` |
| macOS | `install_macos.command` | `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/GearStudio` |

For Windows, save your designs and close Fusion, open the extracted repository folder in File Explorer, type `powershell` into the address bar and press Enter. Run `./install_windows.ps1` in that existing terminal so any errors remain visible. If PowerShell blocks execution, use the recommended Documents-and-link route. Changing execution policy or running as administrator is unnecessary for that route.

On macOS, close Fusion, then run `/bin/bash "/path/to/repository/install_macos.command"` from Terminal. Both scripts prompt you to confirm Fusion has closed. After copying finishes, start Fusion and run the discovered GearStudio entry in Scripts and Add-Ins.

If you use an installer-managed copy, downloading or pulling repository updates does not update that separate copy. Close Fusion and rerun the installer from the updated repository. The installers preserve previous installations in timestamped subfolders of:

| Platform | Installation backups |
| --- | --- |
| Windows | `%APPDATA%\GearStudio\installation-backups` |
| macOS | `~/Library/Application Support/GearStudio/installation-backups` |

To roll back an installer-managed copy, close Fusion, move the current `API/AddIns/GearStudio` folder aside and restore a backed-up `GearStudio` folder at that path.

## Packaged artifacts

A successful run in [GitHub Actions](https://github.com/tensegrity-audio/fusion-gear-add-on/actions) provides an evaluation ZIP in its Artifacts section. If the download contains another `GearStudio-<version>.zip`, extract that ZIP too. Put the folder whose contents include `README.md` and `GearStudio` at **Documents/FusionAddins/fusion-gear-add-on**, then link its inner `GearStudio` folder as above. If extraction produced loose files, create the `fusion-gear-add-on` folder and move those files into it together. An Actions pass verifies automated checks, not native Fusion compatibility.

## Removal and saved settings

For the recommended linked installation, stop GearStudio in Scripts and Add-Ins, disable Run on Startup and unlink it. Close Fusion before moving or deleting its repository folder. For an installer-managed copy, stop it and close Fusion, then move or remove only its `API/AddIns/GearStudio` folder. Keep source modifications or backups you still need.

Existing B-rep bodies remain in saved Fusion designs. Updating them requires the add-in. Settings and presets are stored separately:

| Platform | Preferences |
| --- | --- |
| Windows | `%APPDATA%\GearStudio\settings.json` |
| macOS | `~/Library/Application Support/GearStudio/settings.json` |

Logs are stored beside `settings.json` as `GearStudio.log` with bounded rotating backups. To reset preferences, close Fusion and rename `settings.json`; keeping the renamed file makes the reset reversible. Invalid settings files are preserved with a `.corrupt...` suffix when recovery succeeds.

## Troubleshooting

| Installation symptom | What to do |
| --- | --- |
| PowerShell says `Permission denied` while the prompt shows `C:\WINDOWS\system32` | Use the Documents Git block above, which sets an explicit destination, or use the ZIP route. No administrator terminal is needed. |
| `cd` says the repository does not exist | The clone likely failed. Read the earlier error and finish downloading successfully before changing folders. |
| Git says the destination already exists | Use the update or move instructions. Do not clone over an existing folder. |
| `git` is not recognized | Use the ZIP route; Git is optional. |
| `.ps1` or `.py` extensions are hidden | In Windows 11 File Explorer choose **View > Show > File name extensions**. In Windows 10, use the **View** tab's **File name extensions** checkbox. Select the inner GearStudio folder in Fusion regardless of whether extensions are visible. |
| No Run with PowerShell option, execution is blocked, or the installer window disappears | Use the recommended ZIP-and-link route. If diagnosing an installer run, launch it from an already-open PowerShell terminal as described above. |
| GearStudio does not appear | Select **All scripts and add-ins**, then add the inner GearStudio folder using **+ > Script or add-in from device**. Verify that `GearStudio.py` and `GearStudio.manifest` are directly inside it. |
| Two GearStudio entries appear, or an update seems unchanged | Inspect their displayed paths. Stop and unlink the stale linked copy; move any old automatically discovered `API/AddIns/GearStudio` copy aside with Fusion closed. Restart Fusion and run only the Documents copy. |
| Fusion reports a missing folder after moving files | Unlink the old entry and add the new inner GearStudio folder. |

### Creating a gear reports `3 : this is not a parametric design`

If the message begins **Fusion could not commit this gear**, update to **0.1.3**
or later. Earlier versions wrote user parameters while editing a Base Feature,
which uses direct modeling even within a history-enabled design. The correction
moves parameter writes before that edit; it does not change your design mode.

1. Save your designs and fully close Fusion.
2. Follow [Update an installation](#update-an-installation) for the folder Fusion
   actually loads. For a Git installation, open the Documents checkout and run
   `git pull --ff-only`. For a ZIP installation, replace that copy using the
   linked instructions.
3. Open `GearStudio/GearStudio.manifest` in a text editor and confirm its version
   is **0.1.3** or later. Reopen Fusion and run GearStudio.
4. In a new Hybrid design with **Capture Design History** enabled, create
   the default Spur. Confirm a body appears and Change Parameters contains its
   named input rows (for example, `Teeth_G1` in version 0.2.0). Then try editing the gear and **Update from Parameters**.

A separate message asking you to **Enable Capture Design History before
building editable gears** is a preflight rejection of a direct design. Finish
any active Base Feature edit first; in a genuinely direct design, enable history
before building. Do not switch an existing parametric design to direct mode to
work around the commit error, because that can discard its timeline.

If the commit still fails, retain the complete message, installed version and
`GearStudio.log`. Version 0.1.3 identifies the failing stage and logs the original
native traceback. Live confirmation of the correction remains pending.

### The panel says Interface preview inside Fusion, or reports an unavailable action

This was a connection defect in versions before 0.1.2. The browser adapter could
start before Fusion injected its live connection, and the Python handler could
mistake a host acknowledgement for an unsupported action.

1. Save your designs and fully close Fusion.
2. Follow [Update an installation](#update-an-installation) for the actual folder
   Fusion loads. Use `git pull --ff-only` from the Documents checkout if you
   cloned it, or replace the ZIP copy as described there.
3. Check that `GearStudio.manifest` shows version **0.1.2** or later.
4. Reopen Fusion and run GearStudio from Scripts and Add-Ins. The top-right label
   should change from **Connecting to Fusion** to **Autodesk Fusion**, with no
   Interface preview banner.
5. In a new Hybrid design with design history enabled, leave the default
   Spur values, wait for validation, and click **Create gear**. The intended
   result is a B-rep body in the active Fusion design.

Version 0.1.2 waits up to 15 seconds for the native connection, then displays a
persistent message and **Retry connection** if it is still unavailable. It never
silently switches to preview. If the native label still does not appear, or
creation fails, preserve the full error, the installed folder path and the Fusion
version. Live confirmation of this correction remains pending.

Developers can deliberately open the local web preview with `?preview=1`; that
mode cannot create native solids.

### Startup reports `RuntimeError: 3 : invalid id`

A traceback ending in `controller.py` at `addButtonDefinition` means Fusion found and loaded the add-in. Version 0.1.0 used dotted command IDs; 0.1.1 replaces them with letters, digits and underscores. Native confirmation of this correction is still pending.

Follow [Update an installation](#update-an-installation) with Fusion fully closed, or [move the installation into Documents](#move-an-existing-installation-into-documents) and then update it. Check that `GearStudio.manifest` shows version `0.1.1` or later. If the error remains, check the new traceback's folder path for a stale copy and retain the complete message and Fusion version for diagnosis.

### Using the add-in

| Symptom | Next action |
| --- | --- |
| Add-in is not listed | Confirm the exact folder nesting and register the `GearStudio` folder with **+ / Add**. |
| Panel was closed | Use the **Gear Studio** toolbar command, or stop and run the add-in again. |
| Named expression is invalid | Define the referenced parameter in this design and check its units. Presets do not bring unrelated document parameters with them. |
| Generated parameter is missing or renamed | Restore the original name identified by the error in Change Parameters, then retry. Use Shorten parameter names in Gear Studio for upgrading legacy rows. |
| Copied identity warning | Use **Duplicate** in Gear Studio to create independent definitions. Undo an ordinary copied component if it created duplicate identities. |
| Parameters changed but the complete solid did not | Select the gear and use **Update from Parameters**. Only an existing bore in gears built/updated with 0.3.2 has a live diameter binding; calculated tooth geometry still needs Update. |
| Build rejected or cancelled | Read the field-specific message. The previous successful solid remains the reference until a subsequent update succeeds. |
| Recovery or native API failure | Save a separate diagnostic copy if possible, record the Fusion version and reproduction steps, and inspect `GearStudio.log`. Complete the relevant checks in `ACCEPTANCE.md` before continuing to depend on the affected operation. |

## Startup says it cannot import __version__

This is an add-in loading bug fixed in **0.3.1**, not a missing Python installation. Fusion loads the entry point as a generated package without running `__init__.py`; the version is now imported from its own module.

The reported traceback loads `C:\Users\griff\fusion-gear-add-on\GearStudio`, which is outside Documents. Updating a different copy will not fix the copy Fusion is running.

1. Close Fusion completely. Download the latest repository ZIP and extract it. Keep the old folder as a backup until the new copy works.
2. Put the folder containing README.md and GearStudio in **Documents > FusionAddins > fusion-gear-add-on**. If that destination already exists, follow the update instructions above; preserve your own changes instead of overwriting them blindly. Use File Explorer's Documents entry so redirected/OneDrive Documents locations are respected.
3. Confirm the inner **GearStudio** folder contains **version.py**, **GearStudio.py** and **GearStudio.manifest**. The manifest should show **0.3.1**.
4. Open Fusion's **Scripts and Add-Ins** window. Remove the old GearStudio list entry pointing outside Documents. This removes its Fusion registration; keep the backup folder on disk.
5. Choose **+ > Script or add-in from device** and select **Documents > FusionAddins > fusion-gear-add-on > GearStudio**. Run it, then open **Getting started** and confirm version **0.3.1** and the correct loaded folder. Enable Run on Startup after it opens successfully.

Do not install Python packages or change PowerShell execution policy to fix this import error.
