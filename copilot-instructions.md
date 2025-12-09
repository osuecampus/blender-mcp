# BlenderMCP Copilot Instructions

## Overview

BlenderMCP is a Model Context Protocol (MCP) server that provides sophisticated 3D modeling capabilities through Blender integration. This document outlines the established workflow, tools, and best practices for working with the BlenderMCP system.

## System Architecture

### Core Components

- **BlenderMCP Server**: `src/blender_mcp/server.py` - 17 sophisticated tools for 3D modeling
- **Copilot Bridge**: `copilot_bridge.py` - Python API bridge for GitHub Copilot integration
- **Blender Integration**: Socket communication to Blender addon on port 9876
- **Python Environment**: mcp_pylance tools for direct code execution

### Key Files

- `src/blender_mcp/server.py` - Main MCP server with custom exception handling
- `copilot_bridge.py` - Bridge API with methods like `execute_blender_code()`, `capture_viewport_screenshot()`
- `pyproject.toml` - Project configuration
- `README.md` - Setup instructions

## Established Workflow

### 1. Environment Setup

Always ensure BlenderMCP server is running:

```bash
uvx blender-mcp
```

The server runs on port 9876 with Blender addon integration.

### 2. Python Execution Pattern

**CRITICAL**: Use `mcp_pylance_mcp_s_pylanceRunCodeSnippet` for all Python code execution. This tool:

- Executes Python directly without shell quoting issues
- Provides clean, properly formatted output
- Uses the correct workspace Python interpreter
- Eliminates terminal escaping problems

### 3. BlenderMCP Bridge Usage

The standard pattern for 3D modeling:

```python
import sys
import os

# Add blender-mcp to path (adjust based on your workspace location)
BLENDER_MCP_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BLENDER_MCP_PATH)

from tools.copilot_bridge import BlenderCopilotBridge

bridge = BlenderCopilotBridge()

# Execute Blender code
blender_code = """
import bpy
# Your Blender operations here
"""

result = bridge.execute_blender_code(blender_code)
```

### 4. Key Bridge Methods

- `execute_blender_code(code)` - Execute Python code in Blender
- `capture_viewport_screenshot()` - Take scene screenshots
- `get_scene_info()` - Get object counts and positions
- `search_sketchfab_models(query)` - Search Sketchfab assets
- `download_sketchfab_model(uid)` - Download Sketchfab models
- `search_polyhaven_assets(query)` - Search PolyHaven assets

### 5. Scene Analysis Tool

Use `tools/scene_analyzer.py` or the `analyze_scene()` function for comprehensive scene documentation:

```python
from tools.scene_analyzer import SceneAnalyzer, analyze_scene

# Quick summary
from tools.scene_analyzer import quick_geonodes_summary
print(quick_geonodes_summary())

# Full analysis
report = analyze_scene()  # Returns text report
print(report)

# Export to markdown
analyze_scene(output_format="markdown", filepath="scene_report.md")

# Programmatic access
analyzer = SceneAnalyzer()
analysis = analyzer.full_analysis()  # Returns dict with all data
```

**Scene Analyzer Features:**

- Lists all geometry node groups with node/link counts
- Shows parameters with socket IDs, types, and defaults
- Displays current parameter values per object
- Analyzes materials and shader node types
- Maps collections and object hierarchies
- Exports to text or markdown format

**Command Line Usage:**

```bash
python tools/scene_analyzer.py              # Full text report
python tools/scene_analyzer.py --quick      # Quick geonode summary
python tools/scene_analyzer.py --format markdown -o report.md  # Markdown export
```

### 6. Geometry Node Helper

Use `tools/geonode_helper.py` for organizing nodes with frames:

```python
from tools.geonode_helper import GeoNodeHelper, frame_new_nodes, create_frame, FRAME_COLORS

helper = GeoNodeHelper()

# After creating nodes, frame all unparented ones
result = frame_new_nodes("PlantSystem", "New Feature")

# Create a frame around specific nodes
create_frame("PlantSystem", "My Section", ["Node1", "Node2"], FRAME_COLORS["math"])

# List all frames
frames = helper.list_frames("PlantSystem")

# Rename a frame
helper.rename_frame("PlantSystem", "Old Name", "New Name")

# Set frame color (for debugging - make it stand out)
helper.set_frame_color("PlantSystem", "look here", FRAME_COLORS["debug"])

# Clean up empty frames
helper.delete_empty_frames("PlantSystem")
```

**Standard Frame Colors:**

- `new` (blue): Unorganized/new nodes
- `input` (green): Input processing
- `output` (red): Output processing
- `transform` (orange): Transformations
- `math` (purple): Math operations
- `debug` (bright red): Debugging sections

**Workflow for Creating Nodes:**

