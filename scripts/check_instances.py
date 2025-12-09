#!/usr/bin/env python3
"""Check mature stems instance positions and tree geometry."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.copilot_bridge import BlenderCopilotBridge

bridge = BlenderCopilotBridge()

code = """
import bpy

# Get the vertex group positions (where instances should appear)
obj = bpy.data.objects.get("mature soil")
if obj:
    print("=== Mature Soil Object ===")
    print(f"World Location: {tuple(round(v, 3) for v in obj.location)}")
    
    vg = obj.vertex_groups.get("mature spots")
    if vg:
        verts_in_group = []
        for v in obj.data.vertices:
            for g in v.groups:
                if g.group == vg.index and g.weight > 0.5:
                    world_pos = obj.matrix_world @ v.co
                    verts_in_group.append(tuple(round(c, 3) for c in world_pos))
        
        print(f"Instance positions (first 5 of {len(verts_in_group)}):")
        for i, pos in enumerate(verts_in_group[:5]):
            print(f"  {i+1}. {pos}")

# Check tree geometry offsets
print()
print("=== Tree geometry check ===")
coll = bpy.data.collections.get("mature stems")
if coll:
    for obj in coll.objects:
        if obj.type == "MESH" and len(obj.data.vertices) > 0:
            verts = [v.co for v in obj.data.vertices]
            min_z = min(v.z for v in verts)
            max_z = max(v.z for v in verts)
            height = max_z - min_z
            print(f"{obj.name}: Z range {min_z:.2f} to {max_z:.2f} (height: {height:.2f})")
            print(f"  At 0.01 scale: height = {height * 0.01:.3f} units")
"""

result = bridge.execute_blender_code(code)
print(result)
