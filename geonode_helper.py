#!/usr/bin/env python3
"""
Geometry Node Helpers for BlenderMCP
Provides utilities for creating and organizing geometry nodes, including
automatic frame creation around new nodes.
"""

from typing import Dict, List, Any, Optional, Tuple
from copilot_bridge import BlenderCopilotBridge


class GeoNodeHelper:
    """Helper class for creating and organizing geometry nodes"""

    def __init__(self, host='127.0.0.1', port=9876):
        self.bridge = BlenderCopilotBridge(host, port)

    def create_frame(self, node_group_name: str, frame_label: str, 
                     node_names: List[str], color: Tuple[float, float, float] = None) -> Dict[str, Any]:
        """
        Create a frame around specified nodes in a geometry node group.
        
        Args:
            node_group_name: Name of the geometry node group
            frame_label: Label for the frame (e.g., "New Nodes", "look here")
            node_names: List of node names to include in the frame
            color: Optional RGB tuple (0-1 range) for frame color
        
        Returns:
            Dict with frame name and success status
        """
        node_names_str = str(node_names)
        color_code = ""
        if color:
            color_code = f"""
    frame.use_custom_color = True
    frame.color = ({color[0]}, {color[1]}, {color[2]})
"""
        
        code = f'''
import bpy

result = {{"success": False, "frame_name": None, "message": ""}}
ng = bpy.data.node_groups.get("{node_group_name}")
if not ng:
    result["message"] = "Node group not found: {node_group_name}"
else:
    node_names = {node_names_str}
    
    # Create the frame
    frame = ng.nodes.new("NodeFrame")
    frame.label = "{frame_label}"
    frame.name = "{frame_label}"
{color_code}
    
    # Parent nodes to the frame
    parented = []
    for name in node_names:
        node = ng.nodes.get(name)
        if node:
            node.parent = frame
            parented.append(name)
    
    result["success"] = True
    result["frame_name"] = frame.name
    result["parented_nodes"] = parented
    result["message"] = f"Created frame '{{frame.label}}' with {{len(parented)}} nodes"

print(result)
'''
        result_str = self.bridge.execute_blender_code(code)
        try:
            import ast
            return ast.literal_eval(result_str.strip())
        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_recent_nodes(self, node_group_name: str, count: int = 10) -> List[str]:
        """
        Get the most recently created nodes in a node group.
        Useful for framing nodes that were just created.
        
        Note: Blender doesn't track creation time, so this returns nodes
        that appear last in the nodes collection (typically recently added).
        """
        code = f'''
import bpy

result = []
ng = bpy.data.node_groups.get("{node_group_name}")
if ng:
    # Get non-frame nodes, last N added
    nodes = [n.name for n in ng.nodes if n.type != "FRAME" and n.parent is None]
    result = nodes[-{count}:]

print(result)
'''
        result_str = self.bridge.execute_blender_code(code)
        try:
            import ast
            return ast.literal_eval(result_str.strip())
        except Exception:
            return []

    def frame_unparented_nodes(self, node_group_name: str, frame_label: str = "New Nodes",
                                color: Tuple[float, float, float] = (0.2, 0.6, 0.8)) -> Dict[str, Any]:
        """
        Create a frame around all nodes that don't currently have a parent frame.
        Useful for organizing loose nodes after creation.
        
        Args:
            node_group_name: Name of the geometry node group
            frame_label: Label for the new frame
            color: RGB color for the frame (default: blue)
        """
        code = f'''
import bpy

result = {{"success": False, "frame_name": None, "nodes": [], "message": ""}}
ng = bpy.data.node_groups.get("{node_group_name}")
if not ng:
    result["message"] = "Node group not found: {node_group_name}"
else:
    # Find unparented nodes (excluding Group Input/Output and frames)
    excluded = ["GROUP_INPUT", "GROUP_OUTPUT", "FRAME"]
    unparented = [n for n in ng.nodes if n.parent is None and n.type not in excluded]
    
    if not unparented:
        result["message"] = "No unparented nodes found"
        result["success"] = True
    else:
        # Create frame
        frame = ng.nodes.new("NodeFrame")
        frame.label = "{frame_label}"
        frame.name = "{frame_label}"
        frame.use_custom_color = True
        frame.color = {color}
        
        # Parent nodes
        for node in unparented:
            node.parent = frame
            result["nodes"].append(node.name)
        
        result["success"] = True
        result["frame_name"] = frame.name
        result["message"] = f"Created frame '{{frame.label}}' with {{len(result['nodes'])}} nodes"

print(result)
'''
        result_str = self.bridge.execute_blender_code(code)
        try:
            import ast
            return ast.literal_eval(result_str.strip())
        except Exception as e:
            return {"success": False, "message": str(e)}

    def rename_frame(self, node_group_name: str, old_label: str, new_label: str) -> Dict[str, Any]:
        """Rename a frame by its label"""
        code = f'''
import bpy

result = {{"success": False, "message": ""}}
ng = bpy.data.node_groups.get("{node_group_name}")
if ng:
    for node in ng.nodes:
        if node.type == "FRAME" and (node.label == "{old_label}" or node.name == "{old_label}"):
            node.label = "{new_label}"
            node.name = "{new_label}"
            result["success"] = True
            result["message"] = f"Renamed frame to '{new_label}'"
            break
    if not result["success"]:
        result["message"] = "Frame not found: {old_label}"

print(result)
'''
        result_str = self.bridge.execute_blender_code(code)
        try:
            import ast
            return ast.literal_eval(result_str.strip())
        except Exception as e:
            return {"success": False, "message": str(e)}

    def set_frame_color(self, node_group_name: str, frame_label: str,
                        color: Tuple[float, float, float]) -> Dict[str, Any]:
        """Set the color of a frame"""
        code = f'''
import bpy

result = {{"success": False, "message": ""}}
ng = bpy.data.node_groups.get("{node_group_name}")
if ng:
    for node in ng.nodes:
        if node.type == "FRAME" and (node.label == "{frame_label}" or node.name == "{frame_label}"):
            node.use_custom_color = True
            node.color = {color}
            result["success"] = True
            result["message"] = f"Set frame color"
            break
    if not result["success"]:
        result["message"] = "Frame not found: {frame_label}"

print(result)
'''
        result_str = self.bridge.execute_blender_code(code)
        try:
            import ast
            return ast.literal_eval(result_str.strip())
        except Exception as e:
            return {"success": False, "message": str(e)}

    def list_frames(self, node_group_name: str) -> List[Dict[str, Any]]:
        """List all frames in a node group with their node counts"""
        code = f'''
import bpy

result = []
ng = bpy.data.node_groups.get("{node_group_name}")
if ng:
    for node in ng.nodes:
        if node.type == "FRAME":
            children = [n.name for n in ng.nodes if n.parent == node]
            result.append({{
                "name": node.name,
                "label": node.label if node.label else node.name,
                "node_count": len(children),
                "color": list(node.color) if node.use_custom_color else None
            }})

print(result)
'''
        result_str = self.bridge.execute_blender_code(code)
        try:
            import ast
            return ast.literal_eval(result_str.strip())
        except Exception:
            return []

    def delete_empty_frames(self, node_group_name: str) -> Dict[str, Any]:
        """Delete all frames that have no child nodes"""
        code = f'''
import bpy

result = {{"success": True, "deleted": [], "message": ""}}
ng = bpy.data.node_groups.get("{node_group_name}")
if ng:
    to_delete = []
    for node in ng.nodes:
        if node.type == "FRAME":
            children = [n for n in ng.nodes if n.parent == node]
            if not children:
                to_delete.append(node)
    
    for frame in to_delete:
        result["deleted"].append(frame.label or frame.name)
        ng.nodes.remove(frame)
    
    result["message"] = f"Deleted {{len(result['deleted'])}} empty frames"

print(result)
'''
        result_str = self.bridge.execute_blender_code(code)
        try:
            import ast
            return ast.literal_eval(result_str.strip())
        except Exception as e:
            return {"success": False, "message": str(e)}


