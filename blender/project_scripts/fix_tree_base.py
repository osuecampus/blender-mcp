#!/usr/bin/env python3
"""Shift tree geometry so base is at Z=0."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.copilot_bridge import BlenderCopilotBridge

bridge = BlenderCopilotBridge()

code = """
import bpy

coll = bpy.data.collections.get("mature stems")
if coll:
    print("=== Moving tree geometry so base is at Z=0 ===")
    for obj in coll.objects:
        if obj.type == "MESH" and len(obj.data.vertices) > 0:
            verts = [v.co for v in obj.data.vertices]
            min_z = min(v.z for v in verts)
            
            if abs(min_z) > 0.001:  # Only if not already at 0
                print(f"{obj.name}: shifting geometry up by {-min_z:.3f}")
                
                # Select and edit
                bpy.ops.object.select_all(action='DESELECT')
                bpy.context.view_layer.objects.active = obj
                obj.select_set(True)
                
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.transform.translate(value=(0, 0, -min_z))
                bpy.ops.object.mode_set(mode='OBJECT')
                
                # Verify
                new_min_z = min(v.co.z for v in obj.data.vertices)
                print(f"  New min Z: {new_min_z:.3f}")
            else:
                print(f"{obj.name}: already at Z=0")

    print()
    print("Done! Tree bases now at Z=0.")
"""

result = bridge.execute_blender_code(code)
print(result)
