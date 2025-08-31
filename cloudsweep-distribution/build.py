#!/usr/bin/env python3
"""
CloudSweep Smart Builder
Detects OS and builds appropriate executable
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

def detect_platform():
    """Detect current platform and return appropriate names"""
    system = platform.system().lower()
    
    if system == 'darwin':
        return 'macos', 'cloudsweep-macos'
    elif system == 'windows':
        return 'windows', 'cloudsweep-windows.exe'
    else:  # Linux and others
        return 'linux', 'cloudsweep-linux'

def check_linux_dependencies():
    """Check if required Linux dependencies are available"""
    required_commands = ['gcc', 'objdump']
    missing = []
    
    for cmd in required_commands:
        if not shutil.which(cmd):
            missing.append(cmd)
    
    if missing:
        print(f"❌ Missing system dependencies: {', '.join(missing)}")
        print("📋 Required packages:")
        print("  Ubuntu/Debian: sudo apt-get install build-essential binutils")
        print("  CentOS/RHEL:   sudo yum install gcc gcc-c++ binutils")
        print("  Fedora:        sudo dnf install gcc gcc-c++ binutils")
        print("  Alpine:        sudo apk add gcc musl-dev binutils")
        return False
    
    return True

def check_macos_dependencies():
    """Check if required macOS dependencies are available"""
    # Check for Xcode Command Line Tools
    try:
        subprocess.run(['xcode-select', '-p'], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Xcode Command Line Tools not found")
        print("📋 Install with: xcode-select --install")
        return False

def check_windows_dependencies():
    """Check if required Windows dependencies are available"""
    # Check for Visual C++ compiler (cl.exe)
    if shutil.which('cl'):
        return True
    
    print("❌ Visual C++ Build Tools not found")
    print("📋 Required for PyInstaller on Windows")
    print("  Download: https://visualstudio.microsoft.com/visual-cpp-build-tools/")
    print("  Or install Visual Studio with C++ development tools")
    return False

def install_pyinstaller():
    """Install PyInstaller if not available"""
    try:
        import PyInstaller
        return True
    except ImportError:
        print("📦 Installing PyInstaller...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], 
                         check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False

def clean_build_artifacts():
    """Clean up build artifacts"""
    artifacts = ['dist', 'build', '*.spec']
    for artifact in artifacts:
        if '*' in artifact:
            for path in Path('.').glob(artifact):
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
        else:
            path = Path(artifact)
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()

def main():
    print("🚀 CloudSweep Smart Builder")
    print("=" * 40)
    
    # Check if source file exists
    source_file = Path('cloudsweep.py')
    if not source_file.exists():
        print("❌ Error: cloudsweep.py not found")
        return False
    
    # Detect platform
    platform_name, exe_name = detect_platform()
    print(f"🖥️  Platform detected: {platform_name}")
    print(f"📁 Building: {exe_name}")
    
    # Check system dependencies based on platform
    if platform_name == 'linux':
        if not check_linux_dependencies():
            print("❌ Missing system dependencies")
            print("💡 Run the installer with sudo to install dependencies")
            return False
    elif platform_name == 'macos':
        if not check_macos_dependencies():
            print("❌ Missing system dependencies")
            print("💡 Run: xcode-select --install")
            return False
    elif platform_name == 'windows':
        if not check_windows_dependencies():
            print("❌ Missing system dependencies")
            print("💡 Install Visual C++ Build Tools")
            return False
    
    # Install PyInstaller
    if not install_pyinstaller():
        print("❌ Failed to install PyInstaller")
        return False
    
    print("✅ PyInstaller ready")
    
    # Clean previous builds
    print("🧹 Cleaning previous builds...")
    clean_build_artifacts()
    
    # Build executable
    print(f"🔨 Building {platform_name} executable...")
    
    cmd = [
        'pyinstaller',
        '--onefile',
        '--name', exe_name.replace('.exe', ''),  # Remove .exe for PyInstaller
        'cloudsweep.py'
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Build successful")
        
        # Create target directory
        target_dir = Path(f'executables/{platform_name}')
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Find built executable
        dist_dir = Path('dist')
        built_files = list(dist_dir.glob('*'))
        
        if built_files:
            source_exe = built_files[0]
            target_exe = target_dir / exe_name
            
            # Copy executable
            shutil.copy2(source_exe, target_exe)
            
            # Make executable on Unix systems
            if platform_name != 'windows':
                os.chmod(target_exe, 0o755)
            
            # Show results
            size_mb = target_exe.stat().st_size / (1024 * 1024)
            print(f"📁 Created: {target_exe}")
            print(f"📊 Size: {size_mb:.1f} MB")
            
            # Clean up
            clean_build_artifacts()
            
            print(f"\n✅ {platform_name.title()} executable ready!")
            print(f"\n🧪 Test with:")
            print(f"  ./{target_exe} scan --region us-east-1")
            
            return True
            
        else:
            print("❌ No executable found after build")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)