# Convenience functions

def create_frame(node_group: str, label: str, nodes: List[str], 
                 color: Tuple[float, float, float] = None) -> Dict[str, Any]:
    """Create a frame around specified nodes"""
    helper = GeoNodeHelper()
    return helper.create_frame(node_group, label, nodes, color)


def frame_new_nodes(node_group: str, label: str = "New Nodes") -> Dict[str, Any]:
    """Frame all unparented nodes (typically newly created ones)"""
    helper = GeoNodeHelper()
    return helper.frame_unparented_nodes(node_group, label)


def list_frames(node_group: str) -> List[Dict[str, Any]]:
    """List all frames in a node group"""
    helper = GeoNodeHelper()
    return helper.list_frames(node_group)


# Standard frame colors for organization
FRAME_COLORS = {
    "new": (0.2, 0.6, 0.8),      # Blue - new/unorganized nodes
    "input": (0.3, 0.7, 0.3),    # Green - input processing
    "output": (0.7, 0.3, 0.3),   # Red - output processing  
    "transform": (0.7, 0.5, 0.2), # Orange - transformations
    "math": (0.5, 0.3, 0.7),     # Purple - math operations
    "debug": (0.9, 0.2, 0.2),    # Bright red - debugging/look here
}


if __name__ == "__main__":
    # Demo: list frames in PlantSystem
    helper = GeoNodeHelper()
    frames = helper.list_frames("PlantSystem")
    print("Frames in PlantSystem:")
    for f in frames:
        print(f"  {f['label']}: {f['node_count']} nodes")
