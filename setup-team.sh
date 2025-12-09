#!/bin/bash
# Team Setup Script for BlenderMCP
# Run this after cloning the repo

set -e

echo "============================================"
echo "BlenderMCP Team Setup"
echo "============================================"
echo

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "❌ uv not found. Please install it first:"
    echo
    echo "  macOS:   brew install uv"
    echo "  Linux:   curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  Windows: powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\""
    echo
    exit 1
fi
echo "✓ uv found"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.10+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Python $PYTHON_VERSION found"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo
    echo "Creating virtual environment..."
    uv venv
fi
echo "✓ Virtual environment ready"

# Activate and install
echo
echo "Installing dependencies..."
source .venv/bin/activate
uv pip install -e .
echo "✓ Dependencies installed"

# Check if Blender is installed
echo
echo "Checking for Blender..."
if command -v blender &> /dev/null; then
    BLENDER_VERSION=$(blender --version | head -1)
    echo "✓ $BLENDER_VERSION found"
elif command -v flatpak &> /dev/null && flatpak list | grep -q org.blender.Blender; then
    echo "✓ Blender (Flatpak) found"
else
    echo "⚠ Blender not found in PATH"
    echo "  Please install Blender 3.0+ and add to PATH"
    echo "  Or install via Flatpak: flatpak install flathub org.blender.Blender"
fi

echo
echo "============================================"
echo "Setup Complete!"
echo "============================================"
echo
echo "Next steps:"
echo
echo "1. Open Blender and install the addon:"
echo "   - Edit > Preferences > Add-ons > Install..."
echo "   - Select: $(pwd)/addon.py"
echo "   - Enable 'Interface: Blender MCP'"
echo
echo "2. In Blender, connect to MCP:"
echo "   - Press N to open sidebar"
echo "   - Go to 'BlenderMCP' tab"
echo "   - Click 'Connect to Claude'"
echo
echo "3. Open VS Code in this directory:"
echo "   code ."
echo
echo "4. Start the MCP server (Ctrl+Shift+B in VS Code)"
echo "   Or run: uvx blender-mcp"
echo
echo "See TEAM_SETUP.md for full documentation."
