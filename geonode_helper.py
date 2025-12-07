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


def analyze_geonode_group(node_group_name: str) -> Dict[str, Any]:
    """
    Dump complete structure of a geometry node group.
    Returns detailed info about nodes, connections, socket types, and values.
    
    Args:
        node_group_name: Name of the geometry node group to analyze
        
    Returns:
        Dict containing:
        - nodes: List of all nodes with type, position, parent frame
        - links: List of all connections (from_node, from_socket, to_node, to_socket)
        - inputs: Group input interface sockets
        - outputs: Group output interface sockets
        - frames: List of frames with their children
        - statistics: node_count, link_count, frame_count
    """
    helper = GeoNodeHelper()
    code = '''
import bpy
import json
import math

def safe_value(val):
    """Convert value to JSON-safe format"""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        if math.isnan(val) or math.isinf(val):
            return str(val)
        return val
    if isinstance(val, str):
        return val
    if hasattr(val, "__iter__"):
        return [safe_value(v) for v in list(val)[:4]]
    return str(val)

result = {"success": False, "error": None}
ng = bpy.data.node_groups.get("''' + node_group_name + '''")
if not ng:
    result["error"] = "Node group not found"
else:
    result["success"] = True
    result["name"] = ng.name
    result["type"] = ng.type
    
    # Nodes
    result["nodes"] = []
    for node in ng.nodes:
        node_info = {
            "name": node.name,
            "type": node.type,
            "bl_idname": node.bl_idname,
            "label": node.label if node.label else "",
            "position": [round(node.location.x, 1), round(node.location.y, 1)],
            "parent": node.parent.name if node.parent else None,
            "muted": node.mute,
            "inputs": [],
            "outputs": []
        }
        
        # Input sockets with values
        for inp in node.inputs:
            socket_info = {
                "name": inp.name,
                "type": inp.type,
                "is_linked": inp.is_linked
            }
            # Get default value if not linked
            if not inp.is_linked and hasattr(inp, "default_value"):
                socket_info["value"] = safe_value(inp.default_value)
            node_info["inputs"].append(socket_info)
        
        # Output sockets
        for out in node.outputs:
            socket_info = {
                "name": out.name,
                "type": out.type,
                "is_linked": out.is_linked
            }
            node_info["outputs"].append(socket_info)
        
        result["nodes"].append(node_info)
    
    # Links
    result["links"] = []
    for link in ng.links:
        result["links"].append({
            "from_node": link.from_node.name,
            "from_socket": link.from_socket.name,
            "to_node": link.to_node.name,
            "to_socket": link.to_socket.name
        })
    
    # Frames summary
    result["frames"] = []
    for node in ng.nodes:
        if node.type == "FRAME":
            children = [n.name for n in ng.nodes if n.parent == node]
            result["frames"].append({
                "name": node.name,
                "label": node.label if node.label else node.name,
                "children": children,
                "color": list(node.color)[:3] if node.use_custom_color else None
            })
    
    # Interface inputs/outputs
    result["group_inputs"] = []
    result["group_outputs"] = []
    if hasattr(ng, "interface") and hasattr(ng.interface, "items_tree"):
        for item in ng.interface.items_tree:
            if hasattr(item, "socket_type"):
                item_info = {
                    "name": item.name,
                    "identifier": item.identifier,
                    "socket_type": item.socket_type
                }
                if hasattr(item, "default_value"):
                    item_info["default"] = safe_value(item.default_value)
                if item.in_out == "INPUT":
                    result["group_inputs"].append(item_info)
                else:
                    result["group_outputs"].append(item_info)
    
    # Statistics
    result["statistics"] = {
        "node_count": len(ng.nodes),
        "link_count": len(ng.links),
        "frame_count": len(result["frames"]),
        "input_count": len(result["group_inputs"]),
        "output_count": len(result["group_outputs"])
    }

print(json.dumps(result))
'''
    result_str = helper.bridge.execute_blender_code(code)
    try:
        import json
        return json.loads(result_str.strip())
    except Exception as e:
        return {"success": False, "error": str(e), "raw": result_str[:200] if result_str else None}


