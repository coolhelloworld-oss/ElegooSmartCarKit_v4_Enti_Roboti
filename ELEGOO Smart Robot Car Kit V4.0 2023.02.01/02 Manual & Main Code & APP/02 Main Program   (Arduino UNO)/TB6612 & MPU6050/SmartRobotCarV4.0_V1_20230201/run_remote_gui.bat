@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul

if "%HOST%"=="" set "HOST=192.168.4.1"
if "%PORT%"=="" set "PORT=100"
if "%CAMERA_URL%"=="" set "CAMERA_URL=http://192.168.4.1:81/stream"
if "%SPEED%"=="" set "SPEED=150"

set "PYTHON=py -3"
%PYTHON% -V >nul 2>&1
if errorlevel 1 (
  set "PYTHON=python"
)

%PYTHON% -V >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python 3 not found. Install Python 3 and try again.
  goto :end
)

if not exist ".venv" (
  echo [INFO] Creating virtual environment...
  %PYTHON% -m venv ".venv"
)

set "VENV_PY=%SCRIPT_DIR%.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
  echo [ERROR] Virtual environment not created correctly.
  goto :end
)

echo [INFO] Installing dependencies...
"%VENV_PY%" -m pip install --upgrade pip
"%VENV_PY%" -m pip install -r "requirements_remote_gui.txt"

echo [INFO] Starting Enti Roboti Remote GUI...
"%VENV_PY%" enti_roboti_remote_control.py --host "%HOST%" --port "%PORT%" --camera-url "%CAMERA_URL%" --speed "%SPEED%"

:end
popd >nul
pause
