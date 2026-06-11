@echo off
setlocal
cd /d "%~dp0"

if not exist "env\Scripts\python.exe" (
    echo.
    echo Missing virtual environment. Expected:
    echo   %~dp0env\Scripts\python.exe
    echo.
    echo Create it from this folder:
    echo   python -m venv env
    echo   env\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

"env\Scripts\python.exe" "%~dp0dashboard.py"
set "EXITCODE=%ERRORLEVEL%"
if %EXITCODE% neq 0 (
    echo.
    echo dashboard.py exited with code %EXITCODE%.
    pause
)
exit /b %EXITCODE%
