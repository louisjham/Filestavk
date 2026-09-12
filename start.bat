@echo off
setlocal

echo ===================================================
echo             Filestavk Legal Management             
echo ===================================================

cd /d "%~dp0"

echo.
echo [1/2] Launching Backend Server [FastAPI on 0.0.0.0:8000]...
if exist "%~dp0backend\.venv\Scripts\activate.bat" goto :with_venv
goto :no_venv

:with_venv
echo [OK] Activating dedicated backend virtual environment...
start "Filestavk Backend [FastAPI]" cmd /k "cd /d "%~dp0backend" && call .venv\Scripts\activate.bat && python run.py"
goto :start_frontend

:no_venv
echo [!] Dedicated venv not found, using system python...
start "Filestavk Backend [FastAPI]" cmd /k "cd /d "%~dp0backend" && python run.py"
goto :start_frontend

:start_frontend
timeout /t 2 /nobreak > nul

echo [2/2] Launching Frontend [Vite on http://localhost:5173]...
start "Filestavk Frontend [Vite]" cmd /k "cd /d "%~dp0frontend" && npm run dev -- --host"

echo.
echo ===================================================
echo   Filestavk is ready for your demo:
echo   - Local HTTPS:     https://localhost:5173
echo   - Local Network:   https://192.168.12.166:5173
echo   - Custom Domain:   https://filestavk.law:5173
echo   - Backend API:     http://localhost:8000/docs
echo   - Attorney Login:  admin / admin123
echo   - Assistant Login: asst / asst123
echo ===================================================
echo.
pause
