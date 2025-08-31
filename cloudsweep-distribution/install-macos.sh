#!/bin/bash
# CloudSweep macOS Installer

echo "🍎 CloudSweep macOS Installer"
echo "============================="

# Check for required tools
echo "🔍 Checking system requirements..."

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    echo "📥 Install Python 3 from: https://www.python.org/downloads/"
    echo "📥 Or use Homebrew: brew install python3"
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Check for pip
if ! command -v pip3 &> /dev/null; then
    echo "📦 Installing pip..."
    python3 -m ensurepip --upgrade
fi

# Check for Xcode Command Line Tools (required for PyInstaller)
if ! xcode-select -p &> /dev/null; then
    echo "⚠️  Xcode Command Line Tools not found"
    echo "📥 Installing Xcode Command Line Tools..."
    xcode-select --install
    echo "⏳ Please complete the Xcode installation and run this script again"
    exit 1
fi

echo "✅ Xcode Command Line Tools found"

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip3 install --upgrade pip
pip3 install -r requirements.txt

# Check if executable exists
if [ -f "executables/macos/cloudsweep-macos" ]; then
    echo "✅ macOS executable found"
else
    echo "🔨 Building macOS executable..."
    python3 build.py
    
    if [ ! -f "executables/macos/cloudsweep-macos" ]; then
        echo "❌ Build failed"
        echo "💡 Trying Python script installation instead..."
        
        # Fallback: Install Python script directly
        sudo cp cloudsweep.py /usr/local/bin/cloudsweep.py
        sudo cat > /usr/local/bin/cloudsweep << 'EOF'
#!/bin/bash
python3 /usr/local/bin/cloudsweep.py "$@"
EOF
        sudo chmod +x /usr/local/bin/cloudsweep
        
        echo "✅ CloudSweep installed as Python script"
        echo ""
        echo "🎯 Quick start:"
        echo "  cloudsweep scan --region us-east-1"
        echo ""
        echo "📚 Help:"
        echo "  cloudsweep --help"
        exit 0
    fi
fi

# Install executable to /usr/local/bin
echo "🔧 Installing CloudSweep executable..."
sudo cp executables/macos/cloudsweep-macos /usr/local/bin/cloudsweep
sudo chmod +x /usr/local/bin/cloudsweep

echo ""
echo "✅ CloudSweep installed successfully!"
echo ""
echo "🎯 Quick start:"
echo "  cloudsweep scan --region us-east-1"
echo ""
echo "📚 Help:"
echo "  cloudsweep --help"