# Install Gear Studio

**Recommended location: `Documents\FusionAddins\fusion-gear-add-on`.** Keep the files there and tell Fusion where to find the inner `GearStudio` folder. This is the default for our installation instructions and future setup examples.

For first-time Windows users, follow **Windows: download and install** below. You need Autodesk Fusion desktop and a ZIP download. Git, PowerShell installers, a separate Python installation and administrator access are not required for this route.

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

### 3. Add the folder to Fusion

1. Start Fusion and open a new design in the **Design** workspace.
2. Open **Utilities > Add-Ins > Scripts and Add-Ins**. If the toolbar placement differs, search Fusion's commands for **Scripts and Add-Ins**.
3. Select **All scripts and add-ins** to clear any filters that could hide Gear Studio.
4. Click **+**, then **Script or add-in from device**. If you have the older dialog, select the **Add-Ins** tab and click its **+ / Add** button.
5. Browse through **Documents > FusionAddins > fusion-gear-add-on > GearStudio** and select that **GearStudio folder**. The outer repository folder, `.py` file and `.ps1` file are not the folder Fusion needs.
6. Select **GearStudio** in the list and click its **Run** icon or button.
7. Enable **Run on Startup** if you want it available whenever Fusion opens.

Fusion remembers the linked folder and loads its files in place. This is a supported installation method; leave the folder in Documents after adding it. See [Autodesk's folder-linking instructions](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/WritingDebugging_UM.htm).

### 4. Confirm it opened

The **Gear Studio** panel should open. Its **Gear Studio** toolbar command reopens the panel after you close it. If an error appears, keep the entire message and see [Troubleshooting](#troubleshooting).

Use a modelable **Part** or **Hybrid** design with **Capture Design History** enabled. Pure Assembly design intent is unsupported for body creation. A Hybrid design receives a component per gear; a Part design receives a managed body in its root component.

Start with a new disposable design and the default Spur settings. Native Fusion acceptance is still incomplete; [the verification record](VERIFICATION.md) identifies the reported startup failure, source checks and remaining host tests. Merely appearing in the add-in list does not establish successful gear generation.

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

## First gear and subsequent edits


1. Choose **Spur**, leave the default settings, and generate a gear.
2. Select the resulting body or component, choose **Edit** in the panel's selection area, change the tooth count and update.
3. Open **Modify > Change Parameters** and find its `GS_...` parameter rows. Change face width, close the dialog, select the gear and choose **Update from Parameters**.
4. Save the Fusion document. Close and reopen it, select the gear and confirm **Edit** reloads its definition. Select the body when multiple gears share a Part design's root component.

Both edit paths explicitly rebuild a B-rep solid. Parameter-table changes alone do not regenerate geometry. If validation or a build fails, resolve the reported input problem before using the previous geometry as an updated result.

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
5. In a new Part or Hybrid design with design history enabled, leave the default
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
| Generated parameter is missing or renamed | Restore its original `GS_...` name in Change Parameters, then retry. |
| Copied identity warning | Use **Duplicate** in Gear Studio to create independent definitions. Undo an ordinary copied component if it created duplicate identities. |
| Parameters changed but the solid did not | Select the gear and use **Update from Parameters**. Automatic recomputation is not part of this release. |
| Build rejected or cancelled | Read the field-specific message. The previous successful solid remains the reference until a subsequent update succeeds. |
| Recovery or native API failure | Save a separate diagnostic copy if possible, record the Fusion version and reproduction steps, and inspect `GearStudio.log`. Complete the relevant checks in `ACCEPTANCE.md` before continuing to depend on the affected operation. |
