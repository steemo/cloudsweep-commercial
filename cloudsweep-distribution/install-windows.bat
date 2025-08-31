@echo off
REM CloudSweep Windows Installer

echo 🪟 CloudSweep Windows Installer
echo ===============================

REM Check if executable exists
if exist "executables\windows\cloudsweep-windows.exe" (
    echo ✅ Windows executable found
) else (
    echo 📦 Building Windows executable...
    python build.py
    
    if not exist "executables\windows\cloudsweep-windows.exe" (
        echo ❌ Build failed
        pause
        exit /b 1
    )
)

REM Create CloudSweep directory in Program Files
if not exist "C:\Program Files\CloudSweep" (
    mkdir "C:\Program Files\CloudSweep"
)

REM Copy executable
echo 🔧 Installing CloudSweep...
copy "executables\windows\cloudsweep-windows.exe" "C:\Program Files\CloudSweep\cloudsweep.exe"

REM Add to PATH (requires admin)
setx PATH "%PATH%;C:\Program Files\CloudSweep" /M

echo.
echo ✅ CloudSweep installed successfully!
echo.
echo 🎯 Quick start:
echo   cloudsweep scan --region us-east-1
echo.
echo 📚 Help:
echo   cloudsweep --help
echo.
echo ⚠️  You may need to restart your command prompt
pause