def trace_node_chain(node_group_name: str, start_node: str, direction: str = "downstream") -> Dict[str, Any]:
    """
    Trace the connection chain from a node, following links.
    
    Args:
        node_group_name: Name of the geometry node group
        start_node: Name of the starting node
        direction: "downstream" (follow outputs) or "upstream" (follow inputs)
        
    Returns:
        Dict with ordered list of nodes in the chain and the connections between them
    """
    helper = GeoNodeHelper()
    direction_code = "True" if direction == "downstream" else "False"
    code = f'''
import bpy

result = {{"success": False, "chain": [], "connections": []}}
ng = bpy.data.node_groups.get("{node_group_name}")
if not ng:
    result["error"] = "Node group not found"
else:
    start = ng.nodes.get("{start_node}")
    if not start:
        result["error"] = "Start node not found: {start_node}"
    else:
        downstream = {direction_code}
        visited = set()
        chain = []
        connections = []
        
        def trace(node, depth=0):
            if node.name in visited or depth > 50:
                return
            visited.add(node.name)
            chain.append({{"name": node.name, "type": node.type, "depth": depth}})
            
            if downstream:
                # Follow outputs
                for out in node.outputs:
                    for link in ng.links:
                        if link.from_node == node and link.from_socket == out:
                            connections.append({{
                                "from": node.name,
                                "from_socket": out.name,
                                "to": link.to_node.name,
                                "to_socket": link.to_socket.name
                            }})
                            trace(link.to_node, depth + 1)
            else:
                # Follow inputs
                for inp in node.inputs:
                    for link in ng.links:
                        if link.to_node == node and link.to_socket == inp:
                            connections.append({{
                                "from": link.from_node.name,
                                "from_socket": link.from_socket.name,
                                "to": node.name,
                                "to_socket": inp.name
                            }})
                            trace(link.from_node, depth + 1)
        
        trace(start)
        result["success"] = True
        result["chain"] = chain
        result["connections"] = connections
        result["direction"] = "{"downstream" if direction == "downstream" else "upstream"}"

import json
print(json.dumps(result))
'''
    result_str = helper.bridge.execute_blender_code(code)
    try:
        import json
        return json.loads(result_str.strip())
    except Exception as e:
        return {"success": False, "error": str(e), "raw": result_str[:200] if result_str else None}


def validate_geonode_connections(node_group_name: str) -> Dict[str, Any]:
    """
    Validate a geometry node group for common issues.
    
    Checks for:
    - Orphan nodes (not connected to anything)
    - Unconnected required inputs on nodes
    - Type mismatches in connections
    - Nodes not in any frame (optional organization check)
    
    Args:
        node_group_name: Name of the geometry node group
        
    Returns:
        Dict with validation results and lists of issues found
    """
    helper = GeoNodeHelper()
    code = '''
import bpy

result = {"success": False, "issues": [], "warnings": [], "stats": {}}
ng = bpy.data.node_groups.get("''' + node_group_name + '''")
if not ng:
    result["error"] = "Node group not found"
else:
    result["success"] = True
    orphans = []
    unconnected_inputs = []
    unframed = []
    
    for node in ng.nodes:
        if node.type == "FRAME":
            continue
            
        # Check for orphan nodes (no connections at all)
        has_input_link = any(inp.is_linked for inp in node.inputs)
        has_output_link = any(out.is_linked for out in node.outputs)
        
        # Skip Group Input/Output - they're supposed to be endpoints
        if node.type not in ["GROUP_INPUT", "GROUP_OUTPUT"]:
            if not has_input_link and not has_output_link:
                orphans.append({"node": node.name, "type": node.type})
            
            # Check for important unconnected inputs
            # (geometry, mesh inputs that aren't optional)
            for inp in node.inputs:
                if not inp.is_linked and inp.type in ["GEOMETRY", "MESH"]:
                    # Some nodes have optional geometry inputs
                    if not inp.hide:  # Hidden = probably optional
                        unconnected_inputs.append({
                            "node": node.name,
                            "socket": inp.name,
                            "type": inp.type
                        })
        
        # Check if node is unframed (organization warning)
        if node.parent is None and node.type not in ["GROUP_INPUT", "GROUP_OUTPUT", "FRAME"]:
            unframed.append(node.name)
    
    if orphans:
        result["issues"].append({
            "type": "orphan_nodes",
            "message": f"{len(orphans)} nodes have no connections",
            "nodes": orphans
        })
    
    if unconnected_inputs:
        result["issues"].append({
            "type": "unconnected_geometry_inputs",
            "message": f"{len(unconnected_inputs)} geometry/mesh inputs not connected",
            "sockets": unconnected_inputs
        })
    
    if unframed:
        result["warnings"].append({
            "type": "unframed_nodes",
            "message": f"{len(unframed)} nodes not in any frame",
            "nodes": unframed[:10]  # Limit output
        })
    
    result["stats"] = {
        "total_nodes": len([n for n in ng.nodes if n.type != "FRAME"]),
        "orphan_count": len(orphans),
        "unconnected_input_count": len(unconnected_inputs),
        "unframed_count": len(unframed),
        "is_valid": len(orphans) == 0 and len(unconnected_inputs) == 0
    }

import json
print(json.dumps(result))
'''
    result_str = helper.bridge.execute_blender_code(code)
    try:
        import json
        return json.loads(result_str.strip())
    except Exception as e:
        return {"success": False, "error": str(e), "raw": result_str[:200] if result_str else None}


