@echo off
REM CloudSweep Windows Installer

echo 🪟 CloudSweep Windows Installer
echo ===============================

REM Check for admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ⚠️  This installer requires administrator privileges
    echo Please run as administrator
    pause
    exit /b 1
)

REM Check for Python 3
echo 🔍 Checking system requirements...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ Python 3 is required but not installed
    echo 📥 Download from: https://www.python.org/downloads/
    echo 💡 Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo ✅ Python found
for /f "tokens=*" %%i in ('python --version') do echo %%i

REM Check for pip
pip --version >nul 2>&1
if %errorLevel% neq 0 (
    echo 📦 Installing pip...
    python -m ensurepip --upgrade
)

REM Check for Visual C++ Build Tools (required for some Python packages)
echo 🔍 Checking for Visual C++ Build Tools...
where cl >nul 2>&1
if %errorLevel% neq 0 (
    echo ⚠️  Visual C++ Build Tools not found
    echo 📥 Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo 💡 Or install Visual Studio with C++ development tools
    echo 💡 Continuing anyway - executable build may fail
)

REM Install Python dependencies
echo 🐍 Installing Python dependencies...
pip install --upgrade pip
pip install -r requirements.txt

REM Check if executable exists
if exist "executables\windows\cloudsweep-windows.exe" (
    echo ✅ Windows executable found
) else (
    echo 🔨 Building Windows executable...
    python build.py
    
    if not exist "executables\windows\cloudsweep-windows.exe" (
        echo ❌ Build failed
        echo 💡 Trying Python script installation instead...
        
        REM Fallback: Install Python script directly
        if not exist "C:\Program Files\CloudSweep" (
            mkdir "C:\Program Files\CloudSweep"
        )
        
        copy "cloudsweep.py" "C:\Program Files\CloudSweep\cloudsweep.py"
        
        REM Create batch wrapper
        echo @echo off > "C:\Program Files\CloudSweep\cloudsweep.bat"
        echo python "C:\Program Files\CloudSweep\cloudsweep.py" %%* >> "C:\Program Files\CloudSweep\cloudsweep.bat"
        
        REM Add to PATH
        setx PATH "%PATH%;C:\Program Files\CloudSweep" /M
        
        echo ✅ CloudSweep installed as Python script
        echo.
        echo 🎯 Quick start:
        echo   cloudsweep scan --region us-east-1
        echo.
        echo 📚 Help:
        echo   cloudsweep --help
        echo.
        echo ⚠️  You may need to restart your command prompt
        pause
        exit /b 0
    )
)

REM Create CloudSweep directory in Program Files
if not exist "C:\Program Files\CloudSweep" (
    mkdir "C:\Program Files\CloudSweep"
)

REM Copy executable
echo 🔧 Installing CloudSweep executable...
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