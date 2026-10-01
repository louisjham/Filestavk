# ==============================================================================
# Filestavk - 1-Click Launch Demo Mode
# Sets FILESTAVK_DEMO=true, isolates database to filestavk_demo.db, and starts servers
# ==============================================================================

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "      FILESTAVK - DEMO & MARKETING MODE (LOCAL-FIRST)          " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "[*] Launching with 100% anonymized dummy data..." -ForegroundColor Gray
Write-Host "[*] Safe for screenshots, video walkthroughs, and client pitches." -ForegroundColor Gray
Write-Host "================================================================" -ForegroundColor Cyan

$env:FILESTAVK_DEMO = "true"
$env:PYTHONPATH = "$PSScriptRoot\backend"

$pythonExe = "$PSScriptRoot\backend\.venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}

# Run the python runner
& $pythonExe "$PSScriptRoot\run_demo.py" $args
