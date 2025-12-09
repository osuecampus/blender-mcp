#!/bin/bash
# BlenderMCP Quick Setup Script for Linux
# This script sets up the BlenderMCP environment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🎮 BlenderMCP Setup Script"
echo "=========================="
echo ""

# Check for uv package manager
if ! command -v uv &> /dev/null; then
    echo "❌ 'uv' package manager not found."
    echo "   Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
echo "✅ uv package manager found"

# Check for Blender
BLENDER_CMD=""
if command -v blender &> /dev/null; then
    BLENDER_CMD="blender"
elif flatpak list 2>/dev/null | grep -q "org.blender.Blender"; then
    BLENDER_CMD="flatpak run org.blender.Blender"
elif snap list 2>/dev/null | grep -q "blender"; then
    BLENDER_CMD="snap run blender"
fi

if [ -n "$BLENDER_CMD" ]; then
    echo "✅ Blender found: $BLENDER_CMD"
else
    echo "⚠️  Blender not found in PATH, snap, or flatpak"
    echo "   Please install Blender from https://www.blender.org/download/"
fi

# Sync dependencies
echo ""
echo "📦 Syncing dependencies with uv..."
uv sync

# Verify installation
echo ""
echo "🔍 Verifying installation..."
if .venv/bin/python -c "from blender_mcp.server import mcp; print('✅ MCP Server module loaded')" 2>/dev/null; then
    echo ""
else
    echo "❌ Failed to load MCP Server module"
    exit 1
fi

# Create addon symlink info
ADDON_PATH="$SCRIPT_DIR/addon.py"
echo ""
echo "=========================="
echo "📋 SETUP COMPLETE!"
echo "=========================="
echo ""
echo "NEXT STEPS:"
echo ""
echo "1️⃣  INSTALL BLENDER ADDON:"
echo "   • Open Blender"
echo "   • Go to Edit > Preferences > Add-ons"
echo "   • Click 'Install...' and select:"
echo "     $ADDON_PATH"
echo "   • Enable the 'Blender MCP' addon"
echo ""
echo "2️⃣  START THE ADDON IN BLENDER:"
echo "   • In 3D View, press 'N' to open sidebar"
echo "   • Go to 'BlenderMCP' tab"
echo "   • Click 'Start Server'"
echo "   • (Optional) Enable PolyHaven, Sketchfab, Hyper3D integrations"
echo ""
echo "3️⃣  START MCP SERVER (choose one method):"
echo ""
echo "   Method A - Global (recommended for Claude Desktop/Cursor):"
echo "   $ uvx blender-mcp"
echo ""
echo "   Method B - From this project:"
echo "   $ cd $SCRIPT_DIR"
echo "   $ source .venv/bin/activate"
echo "   $ blender-mcp"
echo ""
echo "4️⃣  FOR VS CODE COPILOT:"
echo "   • MCP config is in .vscode/mcp.json"
echo "   • Reload VS Code window to activate"
echo ""
echo "=========================="
echo ""
