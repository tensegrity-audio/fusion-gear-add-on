# Gear Studio user-scope installer. No administrator access or downloads.
# Close Autodesk Fusion before continuing. Preferences are preserved.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$gearStudioSource = Join-Path $PSScriptRoot 'GearStudio'
if (-not (Test-Path -LiteralPath (Join-Path $gearStudioSource 'GearStudio.py') -PathType Leaf) -or
    -not (Test-Path -LiteralPath (Join-Path $gearStudioSource 'GearStudio.manifest') -PathType Leaf)) {
    throw 'Extract the complete release first. GearStudio must be beside this installer.'
}
if ([string]::IsNullOrWhiteSpace($env:APPDATA)) {
    throw 'APPDATA is unavailable. Use the manual installation instructions in docs/INSTALL.md.'
}

$gearStudioAddIns = Join-Path $env:APPDATA 'Autodesk\Autodesk Fusion 360\API\AddIns'
$gearStudioDestination = Join-Path $gearStudioAddIns 'GearStudio'
$gearStudioBackupRoot = Join-Path $env:APPDATA 'GearStudio\installation-backups'
$gearStudioStamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd_HHmmss') + '_' + [Guid]::NewGuid().ToString('N').Substring(0, 8)
$gearStudioStage = Join-Path $gearStudioAddIns ('.GearStudio-install-' + $gearStudioStamp)
$gearStudioBackup = Join-Path (Join-Path $gearStudioBackupRoot $gearStudioStamp) 'GearStudio'
$gearStudioOldMoved = $false
$gearStudioStageCreated = $false

Write-Host ''
Write-Host 'Gear Studio for Autodesk Fusion' -ForegroundColor Cyan
Write-Host ('Install location: ' + $gearStudioDestination)
Write-Host 'Save your designs and fully close Autodesk Fusion before continuing.'
$null = Read-Host 'Press Enter after Fusion has closed, or Ctrl+C to stop'

try {
    $null = New-Item -ItemType Directory -Path $gearStudioAddIns -Force
    if ([IO.Path]::GetFullPath($gearStudioSource).TrimEnd('\') -eq [IO.Path]::GetFullPath($gearStudioDestination).TrimEnd('\')) {
        throw 'This installer is already inside the installation. Run it from a separate extracted release folder.'
    }
    if (Test-Path -LiteralPath $gearStudioStage) {
        throw 'A staging path already exists. Retry from a fresh terminal.'
    }
    $gearStudioStageCreated = $true
    Copy-Item -LiteralPath $gearStudioSource -Destination $gearStudioStage -Recurse
    if (-not (Test-Path -LiteralPath (Join-Path $gearStudioStage 'GearStudio.py') -PathType Leaf)) {
        throw 'The staged installation is incomplete. The existing installation has not been changed.'
    }
    if (Test-Path -LiteralPath $gearStudioDestination) {
        $null = New-Item -ItemType Directory -Path (Split-Path -Parent $gearStudioBackup) -Force
        Move-Item -LiteralPath $gearStudioDestination -Destination $gearStudioBackup
        $gearStudioOldMoved = $true
    }
    Move-Item -LiteralPath $gearStudioStage -Destination $gearStudioDestination
    Write-Host ''
    Write-Host 'Gear Studio files installed.' -ForegroundColor Green
    if ($gearStudioOldMoved) { Write-Host ('Previous installation: ' + $gearStudioBackup) }
    Write-Host 'Start Fusion, open Scripts and Add-Ins > Add-Ins, select GearStudio, and click Run.'
    Write-Host 'See docs/INSTALL.md for startup, rollback, and manual installation instructions.'
}
catch {
    $gearStudioError = $_
    if ($gearStudioOldMoved -and -not (Test-Path -LiteralPath $gearStudioDestination)) {
        try {
            Move-Item -LiteralPath $gearStudioBackup -Destination $gearStudioDestination
            Write-Host 'The previous installation was restored.'
        }
        catch {
            Write-Warning ('Automatic restoration failed. Restore the backup manually from: ' + $gearStudioBackup)
        }
    }
    throw $gearStudioError
}
finally {
    if ($gearStudioStageCreated -and (Test-Path -LiteralPath $gearStudioStage)) {
        Remove-Item -LiteralPath $gearStudioStage -Recurse -Force
    }
}