1. Create nodes with `execute_blender_code()`
2. Call `frame_new_nodes("NodeGroup", "Feature Name")` to wrap them
3. User can then visually organize the framed nodes in Blender

### 7. Node Analysis and Validation Tools

Use additional functions in `tools/geonode_helper.py` for debugging and understanding node networks:

```python
from tools.geonode_helper import (
    analyze_geonode_group,
    trace_node_chain,
    validate_geonode_connections,
    reorganize_nodes
)

# Get complete structure of a node group
analysis = analyze_geonode_group("SoilGeometryNodes")
print(f"Nodes: {analysis['statistics']['node_count']}")
print(f"Links: {analysis['statistics']['link_count']}")
for node in analysis['nodes']:
    print(f"  {node['name']} ({node['type']})")

# Trace connections from a specific node
chain = trace_node_chain("SoilGeometryNodes", "ClodSystem", direction="downstream")
for item in chain['chain']:
    print(f"  {'  ' * item['depth']}{item['name']}")

# Validate for issues
validation = validate_geonode_connections("SoilGeometryNodes")
if validation['issues']:
    for issue in validation['issues']:
        print(f"Issue: {issue['message']}")
if validation['warnings']:
    for warning in validation['warnings']:
        print(f"Warning: {warning['message']}")

# Auto-layout nodes by dependency depth
result = reorganize_nodes("SoilGeometryNodes", strategy="columnar")
print(f"Repositioned {result['repositioned']} nodes across {result['depth_count']} columns")
```

**Tool Descriptions:**

| Tool                             | Purpose                                                     |
| -------------------------------- | ----------------------------------------------------------- |
| `analyze_geonode_group()`        | Dump complete node structure: nodes, links, sockets, values |
| `trace_node_chain()`             | Follow connections upstream or downstream from a node       |
| `validate_geonode_connections()` | Find orphans, unconnected inputs, organization issues       |
| `reorganize_nodes()`             | Auto-layout nodes in columns by dependency depth            |

**When to Use:**

- **analyze**: Understanding an unfamiliar node group, documenting structure
- **trace**: Following data flow, debugging connection issues
- **validate**: Before finalizing a node group, finding forgotten nodes
- **reorganize**: After major edits, cleaning up chaotic layouts

### 8. Texture Baker (tools/texture_baker_v2.py)

**CRITICAL**: Use `tools/texture_baker_v2.py` for baking procedural materials. This tool handles the COMPLETE workflow:

1. **Bake** - Create texture files from procedural material
2. **Replace** - Remove procedural nodes and connect baked image textures

**ALWAYS list materials first to get exact names:**

```python
from tools.texture_baker_v2 import TextureBaker

baker = TextureBaker()

# STEP 1: List all materials and objects (ALWAYS DO THIS FIRST)
baker.list_all_materials()

# STEP 2: Bake AND replace with exact names from the list
result = baker.bake_and_replace(
    material_name="Exact Material Name",  # From list_all_materials()
    object_name="Exact Object Name",      # From list_all_materials()
    resolution=2048
)

# Or bake only (don't modify material)
result = baker.bake_only(
    material_name="Exact Material Name",
    object_name="Exact Object Name",
    resolution=2048
)
```

**Command Line Usage:**

```bash
# ALWAYS list first to get exact names
python tools/texture_baker_v2.py --list

# Bake only (creates files, doesn't modify material)
python tools/texture_baker_v2.py -m "Material Name" -o "Object Name" -r 2048

# Bake AND replace procedural nodes with image textures
python tools/texture_baker_v2.py -m "Material Name" -o "Object Name" -r 2048 --replace
```

**Supported Bake Types:**

| Type      | Description       | Color Space |
| --------- | ----------------- | ----------- |
| DIFFUSE   | Base color/albedo | sRGB        |
| NORMAL    | Normal map        | Non-Color   |
| ROUGHNESS | Surface roughness | Non-Color   |
| METALLIC  | Metallic value    | Non-Color   |
| AO        | Ambient occlusion | Non-Color   |
| EMISSION  | Emission/glow     | sRGB        |

**CRITICAL Requirements:**

- ALWAYS use `list_all_materials()` first - never auto-detect
- Object must have UV coordinates
- Object must be render-enabled (`hide_render = False`)
- Cycles render engine (automatically set)

**Common Mistakes to Avoid:**

1. **Don't auto-detect objects** - Multiple objects may use the same material
2. **Baking ≠ Replacing** - Baking creates files, you must also replace nodes
3. **Normal textures need Normal Map node** - Don't connect directly to BSDF

## 3D Modeling Best Practices

### Material Creation

Always use basic Principled BSDF properties that work across Blender versions:

