$ErrorActionPreference = 'Stop'
$env:VGAMEPAD_SKIP_VIGEMBUS_INSTALL = 'true'
if (-not (Test-Path .venv\Scripts\python.exe)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
.\.venv\Scripts\pyinstaller.exe --noconfirm --clean --onefile --windowed --name DualSenseXbox-USB --collect-all vgamepad dualsense_xbox.py
if ($LASTEXITCODE -ne 0) { throw 'Executable build failed. Close the app if it is running, then retry.' }
Write-Host 'Built dist\DualSenseXbox-USB.exe'
