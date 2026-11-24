@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 goto fail
set "BOOT="
py -3 -c "import sys; assert sys.version_info >= (3,11)" >nul 2>&1
if not errorlevel 1 set "BOOT=py -3"
if defined BOOT goto python_ok
python -c "import sys; assert sys.version_info >= (3,11)" >nul 2>&1
if not errorlevel 1 set "BOOT=python"
if defined BOOT goto python_ok
echo Python 3.11 or newer was not found. Install Python with the launcher or add it to PATH.
goto fail
:python_ok
if exist ".venv\Scripts\python.exe" goto venv_ok
echo Creating a project virtual environment...
%BOOT% -m venv ".venv"
if errorlevel 1 goto fail
:venv_ok
set "PY=%~dp0.venv\Scripts\python.exe"
"%PY%" -c "import sys; assert sys.version_info >= (3,11)"
if errorlevel 1 goto fail
"%PY%" -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 goto fail
"%PY%" "%~dp0scripts\verify_installation.py"
set "CHECK=%ERRORLEVEL%"
if "%CHECK%"=="0" goto launch
if not "%CHECK%"=="3" goto fail
if defined STUDIO_DB goto fail
if exist "%~dp0data\.initialized" goto fail
echo.
echo No database was found. Existing users: cancel and set STUDIO_DB to your original database.
choice /C YN /N /M "Is this a NEW empty installation? Create a new database [Y/N]: "
if errorlevel 2 goto cancelled
if errorlevel 1 goto initialize
goto fail
:initialize
"%PY%" "%~dp0scripts\verify_installation.py" --initialize
if errorlevel 1 goto fail
:launch
echo.
echo Nexora: http://127.0.0.1:8501
echo Open the URL after Uvicorn reports that startup is complete.
echo Press Ctrl+C in this window to stop Studio. Ollama will not be started or stopped.
"%PY%" -m backend.main
if errorlevel 1 goto fail
goto end
:cancelled
echo Cancelled. No database was created. See README.md for existing-data setup.
goto end
:fail
echo.
echo Studio did not start or exited with an error. Read the messages above.
echo For existing data, verify STUDIO_DB and STUDIO_FILES. Do not initialize a replacement.
:end
pause
endlocal
