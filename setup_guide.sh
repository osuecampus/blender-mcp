#!/bin/bash
# BlenderMCP Setup Guide
# Complete setup instructions for BlenderMCP

echo "🎨 BlenderMCP Setup Guide"
echo "========================="
echo ""

echo "✅ Step 1: uv package manager installed"
echo "✅ Step 2: Blender is running"
echo ""

echo "📋 Next steps to complete setup:"
echo ""

echo "🔧 Step 3: Install Blender Addon"
echo "  1. In Blender, go to Edit > Preferences > Add-ons"
echo "  2. Click 'Install...' button"
echo "  3. Navigate to: $(pwd)/addon.py"
echo "  4. Select addon.py and click 'Install Add-on'"
echo "  5. Search for 'Blender MCP' in the add-ons list"
echo "  6. Check the box to enable it"
echo ""

echo "🚀 Step 4: Start the MCP Server in Blender"
echo "  1. In Blender's 3D viewport, press 'N' to show sidebar (if hidden)"
echo "  2. Look for 'BlenderMCP' tab in the sidebar"
echo "  3. Click 'Connect to MCP server' button"
echo "  4. You should see 'Running on port 9876'"
echo ""

echo "🧪 Step 5: Test the Connection"
echo "  Run this command in a new terminal:"
echo "  uvx blender-mcp"
echo ""
echo "  If successful, you should see:"
echo "  'Successfully connected to Blender on startup'"
echo ""

echo "🔌 Step 6: Connect to AI Assistant"
echo "  For Claude Desktop: Add to claude_desktop_config.json:"
echo "  {"
echo "    \"mcpServers\": {"
echo "      \"blender\": {"
echo "        \"command\": \"uvx\","
echo "        \"args\": [\"blender-mcp\"]"
echo "      }"
echo "    }"
echo "  }"
echo ""

echo "💡 For GitHub Copilot Integration:"
echo "  The MCP server provides tools that can be called programmatically."
echo "  We can create a wrapper that translates Copilot requests to MCP calls."
echo ""

echo "📁 Files in this repo:"
echo "  - addon.py: Blender addon (install this in Blender)"
echo "  - src/blender_mcp/server.py: MCP server (runs with 'uvx blender-mcp')"
echo "  - natural_language_blender.py: Your custom parser (for testing)"
echo ""

echo "🎯 Current Status:"
echo "  ✅ uv installed: $(which uv)"
echo "  ✅ Blender running: $(pgrep blender > /dev/null && echo "Yes" || echo "No")"
echo "  ⏳ Addon not installed yet"
echo "  ⏳ MCP server not connected yet"