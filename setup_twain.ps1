$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $MyInvocation.MyCommand.Path
$tools = Join-Path $project "tools\twainsave"
$zip = Join-Path $env:TEMP "twainsave-binaries-x64.zip"
$url = "https://github.com/dynarithmic/Twainsave/releases/download/v1.4.1/twainsave-binaries-x64.zip"

Write-Host "Installing 64-bit TWAIN support for Unstoppable Invoice Splitter..."
if (Test-Path $tools) { Remove-Item $tools -Recurse -Force }
New-Item -ItemType Directory -Path $tools -Force | Out-Null

Invoke-WebRequest -Uri $url -OutFile $zip
Expand-Archive -Path $zip -DestinationPath $tools -Force
Remove-Item $zip -Force -ErrorAction SilentlyContinue

$exe = Get-ChildItem $tools -Recurse -Filter "twainsave64.exe" | Select-Object -First 1
if (-not $exe) {
    $exe = Get-ChildItem $tools -Recurse -Filter "twainsave-opensource.exe" | Select-Object -First 1
}
if (-not $exe) { throw "TwainSave 64-bit executable was not found after extraction." }

Write-Host ""
Write-Host "TWAIN support installed successfully."
Write-Host "Scanner bridge: $($exe.FullName)"
Write-Host ""
Write-Host "Installed TWAIN sources:"
& $exe.FullName --devicelist
