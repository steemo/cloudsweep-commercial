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

def detect_linux_distro():
    """Detect Linux distribution and return package manager info"""
    try:
        # Check /etc/os-release first
        with open('/etc/os-release', 'r') as f:
            os_release = f.read().lower()
        
        if 'amazon' in os_release or 'amzn' in os_release:
            return 'amazon', 'yum'
        elif 'ubuntu' in os_release or 'debian' in os_release:
            return 'debian', 'apt-get'
        elif 'centos' in os_release or 'rhel' in os_release or 'red hat' in os_release:
            return 'rhel', 'yum'
        elif 'fedora' in os_release:
            return 'fedora', 'dnf'
        elif 'alpine' in os_release:
            return 'alpine', 'apk'
        elif 'suse' in os_release:
            return 'suse', 'zypper'
    except FileNotFoundError:
        pass
    
    # Fallback: check for package managers
    if shutil.which('yum'):
        return 'rhel', 'yum'
    elif shutil.which('apt-get'):
        return 'debian', 'apt-get'
    elif shutil.which('dnf'):
        return 'fedora', 'dnf'
    elif shutil.which('apk'):
        return 'alpine', 'apk'
    elif shutil.which('zypper'):
        return 'suse', 'zypper'
    
    return 'unknown', 'unknown'

def install_linux_dependencies():
    """Automatically install Linux dependencies based on detected distro"""
    distro, pkg_manager = detect_linux_distro()
    
    print(f"🔍 Detected: {distro} with {pkg_manager}")
    print("📦 Installing build dependencies...")
    
    try:
        if pkg_manager == 'yum':
            # Amazon Linux, CentOS, RHEL
            subprocess.run(['sudo', 'yum', 'update', '-y'], check=True, capture_output=True)
            subprocess.run(['sudo', 'yum', 'groupinstall', '-y', 'Development Tools'], check=True, capture_output=True)
            subprocess.run(['sudo', 'yum', 'install', '-y', 'gcc', 'gcc-c++', 'binutils', 'python3-devel'], check=True, capture_output=True)
        
        elif pkg_manager == 'apt-get':
            # Ubuntu, Debian
            subprocess.run(['sudo', 'apt-get', 'update', '-y'], check=True, capture_output=True)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'build-essential', 'binutils', 'python3-dev'], check=True, capture_output=True)
        
        elif pkg_manager == 'dnf':
            # Fedora
            subprocess.run(['sudo', 'dnf', 'update', '-y'], check=True, capture_output=True)
            subprocess.run(['sudo', 'dnf', 'groupinstall', '-y', 'Development Tools'], check=True, capture_output=True)
            subprocess.run(['sudo', 'dnf', 'install', '-y', 'gcc', 'gcc-c++', 'binutils', 'python3-devel'], check=True, capture_output=True)
        
        elif pkg_manager == 'apk':
            # Alpine
            subprocess.run(['sudo', 'apk', 'update'], check=True, capture_output=True)
            subprocess.run(['sudo', 'apk', 'add', 'gcc', 'musl-dev', 'binutils', 'python3-dev', 'make'], check=True, capture_output=True)
        
        elif pkg_manager == 'zypper':
            # openSUSE
            subprocess.run(['sudo', 'zypper', 'refresh'], check=True, capture_output=True)
            subprocess.run(['sudo', 'zypper', 'install', '-y', 'gcc', 'gcc-c++', 'binutils', 'python3-devel'], check=True, capture_output=True)
        
        else:
            print(f"❌ Unsupported package manager: {pkg_manager}")
            return False
        
        print("✅ Dependencies installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def check_linux_dependencies():
    """Check if required Linux dependencies are available, install if missing"""
    required_commands = ['gcc', 'objdump']
    missing = []
    
    for cmd in required_commands:
        if not shutil.which(cmd):
            missing.append(cmd)
    
    if missing:
        print(f"❌ Missing system dependencies: {', '.join(missing)}")
        print("🔧 Attempting automatic installation...")
        
        if install_linux_dependencies():
            # Re-check after installation
            still_missing = []
            for cmd in required_commands:
                if not shutil.which(cmd):
                    still_missing.append(cmd)
            
            if still_missing:
                print(f"❌ Still missing after installation: {', '.join(still_missing)}")
                return False
            else:
                print("✅ All dependencies now available")
                return True
        else:
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
    """Install PyInstaller if not available with multiple fallback methods"""
    try:
        import PyInstaller
        return True
    except ImportError:
        print("📦 Installing PyInstaller...")
        
        # Try multiple installation methods
        install_methods = [
            [sys.executable, '-m', 'pip', 'install', 'pyinstaller'],
            ['pip3', 'install', 'pyinstaller'],
            ['pip', 'install', 'pyinstaller'],
            [sys.executable, '-m', 'pip', 'install', '--user', 'pyinstaller']
        ]
        
        for method in install_methods:
            try:
                print(f"🔧 Trying: {' '.join(method)}")
                result = subprocess.run(method, check=True, capture_output=True, text=True)
                print("✅ PyInstaller installed successfully")
                
                # Verify installation (reload modules to detect user installs)
                try:
                    import importlib
                    import sys
                    if 'PyInstaller' in sys.modules:
                        importlib.reload(sys.modules['PyInstaller'])
                    import PyInstaller
                    return True
                except ImportError:
                    # For --user installs, try importing after adding user site
                    try:
                        import site
                        import PyInstaller
                        return True
                    except ImportError:
                        continue
                    
            except subprocess.CalledProcessError as e:
                print(f"❌ Method failed: {e}")
                if e.stderr:
                    print(f"Error details: {e.stderr[:200]}...")
                continue
        
        # Final attempt: force reinstall to handle packaging conflicts
        print("🔄 Final attempt: force reinstall to handle conflicts...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', '--user', '--force-reinstall', 'pyinstaller'], 
                         check=True, capture_output=True)
            
            # Final verification
            try:
                import site
                import PyInstaller
                print("✅ PyInstaller force install successful")
                return True
            except ImportError:
                print("❌ PyInstaller still not importable after force install")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Force install failed: {e}")
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
        sys.executable,
        '-m', 'PyInstaller',
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