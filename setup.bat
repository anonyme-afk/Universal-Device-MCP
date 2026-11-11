@echo off
setlocal
echo ========================================================================
echo   Launching Universal Device MCP One-Click Setup...
echo ========================================================================

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    where py >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo [x] Error: Python was not found in PATH.
        echo     Please install Python 3.11+ from https://www.python.org/downloads/
        echo     Make sure to check "Add Python to PATH" during installation.
        pause
        exit /b 1
    )
    py -3 -m pip --version >nul 2>nul
    py -3 quickstart.py %*
) else (
    python quickstart.py %*
)

if %ERRORLEVEL% neq 0 (
    echo.
    echo [x] Setup encountered an issue. See messages above.
    pause
    exit /b %ERRORLEVEL%
)

endlocal

