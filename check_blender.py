#!/usr/bin/env python3
"""
BlenderMCP Connection Test & Demo
Run this script to test the connection to Blender and see available capabilities.
"""

import sys
import json
sys.path.insert(0, '/home/nick/GIT/blender-mcp')

from copilot_bridge import BlenderCopilotBridge

def test_connection():
    """Test the connection to Blender and display scene info"""
    print("🔗 Testing connection to Blender...")
    print("=" * 50)
    
    try:
        bridge = BlenderCopilotBridge()
        
        # Test 1: Get scene info
        print("\n📊 Scene Information:")
        scene_info = bridge.get_scene_info()
        print(f"   Scene name: {scene_info.get('name', 'Unknown')}")
        print(f"   Object count: {scene_info.get('object_count', 0)}")
        
        objects = scene_info.get('objects', [])
        if objects:
            print(f"\n   Objects in scene:")
            for obj in objects[:10]:  # Show first 10
                loc = obj.get('location', [0, 0, 0])
                print(f"   • {obj['name']} ({obj['type']}) at ({loc[0]}, {loc[1]}, {loc[2]})")
        
        # Test 2: Check integrations
        print("\n🔌 Integration Status:")
        try:
            polyhaven = bridge.get_polyhaven_status()
            print(f"   PolyHaven: {'✅ Enabled' if polyhaven.get('enabled') else '❌ Disabled'}")
        except:
            print("   PolyHaven: ❌ Disabled or unavailable")
            
        try:
            sketchfab = bridge.get_sketchfab_status()
            print(f"   Sketchfab: {'✅ Enabled' if sketchfab.get('enabled') else '❌ Disabled'}")
        except:
            print("   Sketchfab: ❌ Disabled or unavailable")
            
        try:
            hyper3d = bridge.get_hyper3d_status()
            print(f"   Hyper3D:   {'✅ Enabled' if hyper3d.get('enabled') else '❌ Disabled'}")
        except:
            print("   Hyper3D:   ❌ Disabled or unavailable")
        
        print("\n" + "=" * 50)
        print("✅ Connection successful! BlenderMCP is ready.")
        print("\n💡 Quick Examples:")
        print("""
# Create a cube
from copilot_bridge import BlenderCopilotBridge
bridge = BlenderCopilotBridge()
bridge.execute_blender_code('''
import bpy
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 1), size=2)
''')

# Create a sphere with color
bridge.execute_blender_code('''
import bpy
bpy.ops.mesh.primitive_uv_sphere_add(location=(3, 0, 1), radius=1)
obj = bpy.context.active_object
mat = bpy.data.materials.new(name="Red")
mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (1, 0, 0, 1)
obj.data.materials.append(mat)
''')

# Take a screenshot
screenshot = bridge.capture_viewport_screenshot()
print(f"Screenshot saved to: {screenshot}")
""")
        return True
        
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Make sure Blender is running")
        print("   2. In Blender, press 'N' to open sidebar")
        print("   3. Go to 'BlenderMCP' tab")
        print("   4. Click 'Start Server'")
        print("   5. Look for 'Server started on localhost:9876' message")
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
