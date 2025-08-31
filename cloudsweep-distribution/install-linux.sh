#!/bin/bash
# CloudSweep Linux Installer

echo "🐧 CloudSweep Linux Installer"
echo "============================="

# Check if running as root or with sudo access
if [ "$EUID" -ne 0 ]; then
    echo "⚠️  This installer requires sudo access for system dependencies"
    echo "Please run: sudo ./install-linux.sh"
    exit 1
fi

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    DISTRO=$ID
else
    echo "❌ Cannot detect Linux distribution"
    exit 1
fi

echo "📋 Detected: $OS"

# Install system dependencies based on distribution
echo "📦 Installing system dependencies..."
case $DISTRO in
    "ubuntu"|"debian")
        apt-get update
        apt-get install -y python3 python3-pip python3-dev build-essential binutils
        ;;
    "centos"|"rhel"|"fedora"|"amzn")
        if command -v dnf &> /dev/null; then
            dnf install -y python3 python3-pip python3-devel gcc gcc-c++ binutils
        elif command -v yum &> /dev/null; then
            yum install -y python3 python3-pip python3-devel gcc gcc-c++ binutils
        fi
        ;;
    "alpine")
        apk add --no-cache python3 python3-dev py3-pip gcc musl-dev binutils
        ;;
    *)
        echo "⚠️  Unknown distribution: $DISTRO"
        echo "Please ensure these packages are installed:"
        echo "  - python3, python3-pip, python3-dev"
        echo "  - gcc, build-essential/gcc-c++"
        echo "  - binutils"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
        ;;
esac

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip3 install --upgrade pip
pip3 install -r requirements.txt

# Check if executable exists
if [ -f "executables/linux/cloudsweep-linux" ]; then
    echo "✅ Linux executable found"
else
    echo "🔨 Building Linux executable..."
    python3 build.py
    
    if [ ! -f "executables/linux/cloudsweep-linux" ]; then
        echo "❌ Build failed"
        echo "💡 Trying Python script installation instead..."
        
        # Fallback: Install Python script directly
        cp cloudsweep.py /usr/local/bin/cloudsweep.py
        cat > /usr/local/bin/cloudsweep << 'EOF'
#!/bin/bash
python3 /usr/local/bin/cloudsweep.py "$@"
EOF
        chmod +x /usr/local/bin/cloudsweep
        
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
cp executables/linux/cloudsweep-linux /usr/local/bin/cloudsweep
chmod +x /usr/local/bin/cloudsweep

echo ""
echo "✅ CloudSweep installed successfully!"
echo ""
echo "🎯 Quick start:"
echo "  cloudsweep scan --region us-east-1"
echo ""
echo "📚 Help:"
echo "  cloudsweep --help"