param(
  [string]$PiperVersion = "2023.11.14-2",
  [string]$VoiceName = "fr_FR-siwis-medium"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$PiperDir = Join-Path $Root "piper"
$VoicesDir = Join-Path $Root "voices"
$ZipPath = Join-Path $Root "piper_windows_amd64.zip"
$ExtractDir = Join-Path $Root "piper-extract"

$PiperUrl = "https://github.com/rhasspy/piper/releases/download/$PiperVersion/piper_windows_amd64.zip"
$VoiceBaseUrl = "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium"
$ModelUrl = "$VoiceBaseUrl/$VoiceName.onnx"
$ConfigUrl = "$VoiceBaseUrl/$VoiceName.onnx.json"

New-Item -ItemType Directory -Force -Path $PiperDir, $VoicesDir | Out-Null

Write-Host "[Volp-E] Downloading Piper $PiperVersion..."
Invoke-WebRequest -Uri $PiperUrl -OutFile $ZipPath

if (Test-Path $ExtractDir) {
  Remove-Item -Recurse -Force $ExtractDir
}
New-Item -ItemType Directory -Force -Path $ExtractDir | Out-Null
Expand-Archive -Path $ZipPath -DestinationPath $ExtractDir -Force

$PiperExe = Get-ChildItem -Path $ExtractDir -Recurse -Filter "piper.exe" | Select-Object -First 1
if (-not $PiperExe) {
  throw "piper.exe not found in archive."
}

Copy-Item -Path (Join-Path $PiperExe.Directory.FullName "*") -Destination $PiperDir -Recurse -Force

Write-Host "[Volp-E] Downloading French voice $VoiceName..."
Invoke-WebRequest -Uri $ModelUrl -OutFile (Join-Path $VoicesDir "$VoiceName.onnx")
Invoke-WebRequest -Uri $ConfigUrl -OutFile (Join-Path $VoicesDir "$VoiceName.onnx.json")

Remove-Item -Force $ZipPath
Remove-Item -Recurse -Force $ExtractDir

Write-Host "[Volp-E] Piper installed."
Write-Host "[Volp-E] Test with:"
Write-Host "  .\start-desktop-brain.ps1"
