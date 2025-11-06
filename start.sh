#!/bin/bash

# Koatsume - Startup script for Linux/MacOS
# This script creates a virtual environment if needed, installs requirements, and runs the app

set -e

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🌟 Koatsume Startup Script"
echo "=========================="

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed. Please install Python 3.7 or higher."
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"

# Check for system dependencies on Linux
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "🔍 Checking system dependencies for Linux..."
    
    # Function to check if a package is installed
    check_package() {
        if command -v dpkg &> /dev/null; then
            # Debian/Ubuntu
            dpkg -l "$1" 2>/dev/null | grep -q "^ii"
        elif command -v rpm &> /dev/null; then
            # Fedora/RHEL
            rpm -q "$1" &> /dev/null
        else
            # Unknown package manager, assume installed
            return 0
        fi
    }
    
    # Determine which packages to check based on distro
    MISSING_PACKAGES=()
    
    if command -v apt-get &> /dev/null; then
        # Ubuntu/Debian
        REQUIRED_PACKAGES=("python3-gi" "python3-gi-cairo" "gir1.2-gtk-3.0")
        
        # Check for WebKit2GTK - try different versions
        WEBKIT_PKG=""
        if check_package "gir1.2-webkit2-4.1"; then
            WEBKIT_PKG="gir1.2-webkit2-4.1"
        elif check_package "gir1.2-webkit2-4.0"; then
            WEBKIT_PKG="gir1.2-webkit2-4.0"
        else
            # Neither installed, find which one is available
            if apt-cache show gir1.2-webkit2-4.1 &> /dev/null; then
                WEBKIT_PKG="gir1.2-webkit2-4.1"
            elif apt-cache show gir1.2-webkit2-4.0 &> /dev/null; then
                WEBKIT_PKG="gir1.2-webkit2-4.0"
            else
                echo "⚠️  Warning: Could not find WebKit2GTK package. Trying gir1.2-webkit2-4.1..."
                WEBKIT_PKG="gir1.2-webkit2-4.1"
            fi
        fi
        
        # Check standard packages
        for pkg in "${REQUIRED_PACKAGES[@]}"; do
            if ! check_package "$pkg"; then
                MISSING_PACKAGES+=("$pkg")
            fi
        done
        
        # Check WebKit package
        if ! check_package "$WEBKIT_PKG"; then
            MISSING_PACKAGES+=("$WEBKIT_PKG")
        fi
        
        if [ ${#MISSING_PACKAGES[@]} -ne 0 ]; then
            echo "⚠️  Missing system packages: ${MISSING_PACKAGES[*]}"
            echo "📦 Installing required system packages..."
            echo "This requires sudo privileges."
            sudo apt-get update -qq
            sudo apt-get install -y "${MISSING_PACKAGES[@]}"
            echo "✓ System packages installed"
        else
            echo "✓ All system dependencies are installed"
        fi
    elif command -v dnf &> /dev/null; then
        # Fedora
        REQUIRED_PACKAGES=("python3-gobject" "gtk3" "webkit2gtk3")
        for pkg in "${REQUIRED_PACKAGES[@]}"; do
            if ! check_package "$pkg"; then
                MISSING_PACKAGES+=("$pkg")
            fi
        done
        
        if [ ${#MISSING_PACKAGES[@]} -ne 0 ]; then
            echo "⚠️  Missing system packages: ${MISSING_PACKAGES[*]}"
            echo "📦 Installing required system packages..."
            echo "This requires sudo privileges."
            sudo dnf install -y "${MISSING_PACKAGES[@]}"
            echo "✓ System packages installed"
        else
            echo "✓ All system dependencies are installed"
        fi
    elif command -v yum &> /dev/null; then
        # RHEL/CentOS
        REQUIRED_PACKAGES=("python3-gobject" "gtk3" "webkit2gtk3")
        for pkg in "${REQUIRED_PACKAGES[@]}"; do
            if ! check_package "$pkg"; then
                MISSING_PACKAGES+=("$pkg")
            fi
        done
        
        if [ ${#MISSING_PACKAGES[@]} -ne 0 ]; then
            echo "⚠️  Missing system packages: ${MISSING_PACKAGES[*]}"
            echo "📦 Installing required system packages..."
            echo "This requires sudo privileges."
            sudo yum install -y "${MISSING_PACKAGES[@]}"
            echo "✓ System packages installed"
        else
            echo "✓ All system dependencies are installed"
        fi
    else
        echo "⚠️  Unknown Linux distribution. You may need to install GTK and WebKit manually."
        echo "   See README.md for instructions."
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "✓ macOS detected - no additional system dependencies needed"
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1

# Install requirements
echo "📥 Installing requirements..."
pip install -r requirements.txt

echo "✓ Requirements installed"
echo ""
echo "🚀 Starting Koatsume..."
echo ""

# Run the application
python app.py
