# Build script for Clawdmeter-Windows.
# Creates a venv, installs deps, and produces dist/Clawdmeter.exe.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

if (-not (Test-Path .venv)) {
    py -3 -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\pip.exe install -r requirements.txt
& .\.venv\Scripts\pip.exe install pyinstaller==6.20.0

& .\.venv\Scripts\pyinstaller.exe --clean Clawdmeter.spec

Write-Output ""
Write-Output "Built: $root\dist\Clawdmeter.exe"
