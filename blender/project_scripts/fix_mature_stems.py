#!/usr/bin/env python3
"""Fix mature stems collection object transforms for proper instancing."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.copilot_bridge import BlenderCopilotBridge

bridge = BlenderCopilotBridge()

code = """
import bpy

# The issue: stem objects have locations far from origin
# Solution: Move origins to world origin and apply transforms

coll = bpy.data.collections.get("mature stems")
if coll:
    print("=== Fixing stem object transforms ===")
    for obj in coll.objects:
        print(f"Before: {obj.name} at {tuple(round(v, 2) for v in obj.location)}")
        
        # Store original location
        old_loc = obj.location.copy()
        
        # Select and make active
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        
        # Move geometry to compensate for origin offset
        if obj.type == "MESH":
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.transform.translate(value=(-old_loc.x, -old_loc.y, -old_loc.z))
            bpy.ops.object.mode_set(mode="OBJECT")
            
            # Now set location to origin
            obj.location = (0, 0, 0)
            
            print(f"After: {obj.name} at {tuple(round(v, 2) for v in obj.location)}")
        
        obj.select_set(False)

    print()
    print("Done! Stem objects now have geometry centered at world origin.")
else:
    print("Collection 'mature stems' not found")
"""

result = bridge.execute_blender_code(code)
print(result)
