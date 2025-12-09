"""
BlenderMCP Tools
================
Helper modules for interacting with Blender through the MCP server.

Key modules:
- copilot_bridge: Main bridge for executing Blender commands
- geonode_helper: Geometry node creation and organization
- scene_analyzer: Scene analysis and documentation
- material_helper: Material creation and modification
- texture_baker_v2: Procedural-to-baked texture workflow
"""

from .copilot_bridge import BlenderCopilotBridge
from .geonode_helper import GeoNodeHelper, frame_new_nodes, create_frame, FRAME_COLORS
from .scene_analyzer import SceneAnalyzer, analyze_scene, quick_geonodes_summary
from .material_helper import MaterialHelper
from .texture_baker_v2 import TextureBaker

__all__ = [
    'BlenderCopilotBridge',
    'GeoNodeHelper',
    'frame_new_nodes',
    'create_frame',
    'FRAME_COLORS',
    'SceneAnalyzer',
    'analyze_scene',
    'quick_geonodes_summary',
    'MaterialHelper',
    'TextureBaker',
]
