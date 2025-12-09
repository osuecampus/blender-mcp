#!/usr/bin/env python3
"""Analyze the mature stems geometry node setup."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.copilot_bridge import BlenderCopilotBridge

bridge = BlenderCopilotBridge()

code = """
import bpy

# Find objects using mature stems geometry nodes
print("=== Objects with mature stems modifier ===")
for obj in bpy.data.objects:
    for mod in obj.modifiers:
        if mod.type == "NODES" and mod.node_group:
            if mod.node_group.name == "mature stems":
                print(f"Object: {obj.name}")
                print(f"  World Location: {tuple(round(v, 2) for v in obj.location)}")
                
                # Check for vertex groups
                if hasattr(obj.data, "vertices"):
                    vg = obj.vertex_groups.get("mature spots")
                    if vg:
                        print(f"  Vertex Group: mature spots (index {vg.index})")
                        # Get vertices in group
                        verts_in_group = []
                        for v in obj.data.vertices:
                            for g in v.groups:
                                if g.group == vg.index and g.weight > 0.5:
                                    world_pos = obj.matrix_world @ v.co
                                    verts_in_group.append((v.index, tuple(round(c, 2) for c in v.co), tuple(round(c, 2) for c in world_pos)))
                        print(f"  Vertices in group: {len(verts_in_group)}")
                        for idx, local, world in verts_in_group[:10]:
                            print(f"    Vert {idx}: local={local} world={world}")
                    else:
                        print("  No vertex group named 'mature spots'")

# Check mature stems collection
coll = bpy.data.collections.get("mature stems")
if coll:
    print()
    print("=== Collection: mature stems ===")
    for obj in coll.objects:
        print(f"  {obj.name}: location={tuple(round(v, 2) for v in obj.location)}")
        # Check if origin is at base
        if hasattr(obj.data, "vertices") and len(obj.data.vertices) > 0:
            verts = [v.co for v in obj.data.vertices]
            min_z = min(v.z for v in verts)
            max_z = max(v.z for v in verts)
            print(f"    Geometry Z range: {min_z:.2f} to {max_z:.2f}")
"""

result = bridge.execute_blender_code(code)
print(result)
