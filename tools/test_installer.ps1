# End-to-end check of the Windows installer (used by CI; safe to run locally,
# but it installs and then uninstalls GAM Command Bank for the current user).
#   powershell -ExecutionPolicy Bypass -File tools\test_installer.ps1
$ErrorActionPreference = 'Stop'

$setup = Get-Item dist\GAM_Command_Bank_Setup_*.exe | Select-Object -First 1
if (-not $setup) { throw 'installer not found in dist\' }
$app  = "$env:LOCALAPPDATA\Programs\GAM Command Bank"
$data = "$env:APPDATA\GAM Command Bank"

function Wait-For([scriptblock]$cond, [int]$seconds, [string]$what) {
    for ($i = 0; $i -lt $seconds; $i++) { if (& $cond) { return }; Start-Sleep 1 }
    throw "timed out waiting for: $what"
}

Write-Host "Installing $($setup.Name) silently (current user)"
$p = Start-Process $setup.FullName -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART' -Wait -PassThru
if ($p.ExitCode) { throw "setup exited with $($p.ExitCode)" }
foreach ($f in 'GAM_Command_Bank.exe', 'installed.marker', 'unins000.exe',
               '_internal\commands.json', '_internal\assets\icon-256.png') {
    if (-not (Test-Path "$app\$f")) { throw "installed copy is missing $f" }
}
$lnk = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\GAM Command Bank.lnk"
if (-not (Test-Path $lnk)) { throw 'Start menu shortcut missing' }
$ver = (Get-Item "$app\GAM_Command_Bank.exe").VersionInfo
Write-Host "Installed: $($ver.ProductName) $($ver.ProductVersion)"
if ($ver.ProductName -ne 'GAM Command Bank') { throw "unexpected exe ProductName '$($ver.ProductName)'" }

Write-Host 'Launching the installed app'
$run = Start-Process "$app\GAM_Command_Bank.exe" -PassThru
Wait-For { Test-Path "$data\commands.json" } 30 'first-run data in %APPDATA%'
if ($run.HasExited) { throw "app exited early with code $($run.ExitCode)" }
if (Test-Path "$app\commands.json") { throw 'installed app wrote data into the program folder' }
Stop-Process -Id $run.Id -Force
Start-Sleep 2

Write-Host 'Uninstalling silently'
Start-Process "$app\unins000.exe" -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART' -Wait
Wait-For { -not (Test-Path "$app\GAM_Command_Bank.exe") } 60 'uninstall to remove the app'
if (Test-Path $lnk) { throw 'uninstall left the Start menu shortcut' }
if (-not (Test-Path "$data\commands.json")) { throw 'uninstall removed the user''s commands' }

Write-Host 'Installer test passed: install, launch, data location and uninstall all OK'
