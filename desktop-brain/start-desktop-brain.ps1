$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$PiperExe = Join-Path $ScriptDir "piper\piper.exe"
$PiperModel = Join-Path $ScriptDir "voices\fr_FR-siwis-medium.onnx"
if ((Test-Path $PiperExe) -and (Test-Path $PiperModel)) {
  Write-Host "[Volp-E] Piper voice ready."
} else {
  Write-Host "[Volp-E] Piper voice not installed; Windows TTS fallback will be used."
  Write-Host "[Volp-E] Run .\install-piper-windows.ps1 for a better local voice."
}

$BundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if (Test-Path $BundledPython) {
  & $BundledPython .\volpe_desktop_brain.py
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
  py .\volpe_desktop_brain.py
} elseif ((Get-Command python -ErrorAction SilentlyContinue) -and ((python --version 2>$null) -match "Python")) {
  python .\volpe_desktop_brain.py
} else {
  throw "Python introuvable. Installe Python ou lance avec le Python embarque de Codex."
}
