"""
Analyze the tillageSimulation2.blend scene and provide detailed information.
This script will be executed in Blender to get comprehensive scene information.
"""
import bpy

# Execute the scene analysis code directly
scene_analysis_code = '''
import bpy

print("=" * 60)
print("TILLAGE SIMULATION SCENE ANALYSIS")
print("=" * 60)

# Blender version
print(f"Blender Version: {bpy.app.version_string}")
print()

# Scene information
scene = bpy.context.scene
print(f"Scene Name: {scene.name}")
print(f"Frame Range: {scene.frame_start} - {scene.frame_end}")
print(f"Current Frame: {scene.frame_current}")
print()

# Objects in scene
print("OBJECTS IN SCENE:")
print("-" * 30)
if bpy.data.objects:
    for obj in bpy.data.objects:
        print(f"  • {obj.name}")
        print(f"    Type: {obj.type}")
        print(f"    Location: {obj.location}")
        print(f"    Scale: {obj.scale}")
        if obj.data:
            print(f"    Data: {obj.data.name}")
        print()
else:
    print("  No objects in scene")

# Materials
print("MATERIALS:")
print("-" * 30)
if bpy.data.materials:
    for mat in bpy.data.materials:
        print(f"  • {mat.name}")
        if mat.use_nodes:
            print(f"    Uses nodes: Yes")
        else:
            print(f"    Uses nodes: No")
        print()
else:
    print("  No materials in scene")

# Check for specific tillage-related objects
print("TILLAGE-RELATED OBJECTS:")
print("-" * 30)
tillage_keywords = ['plow', 'tillage', 'soil', 'disc', 'blade', 'furrow']
tillage_objects = []
for obj in bpy.data.objects:
    obj_name_lower = obj.name.lower()
    for keyword in tillage_keywords:
        if keyword in obj_name_lower:
            tillage_objects.append(obj)
            break

if tillage_objects:
    for obj in tillage_objects:
        print(f"  • {obj.name} ({obj.type})")
        print(f"    Location: {obj.location}")
        print(f"    Scale: {obj.scale}")
        print()
else:
    print("  No obvious tillage-related objects found")

print("=" * 60)
print("Analysis complete!")
print("=" * 60)
'''

# Execute the analysis
exec(scene_analysis_code)


