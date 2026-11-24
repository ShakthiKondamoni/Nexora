$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
python -m pip install -r requirements.txt -r requirements-desktop.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
python -m PyInstaller --noconfirm --clean --windowed --onedir --name Nexora --icon desktop/nexora.ico --paths . --add-data "frontend;frontend" --add-data "desktop/loading.html;desktop" desktop/launcher.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }
$iscc = @("$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Install Inno Setup 6; PyInstaller app is available at dist\Nexora." }
& $iscc "desktop\nexora.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup build failed." }
