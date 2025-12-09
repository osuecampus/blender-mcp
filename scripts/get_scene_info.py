"""
Get detailed information about the current Blender scene.
Execute this script to see what objects, materials, and other elements are in your scene.
"""
import bpy

print("=" * 60)
print("BLENDER SCENE INFORMATION")
print("=" * 60)

# Blender version
print(f"Blender Version: {bpy.app.version_string}")
print(f"Blender Build: {bpy.app.build_platform}")
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
        print(f"    Rotation: {obj.rotation_euler}")
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

# Meshes
print("MESHES:")
print("-" * 30)
if bpy.data.meshes:
    for mesh in bpy.data.meshes:
        print(f"  • {mesh.name}")
        print(f"    Vertices: {len(mesh.vertices)}")
        print(f"    Faces: {len(mesh.polygons)}")
        print(f"    Edges: {len(mesh.edges)}")
        print()
else:
    print("  No meshes in scene")

# Cameras
print("CAMERAS:")
print("-" * 30)
cameras = [obj for obj in bpy.data.objects if obj.type == 'CAMERA']
if cameras:
    for cam in cameras:
        print(f"  • {cam.name}")
        print(f"    Location: {cam.location}")
        print(f"    Type: {cam.data.type}")
        print()
else:
    print("  No cameras in scene")

# Lights
print("LIGHTS:")
print("-" * 30)
lights = [obj for obj in bpy.data.objects if obj.type == 'LIGHT']
if lights:
    for light in lights:
        print(f"  • {light.name}")
        print(f"    Type: {light.data.type}")
        print(f"    Energy: {light.data.energy}")
        print(f"    Location: {light.location}")
        print()
else:
    print("  No lights in scene")

print("=" * 60)
print("Scene analysis complete!")
print("=" * 60)