```python
material = bpy.data.materials.new(name="MaterialName")
material.use_nodes = True
bsdf = material.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
bsdf.inputs["Metallic"].default_value = 0.3
bsdf.inputs["Roughness"].default_value = 0.2
```

**AVOID**: `Transmission`, `Emission`, `Alpha` properties - they may not be available in all Blender versions.

### Low-Poly Design Principles

- Use basic primitives: cubes, cylinders, spheres, cones
- Keep vertex counts low (6-sided cylinders, 8-sided cones)
- Scale and position objects for realistic proportions
- Use proper naming conventions: `ObjectType_ComponentName_Variant`

### Spatial Planning

Implement zone-based layouts to prevent object overlaps:

```python
# Define zones for different object types
bed_area = {"x": (-4, -2), "y": (-5, -2)}
desk_area = {"x": (3, 4), "y": (2, 4)}
```

### Camera Management

Always position camera for optimal viewing:

```python
camera = bpy.data.objects.get('Camera')
if camera:
    camera.location = (x, y, z)
    camera.rotation_euler = (pitch, yaw, roll)
```

## Integration Capabilities

### Sketchfab Integration

- API key configured in Blender preferences
- Search and download user's personal models using UID
- Automatic scaling and positioning of imported models
- Example: Door Stop model (UID: b40a8e38404343d3b9cbd94baa11ce66)

### PolyHaven Assets

- Access to textures and 3D models
- Automatic material application
- PBR workflow support

### AI Model Generation

- Text-to-3D model generation
- Status checking and import workflows
- Integration with external AI services

## Established Scene Elements

### Current Session Context

From our development session, the scene contains:

- **Bedroom**: 12x12 room with furniture (bed, dresser, wardrobe, desk, chair, lamp)
- **Colored Spheres**: Red, blue, green spheres in a row
- **Conifer Trees**: 5 variations (Small→Medium→Tall→Bushy→Mature) at Y=8
- **Red Sedan**: 10-part low-poly car at (10, -2, 0)
- **Door Stop**: Scaled Sketchfab model (16 components) at (-5.5, 5.5, 0)
- **House Complex**: Complete property at (-15, 10, 0) with fence and tree (35 objects)

### Coordinate System Understanding

- X-axis: Left (-) to Right (+)
- Y-axis: Back (-) to Front (+)
- Z-axis: Down (-) to Up (+)
- Origin (0,0,0) is scene center

## Code Quality Standards

### Exception Handling

The server uses custom exceptions:

- `BlenderConnectionError` - Communication failures
- `BlenderCommandError` - Command execution errors
- `BlenderResponseError` - Response parsing issues
- `BlenderTimeoutError` - Operation timeouts

### Function Organization

- Break complex functions into smaller helpers
- Avoid high cognitive complexity
- Remove redundant exception handling
- Use specific exception types instead of generic `Exception`

## Debugging and Troubleshooting

### Common Issues

1. **Socket Communication Errors**: Ensure Blender addon is running
2. **Material Property Errors**: Use only basic BSDF properties
3. **Object Overlap**: Implement spatial planning with zones
4. **Scale Issues**: Always verify object dimensions after import

### Diagnostic Tools

- `get_scene_info()` - Check object counts and positions
- `capture_viewport_screenshot()` - Visual verification
- Error logs from bridge communication

## Screenshot and Documentation

Always capture screenshots after major modeling operations:

```python
screenshot_path = bridge.capture_viewport_screenshot()
print(f"Screenshot saved: {screenshot_path}")
```

## Session Continuity

### Starting New Sessions

1. Verify BlenderMCP server is running (`uvx blender-mcp`)
2. Check Blender addon connection (port 9876)
3. Test basic bridge communication
4. Review existing scene elements with `get_scene_info()`

### Context Preservation

- Scene elements persist between sessions
- Camera positions are maintained
- Materials and objects remain in Blender file
- Screenshots provide visual history

## Advanced Features

### Batch Operations

Use `multi_replace_string_in_file` for multiple code edits to improve efficiency.

### Complex Modeling

- Layered object creation (trees with multiple foliage layers)
- Compound objects (cars with body, wheels, lights)
- Architectural elements (houses with windows, doors, roofs)

### Asset Integration

- Sketchfab personal asset library access
- PolyHaven material and model integration
- AI-generated model import workflows

## Performance Considerations

- Use low-poly modeling for better performance
- Implement proper object naming for scene organization
- Position objects strategically to avoid viewport clutter
- Take screenshots incrementally to track progress

## Success Metrics

- Clean code execution without errors
- Proper spatial distribution of objects
- Realistic proportions and materials
- Successful integration of external assets
- Clear visual documentation through screenshots

---

_This workflow has been tested and proven effective through comprehensive 3D modeling sessions including room design, vehicle creation, architectural modeling, and asset integration._
