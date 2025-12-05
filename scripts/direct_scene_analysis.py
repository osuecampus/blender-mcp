"""
Direct scene analysis script for tillageSimulation2.blend
This script will be executed directly in Blender to get comprehensive scene information.
"""

# This is the code that will be executed in Blender
blender_code = '''
import bpy

print("=" * 60)
print("TILLAGE SIMULATION SCENE ANALYSIS")
print("=" * 60)

# Basic scene info
print(f"Blender Version: {bpy.app.version_string}")
print(f"Scene Name: {bpy.context.scene.name}")
print(f"Current Frame: {bpy.context.scene.frame_current}")
print()

# Objects analysis
print("OBJECTS IN SCENE:")
print("-" * 30)
if bpy.data.objects:
    for i, obj in enumerate(bpy.data.objects, 1):
        print(f"{i:2d}. {obj.name}")
        print(f"    Type: {obj.type}")
        print(f"    Location: ({obj.location.x:.2f}, {obj.location.y:.2f}, {obj.location.z:.2f})")
        print(f"    Scale: ({obj.scale.x:.2f}, {obj.scale.y:.2f}, {obj.scale.z:.2f})")
        if obj.data:
            print(f"    Data: {obj.data.name}")
        print()
else:
    print("  No objects in scene")

# Materials analysis
print("MATERIALS:")
print("-" * 30)
if bpy.data.materials:
    for i, mat in enumerate(bpy.data.materials, 1):
        print(f"{i:2d}. {mat.name}")
        print(f"    Uses nodes: {mat.use_nodes}")
        if mat.use_nodes and mat.node_tree:
            print(f"    Node tree: {mat.node_tree.name}")
        print()
else:
    print("  No materials in scene")

# Check for tillage-related objects
print("TILLAGE-RELATED OBJECTS:")
print("-" * 30)
tillage_keywords = ['plow', 'tillage', 'soil', 'disc', 'blade', 'furrow', 'till', 'cultivator']
tillage_objects = []

for obj in bpy.data.objects:
    obj_name_lower = obj.name.lower()
    for keyword in tillage_keywords:
        if keyword in obj_name_lower:
            tillage_objects.append((obj, keyword))
            break

if tillage_objects:
    for obj, keyword in tillage_objects:
        print(f"  • {obj.name} ({obj.type}) - matched keyword: '{keyword}'")
        print(f"    Location: ({obj.location.x:.2f}, {obj.location.y:.2f}, {obj.location.z:.2f})")
        print(f"    Scale: ({obj.scale.x:.2f}, {obj.scale.y:.2f}, {obj.scale.z:.2f})")
        print()
else:
    print("  No obvious tillage-related objects found")

# Camera and lighting info
cameras = [obj for obj in bpy.data.objects if obj.type == 'CAMERA']
lights = [obj for obj in bpy.data.objects if obj.type == 'LIGHT']

print("CAMERAS:")
print("-" * 30)
if cameras:
    for cam in cameras:
        print(f"  • {cam.name} at ({cam.location.x:.2f}, {cam.location.y:.2f}, {cam.location.z:.2f})")
        print(f"    Type: {cam.data.type}")
else:
    print("  No cameras in scene")

print()
print("LIGHTS:")
print("-" * 30)
if lights:
    for light in lights:
        print(f"  • {light.name} ({light.data.type})")
        print(f"    Location: ({light.location.x:.2f}, {light.location.y:.2f}, {light.location.z:.2f})")
        print(f"    Energy: {light.data.energy}")
else:
    print("  No lights in scene")

print("=" * 60)
print("SCENE ANALYSIS COMPLETE!")
print("=" * 60)
'''

# Execute the code
exec(blender_code)