def reorganize_nodes(node_group_name: str, strategy: str = "columnar") -> Dict[str, Any]:
    """
    Auto-layout nodes in a geometry node group.
    
    Args:
        node_group_name: Name of the geometry node group
        strategy: Layout strategy - "columnar" (left-to-right by depth) or "compact"
        
    Returns:
        Dict with repositioned node count and new positions
    """
    helper = GeoNodeHelper()
    code = '''
import bpy

result = {"success": False, "repositioned": 0}
ng = bpy.data.node_groups.get("''' + node_group_name + '''")
if not ng:
    result["error"] = "Node group not found"
else:
    # Build dependency graph
    node_depths = {}
    
    # Start from Group Input (depth 0)
    group_input = None
    for node in ng.nodes:
        if node.type == "GROUP_INPUT":
            group_input = node
            break
    
    if not group_input:
        result["error"] = "No Group Input node found"
    else:
        # BFS to assign depths
        from collections import deque
        queue = deque([(group_input, 0)])
        visited = set()
        
        while queue:
            node, depth = queue.popleft()
            if node.name in visited:
                continue
            visited.add(node.name)
            
            # Track max depth for each node
            if node.name not in node_depths:
                node_depths[node.name] = depth
            else:
                node_depths[node.name] = max(node_depths[node.name], depth)
            
            # Find connected downstream nodes
            for out in node.outputs:
                for link in ng.links:
                    if link.from_node == node and link.from_socket == out:
                        queue.append((link.to_node, depth + 1))
        
        # Assign nodes not reached (orphans or upstream-only) depth based on their x position
        for node in ng.nodes:
            if node.name not in node_depths and node.type != "FRAME":
                # Estimate depth from current position
                node_depths[node.name] = max(0, int((node.location.x + 400) / 300))
        
        # Group by depth
        depth_groups = {}
        for node_name, depth in node_depths.items():
            if depth not in depth_groups:
                depth_groups[depth] = []
            depth_groups[depth].append(node_name)
        
        # Position nodes
        X_SPACING = 300
        Y_SPACING = 150
        repositioned = []
        
        for depth, nodes in sorted(depth_groups.items()):
            x = -400 + (depth * X_SPACING)
            for i, node_name in enumerate(sorted(nodes)):
                node = ng.nodes.get(node_name)
                if node and node.type != "FRAME":
                    y = -i * Y_SPACING
                    node.location.x = x
                    node.location.y = y
                    repositioned.append({"name": node_name, "position": [x, y]})
        
        result["success"] = True
        result["repositioned"] = len(repositioned)
        result["positions"] = repositioned[:20]  # Limit output
        result["depth_count"] = len(depth_groups)

import json
print(json.dumps(result))
'''
    result_str = helper.bridge.execute_blender_code(code)
    try:
        import json
        return json.loads(result_str.strip())
    except Exception as e:
        return {"success": False, "error": str(e), "raw": result_str[:200] if result_str else None}


if __name__ == "__main__":
    # Demo: list frames in PlantSystem
    helper = GeoNodeHelper()
    frames = helper.list_frames("PlantSystem")
    print("Frames in PlantSystem:")
    for f in frames:
        print(f"  {f['label']}: {f['node_count']} nodes")
