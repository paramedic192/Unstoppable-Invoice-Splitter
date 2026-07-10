@echo off
setlocal
cd /d "%~dp0"

echo ================================================
echo Building Unstoppable Invoice Splitter
echo ================================================
echo.

echo Installing or updating PyInstaller...
py -m pip install --upgrade pyinstaller
if errorlevel 1 goto :error

echo.
echo Cleaning previous build files...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "Unstoppable Invoice Splitter.spec" del /q "Unstoppable Invoice Splitter.spec"

echo.
echo Creating Windows executable...
py -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name "Unstoppable Invoice Splitter" ^
    --collect-all fitz ^
    --collect-all pymupdf ^
    --collect-all PySide6 ^
    app.py

if errorlevel 1 goto :error

echo.
echo ================================================
echo BUILD COMPLETE
echo ================================================
echo.
echo Your app is located here:
echo %CD%\dist\Unstoppable Invoice Splitter.exe
echo.
explorer "%CD%\dist"
pause
exit /b 0

:error
echo.
echo ================================================
echo BUILD FAILED
echo ================================================
echo Review the error messages above.
pause
exit /b 1
