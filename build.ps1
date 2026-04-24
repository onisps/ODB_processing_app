$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$Requirements = Join-Path $ProjectDir "requirements.txt"
$Spec = Join-Path $ProjectDir "odb_processing_app.spec"

if (-not (Test-Path $VenvPython)) {
  $SystemPython = Get-Command python -ErrorAction Stop
  & $SystemPython.Source -m venv (Join-Path $ProjectDir ".venv")
}

& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r $Requirements
& $VenvPython -m PyInstaller --noconfirm --clean $Spec

$OutDir = Join-Path $ProjectDir "dist\ODBProcessingApp"
$OutExe = Join-Path $OutDir "ODBProcessingApp.exe"

if (Test-Path $OutExe) {
  Write-Host ("Build OK: " + $OutExe)
} else {
  Write-Host ("Build finished, but exe not found at: " + $OutExe)
  exit 1
}
