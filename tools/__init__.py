"""
BlenderMCP Tools
================
Helper modules for interacting with Blender through the MCP server.

Key modules:
- blender_socket: Standalone socket communication (no dependencies, always works)
- copilot_bridge: Main bridge for executing Blender commands
- geonode_helper: Geometry node creation and organization
- scene_analyzer: Scene analysis and documentation
- material_helper: Material creation and modification
- texture_baker_v2: Procedural-to-baked texture workflow

Import Strategy:
    This module uses lazy imports via __getattr__ to prevent cascading failures.
    If one module has a bug, other modules can still be imported successfully.
    
    Example:
        from tools import BlenderCopilotBridge  # Only loads copilot_bridge
        from tools import TextureBaker          # Only loads texture_baker_v2
"""

# Always import blender_socket eagerly - it has no dependencies and is our fallback
from .blender_socket import send_code, send_command, get_scene_info, is_blender_connected

# Define what's available for lazy loading
__all__ = [
    # Eagerly loaded (always available)
    'send_code',
    'send_command', 
    'get_scene_info',
    'is_blender_connected',
    # Lazily loaded
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

# Cache for lazily loaded modules/attributes
_lazy_cache = {}


def __getattr__(name: str):
    """
    Lazy import handler - only loads modules when their exports are accessed.
    This prevents cascading import failures from breaking unrelated imports.
    """
    if name in _lazy_cache:
        return _lazy_cache[name]
    
    # copilot_bridge exports
    if name == 'BlenderCopilotBridge':
        from .copilot_bridge import BlenderCopilotBridge
        _lazy_cache[name] = BlenderCopilotBridge
        return BlenderCopilotBridge
    
    # geonode_helper exports
    if name in ('GeoNodeHelper', 'frame_new_nodes', 'create_frame', 'FRAME_COLORS'):
        from . import geonode_helper
        _lazy_cache['GeoNodeHelper'] = geonode_helper.GeoNodeHelper
        _lazy_cache['frame_new_nodes'] = geonode_helper.frame_new_nodes
        _lazy_cache['create_frame'] = geonode_helper.create_frame
        _lazy_cache['FRAME_COLORS'] = geonode_helper.FRAME_COLORS
        return _lazy_cache[name]
    
    # scene_analyzer exports
    if name in ('SceneAnalyzer', 'analyze_scene', 'quick_geonodes_summary'):
        from . import scene_analyzer
        _lazy_cache['SceneAnalyzer'] = scene_analyzer.SceneAnalyzer
        _lazy_cache['analyze_scene'] = scene_analyzer.analyze_scene
        _lazy_cache['quick_geonodes_summary'] = scene_analyzer.quick_geonodes_summary
        return _lazy_cache[name]
    
    # material_helper exports
    if name == 'MaterialHelper':
        from .material_helper import MaterialHelper
        _lazy_cache[name] = MaterialHelper
        return MaterialHelper
    
    # texture_baker_v2 exports
    if name == 'TextureBaker':
        from .texture_baker_v2 import TextureBaker
        _lazy_cache[name] = TextureBaker
        return TextureBaker
    
    raise AttributeError(f"module 'tools' has no attribute '{name}'")
