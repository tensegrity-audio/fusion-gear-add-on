#!/bin/bash
# Gear Studio user-scope installer. No administrator access or downloads.
# Close Autodesk Fusion before continuing. Preferences are preserved.
set -euo pipefail

gear_studio_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
gear_studio_source="$gear_studio_script_dir/GearStudio"
gear_studio_addins="$HOME/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns"
gear_studio_destination="$gear_studio_addins/GearStudio"
gear_studio_backup_root="$HOME/Library/Application Support/GearStudio/installation-backups"
gear_studio_stamp="$(date -u +%Y%m%d_%H%M%S)_$$"
gear_studio_stage="$gear_studio_addins/.GearStudio-install-$gear_studio_stamp"
gear_studio_backup="$gear_studio_backup_root/$gear_studio_stamp/GearStudio"
gear_studio_old_moved=0
gear_studio_stage_created=0

if [[ ! -f "$gear_studio_source/GearStudio.py" || ! -f "$gear_studio_source/GearStudio.manifest" ]]; then
    printf '%s\n' 'Extract the complete release first. GearStudio must be beside this installer.' >&2
    exit 1
fi

printf '\n%s\n' 'Gear Studio for Autodesk Fusion'
printf 'Install location: %s\n' "$gear_studio_destination"
printf '%s\n' 'Save your designs and fully quit Autodesk Fusion before continuing.'
read -r -p 'Press Return after Fusion has quit, or Ctrl+C to stop. ' gear_studio_ack

gear_studio_cleanup() {
    gear_studio_status=$?
    trap - EXIT
    if [[ $gear_studio_status -ne 0 && $gear_studio_old_moved -eq 1 && ! -e "$gear_studio_destination" ]]; then
        if mv "$gear_studio_backup" "$gear_studio_destination"; then
            printf '%s\n' 'The previous installation was restored.' >&2
        else
            printf 'Automatic restoration failed. Restore the backup manually from: %s\n' "$gear_studio_backup" >&2
        fi
    fi
    # Only this invocation's staging directory may be removed.
    if [[ $gear_studio_stage_created -eq 1 && -d "$gear_studio_stage" ]]; then rm -rf "$gear_studio_stage"; fi
    if [[ $gear_studio_status -ne 0 ]]; then
        printf '%s\n' 'Installation did not complete. See docs/INSTALL.md for manual installation.' >&2
    fi
    exit "$gear_studio_status"
}
trap gear_studio_cleanup EXIT

mkdir -p "$gear_studio_addins"
if [[ "$(cd -- "$gear_studio_source" && pwd -P)" == "$gear_studio_destination" ]]; then
    printf '%s\n' 'Run the installer from a separate extracted release folder.' >&2
    exit 1
fi
if [[ -e "$gear_studio_stage" || -e "$gear_studio_backup" ]]; then
    printf '%s\n' 'A staging or backup path already exists. Retry from a fresh terminal.' >&2
    exit 1
fi
gear_studio_stage_created=1
cp -R "$gear_studio_source" "$gear_studio_stage"
if [[ ! -f "$gear_studio_stage/GearStudio.py" || ! -f "$gear_studio_stage/GearStudio.manifest" ]]; then
    printf '%s\n' 'The staged installation is incomplete. The existing installation has not been changed.' >&2
    exit 1
fi
if [[ -e "$gear_studio_destination" ]]; then
    mkdir -p "$(dirname -- "$gear_studio_backup")"
    mv "$gear_studio_destination" "$gear_studio_backup"
    gear_studio_old_moved=1
fi
mv "$gear_studio_stage" "$gear_studio_destination"

printf '\n%s\n' 'Gear Studio files installed.'
if [[ $gear_studio_old_moved -eq 1 ]]; then
    printf 'Previous installation: %s\n' "$gear_studio_backup"
fi
printf '%s\n' 'Start Fusion, open Scripts and Add-Ins > Add-Ins, select GearStudio, and click Run.'
printf '%s\n' 'See docs/INSTALL.md for startup, rollback, and manual installation instructions.'
