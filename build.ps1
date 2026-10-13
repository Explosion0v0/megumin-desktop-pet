$ErrorActionPreference='Stop'
$python=Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $python)) {throw '先按 README 创建 .venv 并安装 requirements.txt'}
Push-Location -LiteralPath $PSScriptRoot
try {
 & $python tools/check_assets.py
 if ($LASTEXITCODE -ne 0) {throw '缺少自备运行素材，参见 docs/ASSETS.md'}
 & $python -m PyInstaller --noconfirm MeguminPet.spec
 if ($LASTEXITCODE -ne 0) {throw 'Build failed'}
} finally {Pop-Location}
