# Build the portable exe and the Windows installer (run on Windows from the repo root).
#   powershell -ExecutionPolicy Bypass -File tools\build_installer.ps1
# Needs Python with pyinstaller, and Inno Setup 6 (https://jrsoftware.org/isdl.php,
# or: winget install JRSoftware.InnoSetup).
$ErrorActionPreference = 'Stop'

$version = (python -c "import command_store as c; v = c.APP_VERSION; print(v + '.0' * (2 - v.count('.')))").Trim()
Write-Host "Building GAM Command Bank $version"

# portable single-file exe -> dist\GAM_Command_Bank.exe
$env:GCB_ONEDIR = ''
pyinstaller --noconfirm GAM_Command_Bank.spec
if ($LASTEXITCODE) { throw 'pyinstaller (portable) failed' }

# app folder for the installer -> dist\GAM_Command_Bank\
$env:GCB_ONEDIR = '1'
pyinstaller --noconfirm --workpath build\onedir GAM_Command_Bank.spec
if ($LASTEXITCODE) { throw 'pyinstaller (installer folder) failed' }
$env:GCB_ONEDIR = ''

$iscc = @(
    (Get-Command iscc -ErrorAction SilentlyContinue).Source,
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $iscc) { throw 'Inno Setup 6 not found (winget install JRSoftware.InnoSetup)' }

& $iscc "/DAppVersion=$version" installer\GAM_Command_Bank.iss
if ($LASTEXITCODE) { throw 'Inno Setup failed' }

Get-Item dist\GAM_Command_Bank.exe, "dist\GAM_Command_Bank_Setup_$version.exe" |
    Format-Table Name, @{n='MB'; e={[math]::Round($_.Length / 1MB, 1)}}
