@echo off
setlocal
echo ===================================================
echo     Filestavk Local Domain Setup (filestavk.law)
echo ===================================================
echo.
echo This script maps filestavk.law to 127.0.0.1 in your Windows hosts file.
echo.

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Administrator privileges required.
    echo Please right-click this file and select "Run as administrator".
    echo.
    pause
    exit /b 1
)

set HOSTS_FILE=%WINDIR%\System32\drivers\etc\hosts

findstr /i "filestavk.law" "%HOSTS_FILE%" >nul
if %errorlevel% equ 0 (
    echo [OK] filestavk.law is already registered in %HOSTS_FILE%
) else (
    echo 127.0.0.1  filestavk.law >> "%HOSTS_FILE%"
    echo [SUCCESS] Added "127.0.0.1 filestavk.law" to %HOSTS_FILE%
)

echo.
echo You can now access Filestavk at:
echo   http://filestavk.law:5173
echo.
pause
