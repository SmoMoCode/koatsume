# koatsume 🌟
An app to connect lots of little things together.

## Features

- 🖥️ **Cross-platform**: Runs on Linux, macOS, and Windows
- 🐍 **Python-powered**: Built with Python and PyWebView
- 🎨 **Material UI**: Chunky, colorful Material UI-style interface
- 👤 **Persistent Username**: Your username is saved between sessions
- 🔍 **Auto-discovery**: Automatically finds other Koatsume instances on your LAN using zeroconf
- 🎯 **Visual Display**: Shows each discovered instance as a colorful tile

## Quick Start

### Linux / macOS

1. Make sure you have Python 3.7+ installed
2. Run the start script:
   ```bash
   ./start.sh
   ```

The script will:
- Create a virtual environment (if it doesn't exist)
- Install all required dependencies
- Launch the application

### Windows

1. Make sure you have Python 3.7+ installed from [python.org](https://www.python.org/)
2. Double-click `start.bat` or run it from the command prompt:
   ```cmd
   start.bat
   ```

The script will:
- Create a virtual environment (if it doesn't exist)
- Install all required dependencies
- Launch the application

## Manual Installation

If you prefer to set up manually:

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

## How It Works

1. **Username Persistence**: Enter your username in the text field and click "Save". Your username is stored in `config.json` and will be remembered next time you start the app.

2. **Instance Discovery**: The app uses zeroconf (Bonjour/mDNS) to:
   - Broadcast its presence on the local network
   - Discover other Koatsume instances
   - Display them as colorful tiles

3. **Network Requirements**: All instances must be on the same local network and be able to communicate via multicast DNS.

## Requirements

- Python 3.7 or higher
- Dependencies (automatically installed by start scripts):
  - `pywebview>=4.4` - For the GUI
  - `zeroconf>=0.132.0` - For service discovery

## Configuration

The app creates a `config.json` file in the same directory to store your username. This file is automatically created on first run and updated whenever you save your username.

## Troubleshooting

### Linux
- If you get an error about missing dependencies for PyWebView, install the required system packages:
  ```bash
  # Ubuntu/Debian
  sudo apt-get install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.0
  
  # Fedora
  sudo dnf install python3-gobject gtk3 webkit2gtk3
  ```

### macOS
- No additional dependencies needed - uses native WebKit

### Windows
- Make sure Python is added to your PATH during installation
- The app uses Edge WebView2 (usually pre-installed on Windows 10/11)

### Network Discovery Issues
- Ensure your firewall allows multicast DNS traffic
- Verify all instances are on the same local network
- Some networks (like corporate/enterprise networks) may block mDNS

## License

TBD
