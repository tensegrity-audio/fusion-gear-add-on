# Install Gear Studio

Gear Studio is an Autodesk Fusion desktop add-in for Windows and macOS. Keep the installation folder named exactly `GearStudio`, with `GearStudio.py` and `GearStudio.manifest` directly inside it.

Native Fusion execution and installation must still be verified on both platforms for this initial release. The add-in requires a parametric Fusion design with usable component and BaseFeature APIs. It does not use the preview Custom Features API.

## Get the files

Choose one of these routes:

- **GitHub ZIP:** Open the [repository](https://github.com/tensegrity-audio/fusion-gear-add-on), choose **Code > Download ZIP**, and extract it. Open the resulting `fusion-gear-add-on-main` folder. It contains the installers and the inner `GearStudio` add-in folder.
- **Git clone:** Run the commands below and use the checked-out repository folder. There are no submodules or third-party packages to fetch for Fusion installation; the required geometry code is included.
- **Packaged artifact:** Open a successful run in the repository's [Actions tab](https://github.com/tensegrity-audio/fusion-gear-add-on/actions), download its build artifact, and extract it. If the artifact contains another `GearStudio-<version>.zip`, extract that ZIP too. The install root is the folder containing `README.md`, both installers and `GearStudio/`. An Actions pass verifies automated checks, not native Fusion compatibility.

```sh
git clone https://github.com/tensegrity-audio/fusion-gear-add-on.git
cd fusion-gear-add-on
```

Installers always copy the inner `GearStudio` folder. Do not rename the whole repository folder to `GearStudio` or register it in Fusion as if it were the add-in. No GitHub release or Marketplace installer is required.

## Windows

1. Get and extract or clone the files into a normal local folder as described above.
2. Save your designs and fully close Fusion.
3. Right-click `install_windows.ps1` and choose **Run with PowerShell**, or run it from a PowerShell terminal in the extracted folder:

   ```powershell
   .\install_windows.ps1
   ```

4. Read the destination printed by the script. Press Enter only after Fusion has closed.
5. Start Fusion and follow **Load the add-in** below.

The destination is:

```text
%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\GearStudio
```

If your computer's PowerShell policy blocks the script, use manual installation below. Changing system execution policy or running as administrator is unnecessary.

## macOS

1. Get and extract or clone the files into a normal local folder as described above.
2. Save your designs and fully quit Fusion.
3. Double-click `install_macos.command`. If Finder does not launch it, open Terminal and run:

   ```sh
   /bin/bash "/path/to/extracted/install_macos.command"
   ```

4. Read the destination printed by the script. Press Enter only after Fusion has quit.
5. Start Fusion and follow **Load the add-in** below.

The destination is:

```text
~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/GearStudio
```

The installer requires no administrator access and downloads nothing. If a managed Mac prevents local scripts, use manual installation or your normal IT process.

## Manual installation

1. Close Fusion.
2. Locate the `API/AddIns` directory for your platform shown above; create it if necessary.
3. If `GearStudio` already exists there, move it to a backup folder outside `AddIns`.
4. Copy the extracted `GearStudio` folder into `AddIns`.
5. Check that `AddIns/GearStudio/GearStudio.py` exists. Avoid an extra nested `GearStudio/GearStudio` directory.

Alternatively, use the **+** or **Add** control in Fusion's **Scripts and Add-Ins > Add-Ins** dialog to register the extracted `GearStudio` folder directly. Keep that folder at a stable local path if you use this approach.

## Load the add-in

1. Start Fusion and open a design in the Design workspace.
2. Open **Utilities > Add-Ins > Scripts and Add-Ins**. Fusion releases may place this command differently; search for **Scripts and Add-Ins** if necessary.
3. In the current dialog, select **All scripts and add-ins** to clear filters, find **GearStudio**, and click its **Run** icon. If it is missing, choose **+ > Script or add-in from device** and select the inner `GearStudio` directory. In the older dialog, use the **Add-Ins** tab and its **+ / Add** button.
4. Enable **Run on Startup** if desired.
5. The Gear Studio panel opens. A **Gear Studio** toolbar command also reopens it. It is placed in an available Create or assembly toolbar panel.

Use a modelable Part or Hybrid design with **Capture Design History** enabled. Pure Assembly design intent is unsupported for body creation. A Hybrid design receives a component per gear; a Part design receives a managed body in its root component. If Fusion reports an unsupported document mode or component context, follow the message before generating geometry. Do the first acceptance run in a new disposable design.

## First gear and subsequent edits

1. Choose **Spur**, leave the default settings, and generate a gear.
2. Select the resulting body or component, choose **Edit** in the panel's selection area, change the tooth count and update.
3. Open **Modify > Change Parameters** and find its `GS_...` parameter rows. Change face width, close the dialog, select the gear and choose **Update from Parameters**.
4. Save the Fusion document. Close and reopen it, select the gear and confirm **Edit** reloads its definition. Select the body when multiple gears share a Part design's root component.

Both edit paths explicitly rebuild a B-rep solid. Parameter-table changes alone do not regenerate geometry. If validation or a build fails, resolve the reported input problem before using the previous geometry as an updated result.

## Updates, backups and removal

The supplied installers stage the new folder before activating it. An existing installation is moved into a timestamped subfolder of:

| Platform | Installation backups |
| --- | --- |
| Windows | `%APPDATA%\GearStudio\installation-backups` |
| macOS | `~/Library/Application Support/GearStudio/installation-backups` |

To roll back, close Fusion, move the current `AddIns/GearStudio` folder aside, then copy a backed-up `GearStudio` folder into its place. Keep the current folder until you have confirmed the rollback works.

For a clean Git checkout, update the repository with `git pull --ff-only`, close Fusion, then rerun the appropriate installer. A Git pull updates the checkout; it does not update a separately installed copy. If you registered the checkout's inner `GearStudio` folder directly, close Fusion before pulling changes because Fusion will load those files in place. Keep local modifications on a branch and review changes before updating.

To uninstall, stop GearStudio in **Scripts and Add-Ins**, disable **Run on Startup**, close Fusion, then move or remove only its `AddIns/GearStudio` folder. Existing B-rep bodies remain in saved designs. Updating them requires the add-in.

The installers do not delete presets or last-used settings. These live in:

| Platform | Preferences |
| --- | --- |
| Windows | `%APPDATA%\GearStudio\settings.json` |
| macOS | `~/Library/Application Support/GearStudio/settings.json` |

Logs are stored beside `settings.json` as `GearStudio.log` with bounded rotating backups. To reset preferences, close Fusion and rename `settings.json`; keeping the renamed file makes the reset reversible. Invalid settings files are preserved with a `.corrupt...` suffix when recovery succeeds.

## Troubleshooting

### Startup reports `RuntimeError: 3 : invalid id`

If the traceback ends in `controller.py` at `addButtonDefinition`, Fusion has
already found and loaded the add-in. Version 0.1.0 used dotted command IDs;
0.1.1 replaces these with letters, digits and underscores. This startup fix
still needs confirmation in the affected Fusion installation.

1. Fully close Fusion to unload the old Python modules.
2. Download a fresh repository ZIP and extract it into a separate folder.
3. Find the `GearStudio` folder Fusion actually loads. The traceback gives its
   path; the Scripts and Add-Ins dialog also displays the location. A directly
   linked Downloads copy is separate from a copy in `API/AddIns`.
4. Move that old `GearStudio` folder aside, then put the new inner `GearStudio`
   folder at the exact same path. Keep the old copy until the update starts
   successfully. The new `GearStudio.manifest` must show version `0.1.1` or later.
5. Restart Fusion and run GearStudio again. If the location changed instead,
   unlink the old entry and add the new inner folder using
   **+ > Script or add-in from device**.

If the same error remains, check the path in the new traceback for a stale
second copy. Keep any different traceback with the full Fusion version for
further diagnosis. Updating the add-in folder does not reset remembered
settings, presets or saved Fusion gear definitions.

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
