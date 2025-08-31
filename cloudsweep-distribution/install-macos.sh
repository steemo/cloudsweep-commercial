#!/bin/bash
# CloudSweep macOS Installer

echo "🍎 CloudSweep macOS Installer"
echo "============================="

# Check if executable exists
if [ -f "executables/macos/cloudsweep-macos" ]; then
    echo "✅ macOS executable found"
else
    echo "📦 Building macOS executable..."
    python3 build.py
    
    if [ ! -f "executables/macos/cloudsweep-macos" ]; then
        echo "❌ Build failed"
        exit 1
    fi
fi

# Install to /usr/local/bin
echo "🔧 Installing CloudSweep..."
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