@echo off
setlocal enabledelayedexpansion

set "BASE_DIR=%CD%\input"
set "OUTPUT_DIR=%CD%\output"

REM Create output folder if not exists
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

for /r "%BASE_DIR%" %%f in (*.jpg) do (
    REM Skip files already in the output folder
    echo %%f | findstr /i /c:"\output\" >nul
    if errorlevel 1 (
        set "fullpath=%%f"

        REM Remove the BASE_DIR part from fullpath to get relative path
        set "relpath=!fullpath:%BASE_DIR%\=!"

        REM Compose output path
        set "outpath=%OUTPUT_DIR%\!relpath!"

        REM Create output directory if not exists
        for %%a in ("!outpath!") do (
            if not exist "%%~dpa" mkdir "%%~dpa"
        )

        echo Processing: %%f
        echo Output: !outpath!

        REM Run the executable
        problem2.exe "%%f" "!outpath!"
    )
)

pause
