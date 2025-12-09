#!/usr/bin/env python3
"""
Test the MCP server connection by calling it directly
This demonstrates how we can integrate with GitHub Copilot
"""

import subprocess
import json
import sys


def test_mcp_tools():
    """Test various MCP tools to verify functionality"""

    print("🧪 Testing MCP Server Connection")
    print("=" * 40)

    # Test 1: Get scene info using our socket approach
    print("\n📋 Test 1: Getting scene info...")
    try:
        import socket
        import json

        command = {
            "type": "get_scene_info",
            "params": {}
        }

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(("127.0.0.1", 9876))
            s.sendall(json.dumps(command).encode('utf-8'))
            response = s.recv(4096)
            result = json.loads(response.decode('utf-8'))

            if result.get("status") == "success":
                scene_info = result.get("result", {})
                print(f"✅ Scene: {scene_info.get('name', 'Unknown')}")
                print(f"✅ Objects: {scene_info.get('object_count', 0)}")
                print("✅ MCP server is working correctly!")
            else:
                print(
                    f"⚠️  Server responded but with status: {result.get('status')}")

    except Exception as e:
        print(f"❌ Error testing MCP: {e}")


def create_copilot_bridge():
    """Create a bridge between GitHub Copilot and MCP tools"""

    print("\n🔌 Creating GitHub Copilot Bridge")
    print("=" * 40)

    # We can create functions that wrap MCP calls
    # and make them available to Copilot

    bridge_functions = {
        "get_blender_scene": "Get current Blender scene information",
        "create_object": "Create 3D objects in Blender",
        "apply_material": "Apply materials and textures",
        "download_asset": "Download assets from PolyHaven/Sketchfab",
        "generate_3d_model": "Generate 3D models with AI",
        "capture_screenshot": "Take viewport screenshots"
    }

    print("🛠️  Available bridge functions:")
    for func, desc in bridge_functions.items():
        print(f"  • {func}(): {desc}")

    return bridge_functions


if __name__ == "__main__":
    test_mcp_tools()
    create_copilot_bridge()

    print("\n🎯 Next Steps for GitHub Copilot Integration:")
    print("1. Create Python functions that wrap MCP tool calls")
    print("2. Use subprocess to call 'uvx blender-mcp' with specific tools")
    print("3. Parse responses and format for Copilot")
    print("4. Build natural language interface on top")
