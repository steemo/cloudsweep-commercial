#!/bin/bash
# CloudSweep Linux Installer

echo "🐧 CloudSweep Linux Installer"
echo "============================="

# Check if executable exists
if [ -f "executables/linux/cloudsweep-linux" ]; then
    echo "✅ Linux executable found"
else
    echo "📦 Building Linux executable..."
    python3 build.py
    
    if [ ! -f "executables/linux/cloudsweep-linux" ]; then
        echo "❌ Build failed"
        exit 1
    fi
fi

# Install to /usr/local/bin
echo "🔧 Installing CloudSweep..."
sudo cp executables/linux/cloudsweep-linux /usr/local/bin/cloudsweep
sudo chmod +x /usr/local/bin/cloudsweep

echo ""
echo "✅ CloudSweep installed successfully!"
echo ""
echo "🎯 Quick start:"
echo "  cloudsweep scan --region us-east-1"
echo ""
echo "📚 Help:"
echo "  cloudsweep --help"