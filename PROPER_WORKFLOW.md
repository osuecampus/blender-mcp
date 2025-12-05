# BlenderMCP Proper Workflow Guide

## Critical Understanding

**The MCP connection works through a socket on port 9876 to the Blender addon.**

This is NOT about running Python scripts locally - it's about sending commands to Blender through the MCP protocol.

## Architecture

```
┌─────────────────┐     Socket (9876)     ┌─────────────────────┐
│  MCP Server     │◄────────────────────►│  Blender Addon      │
│  (server.py)    │                       │  (addon.py)         │
└─────────────────┘                       └─────────────────────┘
        │                                          │
        │ MCP Tools                               │ Blender Python API
        ▼                                          ▼
┌─────────────────┐                       ┌─────────────────────┐
│  Copilot/Claude │                       │  Blender Scene      │
└─────────────────┘                       └─────────────────────┘
```

## Available MCP Tools

### Core Tools (Always Available)

1. **get_scene_info** - Get scene name, object count, and list of objects with locations
2. **get_object_info(object_name)** - Get detailed info: location, rotation, scale, materials, mesh data, world bounding box
3. **get_viewport_screenshot(max_size)** - Capture viewport image for visual verification
4. **execute_blender_code(code)** - Execute Python code in Blender

### Asset Integration Tools (Require Addon Settings)

5. **get_polyhaven_status** - Check if PolyHaven is enabled
6. **get_polyhaven_categories(asset_type)** - List categories (hdris, textures, models)
7. **search_polyhaven_assets(asset_type, categories)** - Search assets
8. **download_polyhaven_asset(asset_id, asset_type, resolution)** - Download and import
9. **set_texture(object_name, texture_id)** - Apply texture to object

10. **get_sketchfab_status** - Check if Sketchfab is enabled
11. **search_sketchfab_models(query, categories, count)** - Search models
12. **download_sketchfab_model(uid)** - Download and import model

13. **get_hyper3d_status** - Check if Hyper3D is enabled
14. **generate_hyper3d_model_via_text(text_prompt, bbox_condition)** - Generate from text
15. **generate_hyper3d_model_via_images(input_image_paths/urls)** - Generate from images
16. **poll_rodin_job_status(subscription_key/request_id)** - Check generation status
17. **import_generated_asset(name, task_uuid/request_id)** - Import generated model

## Proper Workflow for Any Modeling Task

### Step 1: Always Start With Scene Info

```python
# Get current state before doing anything
scene_info = get_scene_info()
# Understand what objects exist, their positions, types
```

### Step 2: Get Detailed Info on Relevant Objects

```python
# For any object you need to work with
obj_info = get_object_info("ObjectName")
# This gives you: location, rotation, scale, materials, mesh data, world_bounding_box
```

### Step 3: Execute Blender Code

When using `execute_blender_code`, the code runs in Blender's context:

```python
code = """
import bpy

# Your Blender operations here
# Use print() to output information back
obj = bpy.data.objects.get('ObjectName')
print(f'Object found: {obj is not None}')
"""
result = execute_blender_code(code)
# result contains the printed output
```

### Step 4: ALWAYS Verify Results

**CRITICAL: After ANY modeling operation, verify the result!**

1. **For visual verification**: Use `get_viewport_screenshot()`
2. **For data verification**: Use `get_object_info()` on affected objects
3. **For geometry nodes**: Query the node tree through `execute_blender_code`

### Step 5: For Geometry Nodes Specifically

Geometry nodes require extra care. Always:

1. **Check for orphaned nodes** after operations
2. **Verify links are connected properly**
3. **Use meaningful node names**

```python
code = """
import bpy

obj = bpy.data.objects.get('ObjectName')
for mod in obj.modifiers:
    if mod.type == 'NODES' and mod.node_group:
        ng = mod.node_group
        
        # Check for orphaned nodes (nodes with no input/output connections)
        orphaned = []
        for node in ng.nodes:
            if node.bl_idname in ['NodeGroupInput', 'NodeGroupOutput']:
                continue  # These are special
            has_input = any(link.to_node == node for link in ng.links)
            has_output = any(link.from_node == node for link in ng.links)
            if not has_input and not has_output:
                orphaned.append(node.name)
        
        print(f'Total nodes: {len(ng.nodes)}')
        print(f'Total links: {len(ng.links)}')
        print(f'Orphaned nodes: {orphaned}')
        
        # List all nodes with their connections
        for node in ng.nodes:
            inputs = [l.from_node.name for l in ng.links if l.to_node == node]
            outputs = [l.to_node.name for l in ng.links if l.from_node == node]
            print(f'{node.name}: inputs={inputs}, outputs={outputs}')
"""
```

## Common Mistakes to Avoid

1. **Not verifying after changes** - Always take a screenshot or query object info
2. **Working blind** - Always get scene_info before making changes
3. **Not checking for existing objects** - Query before creating to avoid duplicates
4. **Ignoring error output** - The execute_blender_code result contains print output AND errors
5. **Large code blocks** - Break complex operations into smaller verified steps
6. **Not tracking geometry node state** - Always query node tree after modifications

## Debugging Geometry Nodes

```python
def diagnose_geometry_nodes(object_name):
    code = f"""
import bpy

obj = bpy.data.objects.get('{object_name}')
if not obj:
    print('Object not found')
else:
    gn_mods = [m for m in obj.modifiers if m.type == 'NODES']
    print(f'Geometry Nodes modifiers: {{len(gn_mods)}}')
    
    for mod in gn_mods:
        if not mod.node_group:
            print(f'  {{mod.name}}: NO NODE GROUP (broken!)')
            continue
            
        ng = mod.node_group
        print(f'  {{mod.name}}: {{ng.name}}')
        print(f'    Nodes: {{len(ng.nodes)}}')
        print(f'    Links: {{len(ng.links)}}')
        
        # Find group input/output
        group_input = None
        group_output = None
        for node in ng.nodes:
            if node.bl_idname == 'NodeGroupInput':
                group_input = node
            elif node.bl_idname == 'NodeGroupOutput':
                group_output = node
        
        if group_input:
            out_links = [l for l in ng.links if l.from_node == group_input]
            print(f'    Group Input -> {{[l.to_node.name for l in out_links]}}')
        
        if group_output:
            in_links = [l for l in ng.links if l.to_node == group_output]
            print(f'    Group Output <- {{[l.from_node.name for l in in_links]}}')
"""
    return execute_blender_code(code)
```

## Working With the Copilot Bridge

The `copilot_bridge.py` provides a Python class for direct socket communication:

```python
from copilot_bridge import BlenderCopilotBridge

bridge = BlenderCopilotBridge()

# Get scene info
scene = bridge.get_scene_info()

# Get object info
obj = bridge.get_object_info("ObjectName")

# Execute code
result = bridge.execute_blender_code("""
import bpy
# Your code here
""")

# Capture screenshot
screenshot_path = bridge.capture_viewport_screenshot()
```

## Summary

1. **Always query before modifying**
2. **Always verify after modifying**
3. **Take screenshots for complex visual work**
4. **For geometry nodes: track nodes and links explicitly**
5. **Break complex operations into small, verified steps**
