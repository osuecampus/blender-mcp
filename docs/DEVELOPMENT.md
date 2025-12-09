# BlenderMCP Development Guide

> **Fork Note**: This is a fork of [ahujasid/blender-mcp](https://github.com/ahujasid/blender-mcp) with additional tooling for GitHub Copilot integration and team development workflows.

## Architecture

```
┌─────────────────┐     Socket (9876)     ┌─────────────────────┐
│  MCP Server     │◄────────────────────► │  Blender Addon      │
│  (server.py)    │                       │  (addon.py)         │
└─────────────────┘                       └─────────────────────┘
        │                                          │
        │ MCP Tools                                │ Blender Python API
        ▼                                          ▼
┌─────────────────┐                       ┌─────────────────────┐
│  Copilot/Claude │                       │  Blender Scene      │
└─────────────────┘                       └─────────────────────┘
```

## Quick Start

### Prerequisites

- **Blender 3.0+** (5.0+ recommended)
- **Python 3.10+**
- **VS Code** with GitHub Copilot
- **uv** package manager

### Setup

```bash
# Clone and setup
git clone https://github.com/nickHarperOSU/blender-mcp.git
cd blender-mcp
./setup.sh
```

Or manually:

```bash
uv venv
source .venv/bin/activate  # Linux/Mac
uv pip install -e .
```

### Install Blender Addon

1. Open Blender → **Edit > Preferences > Add-ons**
2. Click **Install...** and select `addon.py`
3. Enable **"Interface: Blender MCP"**

### Connect Blender

1. In Blender, press `N` to open the sidebar
2. Find the **"BlenderMCP"** tab
3. Click **"Connect to Claude"** (listens on `localhost:9876`)

### Start the MCP Server

```bash
uvx blender-mcp
```

Or in VS Code: **Ctrl+Shift+B** to run the build task.

---

## Available MCP Tools

### Core Tools (Always Available)

| Tool | Description |
|------|-------------|
| `get_scene_info` | Scene name, object count, and objects with locations |
| `get_object_info(name)` | Location, rotation, scale, materials, mesh data, bounding box |
| `get_viewport_screenshot(max_size)` | Capture viewport image |
| `execute_blender_code(code)` | Execute Python code in Blender |

### Asset Integration (Require Addon Settings)

| Tool | Description |
|------|-------------|
| `get_polyhaven_status` | Check if PolyHaven is enabled |
| `search_polyhaven_assets(type, categories)` | Search assets |
| `download_polyhaven_asset(id, type, resolution)` | Download and import |
| `get_sketchfab_status` | Check if Sketchfab is enabled |
| `search_sketchfab_models(query, categories, count)` | Search models |
| `download_sketchfab_model(uid)` | Download and import |
| `get_hyper3d_status` | Check if Hyper3D is enabled |
| `generate_hyper3d_model_via_text(prompt)` | Generate from text |
| `poll_rodin_job_status(key)` | Check generation status |
| `import_generated_asset(name, uuid)` | Import generated model |

---

## Using the Copilot Bridge

The `tools/copilot_bridge.py` provides a Python API for direct communication:

```python
from tools.copilot_bridge import BlenderCopilotBridge

bridge = BlenderCopilotBridge()

# Get scene info
scene = bridge.get_scene_info()

# Get object info
obj = bridge.get_object_info("Cube")

# Execute Blender code
result = bridge.execute_blender_code("""
import bpy
print(f"Scene has {len(bpy.data.objects)} objects")
""")

# Capture screenshot
screenshot_path = bridge.capture_viewport_screenshot()
```

---

## Project Tools

| Tool | Purpose |
|------|---------|
| `tools/copilot_bridge.py` | Python API to communicate with Blender |
| `tools/texture_baker_v2.py` | Bake procedural materials to textures |
| `tools/geonode_helper.py` | Analyze and organize geometry nodes |
| `tools/scene_analyzer.py` | Document scene structure |
| `tools/material_helper.py` | Material utilities |

### Texture Baker

```python
from tools.texture_baker_v2 import TextureBaker

baker = TextureBaker()
baker.list_all_materials()  # Always list first
result = baker.bake_and_replace(
    material_name="Material Name",
    object_name="Object Name",
    resolution=2048
)
```

### Scene Analyzer

```python
from tools.scene_analyzer import analyze_scene, quick_geonodes_summary

# Quick geometry nodes summary
print(quick_geonodes_summary())

# Full analysis
report = analyze_scene()
print(report)
```

### Geometry Node Helper

```python
from tools.geonode_helper import (
    frame_new_nodes,
    analyze_geonode_group,
    validate_geonode_connections
)

# Frame unorganized nodes
frame_new_nodes("NodeGroup", "Feature Name")

# Analyze node group
analysis = analyze_geonode_group("NodeGroup")

# Validate connections
validation = validate_geonode_connections("NodeGroup")
```

---

## Workflow Best Practices

### 1. Always Query Before Modifying

```python
scene_info = bridge.get_scene_info()
obj_info = bridge.get_object_info("ObjectName")
```

### 2. Always Verify After Modifying

```python
# Visual verification
screenshot = bridge.capture_viewport_screenshot()

# Data verification
updated_info = bridge.get_object_info("ObjectName")
```

### 3. Break Complex Operations Into Steps

Don't write one giant code block. Execute, verify, then continue.

### 4. For Geometry Nodes: Track State Explicitly

```python
code = """
import bpy
obj = bpy.data.objects.get('ObjectName')
for mod in obj.modifiers:
    if mod.type == 'NODES' and mod.node_group:
        ng = mod.node_group
        print(f'Nodes: {len(ng.nodes)}, Links: {len(ng.links)}')
"""
bridge.execute_blender_code(code)
```

---

## Development Workflow

### Tool Development Cycle

```
1. Encounter a repetitive task in Blender
2. Build a Python tool to automate it
3. Test via copilot_bridge.py
4. Document lessons learned in docs/BLENDER_API_LESSONS.md
5. Update copilot-instructions.md
6. Commit and share
```

### Creating New Tools

```python
#!/usr/bin/env python3
"""
Tool Name - Brief description

Usage:
    from tools.tool_name import main_function
    result = main_function(args)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.copilot_bridge import BlenderCopilotBridge

def main_function():
    bridge = BlenderCopilotBridge()
    code = """
import bpy
# Your Blender code here
"""
    return bridge.execute_blender_code(code)

if __name__ == "__main__":
    main_function()
```

---

## Troubleshooting

### "Connection refused" error

- Ensure Blender is open
- Click "Connect to Claude" in Blender's sidebar
- Check that port 9876 is not in use

### "Material not found" when baking

- Run `list_all_materials()` first
- Use EXACT material name (case-sensitive)
- Verify object has UV coordinates

### Geometry nodes not updating

- Check if using shader nodes (may freeze after first evaluation)
- Consider using drivers instead
- Test incrementally after each change

---

## Resources

- [Blender Python API](https://docs.blender.org/api/current/)
- [MCP Specification](https://modelcontextprotocol.io/)
- [Upstream Project](https://github.com/ahujasid/blender-mcp)
- [Discord Community](https://discord.gg/z5apgR8TFU)
