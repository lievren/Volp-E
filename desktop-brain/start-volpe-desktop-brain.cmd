@echo off
title Volp-E Desktop Brain

cd /d "%~dp0"

set "VOLPE_PIPER_MODEL=%~dp0voices\fr_FR-tom-medium.onnx"
set "VOLPE_PIPER_EXE=%~dp0piper\piper.exe"
set "VOLPE_OLLAMA_MODEL=qwen3:1.7b"

echo ==========================================
echo        Volp-E Desktop Brain
echo ==========================================
echo.
echo Dossier : %~dp0
echo Voix    : Tom Medium
echo IA      : Qwen3 1.7B
echo Port    : 8787
echo.

python "%~dp0volpe_desktop_brain.py"

echo.
echo Le Desktop Brain s'est arrete.
pause