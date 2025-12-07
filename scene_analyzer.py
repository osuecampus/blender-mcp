#!/usr/bin/env python3
"""
Scene Analyzer for BlenderMCP
Provides comprehensive analysis of Blender scenes including geometry nodes,
materials, and object properties. Useful for documenting and understanding projects.
"""

import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from copilot_bridge import BlenderCopilotBridge


@dataclass
class GeoNodeParameter:
    """Represents a geometry node parameter"""
    name: str
    socket_id: str
    socket_type: str
    value: Any
    default: Any = None
    min_value: Any = None
    max_value: Any = None


@dataclass
class GeoNodeGroup:
    """Represents a geometry node group"""
    name: str
    node_count: int
    link_count: int
    parameters: List[GeoNodeParameter]
    used_by: List[str]  # Object names using this node group


@dataclass
class MaterialInfo:
    """Represents material information"""
    name: str
    node_count: int
    has_nodes: bool
    blend_method: str
    used_by: List[str]  # Object names using this material


class SceneAnalyzer:
    """Analyzes Blender scenes for geometry nodes, materials, and objects"""

    def __init__(self, host='127.0.0.1', port=9876):
        self.bridge = BlenderCopilotBridge(host, port)

    def analyze_geometry_nodes(self) -> List[Dict[str, Any]]:
        """Analyze all geometry node groups in the scene"""
        code = '''
import bpy
import json

result = []

for ng in bpy.data.node_groups:
    if ng.type != "GEOMETRY":
        continue
    
    group_info = {
        "name": ng.name,
        "node_count": len(ng.nodes),
        "link_count": len(ng.links),
        "parameters": [],
        "used_by": []
    }
    
    # Get input parameters from interface
    if hasattr(ng, "interface") and hasattr(ng.interface, "items_tree"):
        for item in ng.interface.items_tree:
            if hasattr(item, "socket_type") and item.in_out == "INPUT":
                param = {
                    "name": item.name,
                    "socket_id": item.identifier,
                    "socket_type": item.socket_type,
                    "default": None,
                    "min_value": None,
                    "max_value": None
                }
                
                # Get default value if available
                if hasattr(item, "default_value"):
                    val = item.default_value
                    if hasattr(val, "__iter__") and not isinstance(val, str):
                        param["default"] = list(val)[:4]  # Limit vectors
                    else:
                        param["default"] = val
                
                # Get min/max if available
                if hasattr(item, "min_value"):
                    param["min_value"] = item.min_value
                if hasattr(item, "max_value"):
                    param["max_value"] = item.max_value
                
                group_info["parameters"].append(param)
    
    # Find objects using this node group
    for obj in bpy.data.objects:
        if obj.type == "MESH" or obj.type == "CURVE":
            for mod in obj.modifiers:
                if mod.type == "NODES" and mod.node_group == ng:
                    group_info["used_by"].append(obj.name)
    
    # Get frames (simplified - just name, label, and node count)
    group_info["frames"] = []
    for node in ng.nodes:
        if node.type == "FRAME":
            node_count = sum(1 for child in ng.nodes if child.parent == node)
            frame_info = {
                "name": node.name,
                "label": node.label if node.label else node.name,
                "node_count": node_count
            }
            group_info["frames"].append(frame_info)
    
    result.append(group_info)

print(json.dumps(result))
'''
        result = self.bridge.execute_blender_code(code)
        try:
            import json
            return json.loads(result.strip())
        except Exception:
            return []

    def get_modifier_values(self, object_name: str, node_group_name: str) -> Dict[str, Any]:
        """Get current parameter values from a geometry nodes modifier"""
        code = f'''
import bpy
import json

result = {{}}
obj = bpy.data.objects.get("{object_name}")
if obj:
    for mod in obj.modifiers:
        if mod.type == "NODES" and mod.node_group and mod.node_group.name == "{node_group_name}":
            ng = mod.node_group
            if hasattr(ng, "interface") and hasattr(ng.interface, "items_tree"):
                for item in ng.interface.items_tree:
                    if hasattr(item, "socket_type") and item.in_out == "INPUT":
                        socket_id = item.identifier
                        try:
                            val = mod[socket_id]
                            if hasattr(val, "__iter__") and not isinstance(val, str):
                                result[item.name] = list(val)[:4]
                            else:
                                result[item.name] = val
                        except:
                            result[item.name] = None
            break

print(json.dumps(result))
'''
        result = self.bridge.execute_blender_code(code)
        try:
            import json
            return json.loads(result.strip())
        except Exception:
            return {}

    def get_frame_details(self, node_group_name: str, frame_label: str = None) -> List[Dict[str, Any]]:
        """
        Get detailed information about frames in a geometry node group.
        If frame_label is provided, returns only that frame with full node details.
        Useful for debugging specific sections marked with frames like "look here".
        """
        code = f'''
import bpy
import json

def safe_value(val):
    """Convert Blender values to JSON-serializable types"""
    if val is None:
        return None
    if isinstance(val, (int, float, bool, str)):
        return val
    if hasattr(val, "__iter__"):
        try:
            return [float(v) if isinstance(v, (int, float)) else str(v) for v in list(val)[:4]]
        except:
            return str(val)
    return str(val)

result = []
ng = bpy.data.node_groups.get("{node_group_name}")
if ng:
    for node in ng.nodes:
        if node.type == "FRAME":
            label = node.label if node.label else node.name
            frame_filter = "{frame_label}" if "{frame_label}" else None
            
            # If filtering by label, skip non-matching frames
            if frame_filter and frame_filter.lower() not in label.lower():
                continue
            
            frame_info = {{
                "name": node.name,
                "label": label,
                "color": list(node.color) if node.use_custom_color else None,
                "nodes": [],
                "internal_links": []
            }}
            
            # Collect all nodes in this frame
            frame_nodes = set()
            for child in ng.nodes:
                if child.parent == node:
                    frame_nodes.add(child.name)
                    node_detail = {{
                        "name": child.name,
                        "type": child.type,
                        "label": child.label if child.label else child.name,
                        "inputs": [],
                        "outputs": []
                    }}
                    
                    # Get input sockets with values
                    for inp in child.inputs:
                        inp_info = {{"name": inp.name, "type": inp.type}}
                        if hasattr(inp, "default_value"):
                            inp_info["value"] = safe_value(inp.default_value)
                        # Check if connected
                        inp_info["connected"] = inp.is_linked
                        node_detail["inputs"].append(inp_info)
                    
                    # Get output sockets
                    for out in child.outputs:
                        out_info = {{"name": out.name, "type": out.type, "connected": out.is_linked}}
                        node_detail["outputs"].append(out_info)
                    
                    frame_info["nodes"].append(node_detail)
            
            # Find links within the frame
            for link in ng.links:
                if link.from_node.name in frame_nodes and link.to_node.name in frame_nodes:
                    frame_info["internal_links"].append({{
                        "from": f"{{link.from_node.name}}.{{link.from_socket.name}}",
                        "to": f"{{link.to_node.name}}.{{link.to_socket.name}}"
                    }})
            
            # Find links going into/out of the frame
            frame_info["incoming_links"] = []
            frame_info["outgoing_links"] = []
            for link in ng.links:
                if link.to_node.name in frame_nodes and link.from_node.name not in frame_nodes:
                    frame_info["incoming_links"].append({{
                        "from": f"{{link.from_node.name}}.{{link.from_socket.name}}",
                        "to": f"{{link.to_node.name}}.{{link.to_socket.name}}"
                    }})
                elif link.from_node.name in frame_nodes and link.to_node.name not in frame_nodes:
                    frame_info["outgoing_links"].append({{
                        "from": f"{{link.from_node.name}}.{{link.from_socket.name}}",
                        "to": f"{{link.to_node.name}}.{{link.to_socket.name}}"
                    }})
            
            result.append(frame_info)

print(json.dumps(result))
'''
        result = self.bridge.execute_blender_code(code)
        try:
            import json
            return json.loads(result.strip())
        except Exception:
            return []

    def analyze_materials(self) -> List[Dict[str, Any]]:
        """Analyze all materials in the scene"""
        code = '''
import bpy
import json

result = []

for mat in bpy.data.materials:
    mat_info = {
        "name": mat.name,
        "has_nodes": mat.use_nodes,
        "node_count": len(mat.node_tree.nodes) if mat.use_nodes and mat.node_tree else 0,
        "blend_method": mat.blend_method if hasattr(mat, "blend_method") else "OPAQUE",
        "used_by": [],
        "shader_nodes": []
    }
    
    # Get shader node types
    if mat.use_nodes and mat.node_tree:
        for node in mat.node_tree.nodes:
            if node.type not in ["OUTPUT_MATERIAL", "FRAME", "REROUTE"]:
                mat_info["shader_nodes"].append(node.type)
    
    # Find objects using this material
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            for slot in obj.material_slots:
                if slot.material == mat:
                    if obj.name not in mat_info["used_by"]:
                        mat_info["used_by"].append(obj.name)
    
    result.append(mat_info)

print(json.dumps(result))
'''
        result = self.bridge.execute_blender_code(code)
        try:
            import json
            return json.loads(result.strip())
        except Exception:
            return []

    def analyze_objects(self) -> List[Dict[str, Any]]:
        """Analyze all objects in the scene"""
        code = '''
import bpy
import json

result = []

for obj in bpy.data.objects:
    obj_info = {
        "name": obj.name,
        "type": obj.type,
        "location": list(obj.location),
        "rotation": [round(r, 4) for r in obj.rotation_euler],
        "scale": list(obj.scale),
        "collection": None,
        "modifiers": [],
        "materials": []
    }
    
    # Get collection
    for col in bpy.data.collections:
        if obj.name in col.objects:
            obj_info["collection"] = col.name
            break
    
    # Get modifiers
    for mod in obj.modifiers:
        mod_info = {"name": mod.name, "type": mod.type}
        if mod.type == "NODES" and mod.node_group:
            mod_info["node_group"] = mod.node_group.name
        obj_info["modifiers"].append(mod_info)
    
    # Get materials
    if hasattr(obj, "material_slots"):
        for slot in obj.material_slots:
            if slot.material:
                obj_info["materials"].append(slot.material.name)
    
    result.append(obj_info)

print(json.dumps(result))
'''
        result = self.bridge.execute_blender_code(code)
        try:
            import json
            return json.loads(result.strip())
        except Exception:
            return []

    def analyze_collections(self) -> List[Dict[str, Any]]:
        """Analyze all collections in the scene"""
        code = '''
import bpy
import json

result = []

def analyze_collection(col, parent=None):
    col_info = {
        "name": col.name,
        "parent": parent,
        "object_count": len(col.objects),
        "objects": [obj.name for obj in col.objects],
        "children": [c.name for c in col.children]
    }
    result.append(col_info)
    
    for child in col.children:
        analyze_collection(child, col.name)

# Start with scene collection
scene_col = bpy.context.scene.collection
analyze_collection(scene_col)

print(json.dumps(result))
'''
        result = self.bridge.execute_blender_code(code)
        try:
            import json
            return json.loads(result.strip())
        except Exception:
            return []

    def full_analysis(self, include_values: bool = True) -> Dict[str, Any]:
        """Perform a complete scene analysis"""
        analysis = {
            "geometry_nodes": self.analyze_geometry_nodes(),
            "materials": self.analyze_materials(),
            "objects": self.analyze_objects(),
            "collections": self.analyze_collections()
        }
        
        # Add current parameter values for each geometry node group
        if include_values:
            for gn in analysis["geometry_nodes"]:
                gn["current_values"] = {}
                for obj_name in gn["used_by"]:
                    values = self.get_modifier_values(obj_name, gn["name"])
                    if values:
                        gn["current_values"][obj_name] = values
        
        return analysis

    def print_report(self, analysis: Dict[str, Any] = None) -> str:
        """Generate a human-readable report of the scene"""
        if analysis is None:
            analysis = self.full_analysis()
        
        lines = []
        lines.append("=" * 60)
        lines.append("BLENDER SCENE ANALYSIS REPORT")
        lines.append("=" * 60)
        
        # Geometry Node Groups
        lines.append("\n📦 GEOMETRY NODE GROUPS")
        lines.append("-" * 40)
        
        for gn in analysis.get("geometry_nodes", []):
            lines.append(f"\n  {gn['name']}")
            lines.append(f"    Nodes: {gn['node_count']}, Links: {gn['link_count']}")
            lines.append(f"    Used by: {', '.join(gn['used_by']) or 'None'}")
            
            # Show frames if present
            if gn.get("frames"):
                lines.append("    Frames:")
                for frame in gn["frames"]:
                    lines.append(f"      - {frame['label']} ({frame['node_count']} nodes)")
            
            if gn.get("parameters"):
                lines.append("    Parameters:")
                for param in gn["parameters"]:
                    ptype = param["socket_type"].replace("NodeSocket", "")
                    default = param.get("default", "?")
                    lines.append(f"      - {param['name']} ({ptype}): default={default}")
            
            # Show current values per object
            if gn.get("current_values"):
                for obj_name, values in gn["current_values"].items():
                    lines.append(f"    Current values on '{obj_name}':")
                    for name, val in values.items():
                        if isinstance(val, float):
                            lines.append(f"      {name}: {val:.4f}")
                        else:
                            lines.append(f"      {name}: {val}")
        
        # Materials
        lines.append("\n\n🎨 MATERIALS")
        lines.append("-" * 40)
        
        for mat in analysis.get("materials", []):
            lines.append(f"\n  {mat['name']}")
            lines.append(f"    Nodes: {mat['node_count']}, Blend: {mat['blend_method']}")
            lines.append(f"    Used by: {', '.join(mat['used_by']) or 'None'}")
            if mat.get("shader_nodes"):
                nodes_summary = ", ".join(set(mat["shader_nodes"][:5]))
                if len(mat["shader_nodes"]) > 5:
                    nodes_summary += f" (+{len(mat['shader_nodes']) - 5} more)"
                lines.append(f"    Shader types: {nodes_summary}")
        
        # Collections
        lines.append("\n\n📁 COLLECTIONS")
        lines.append("-" * 40)
        
        for col in analysis.get("collections", []):
            indent = "  " if col["parent"] is None else "    "
            lines.append(f"{indent}{col['name']} ({col['object_count']} objects)")
        
        # Objects Summary
        lines.append("\n\n🎯 OBJECTS SUMMARY")
        lines.append("-" * 40)
        
        # Group by type
        by_type = {}
        for obj in analysis.get("objects", []):
            obj_type = obj["type"]
            if obj_type not in by_type:
                by_type[obj_type] = []
            by_type[obj_type].append(obj)
        
        for obj_type, objects in by_type.items():
            lines.append(f"\n  {obj_type} ({len(objects)})")
            for obj in objects[:10]:  # Limit to 10 per type
                mods = [m["name"] for m in obj["modifiers"]]
                mats = obj["materials"]
                details = []
                if mods:
                    details.append(f"mods: {', '.join(mods)}")
                if mats:
                    details.append(f"mats: {', '.join(mats)}")
                detail_str = f" [{'; '.join(details)}]" if details else ""
                lines.append(f"    - {obj['name']}{detail_str}")
            if len(objects) > 10:
                lines.append(f"    ... and {len(objects) - 10} more")
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)

    def export_to_markdown(self, filepath: str = None) -> str:
        """Export the analysis to a markdown file"""
        analysis = self.full_analysis()
        
        lines = []
        lines.append("# Blender Scene Analysis Report\n")
        
        # Geometry Nodes Section
        lines.append("## Geometry Node Groups\n")
        
        for gn in analysis.get("geometry_nodes", []):
            lines.append(f"### {gn['name']}\n")
            lines.append(f"- **Nodes:** {gn['node_count']}")
            lines.append(f"- **Links:** {gn['link_count']}")
            lines.append(f"- **Used by:** {', '.join(gn['used_by']) or 'None'}\n")
            
            if gn.get("parameters"):
                lines.append("#### Parameters\n")
                lines.append("| Name | Socket ID | Type | Default |")
                lines.append("|------|-----------|------|---------|")
                for param in gn["parameters"]:
                    ptype = param["socket_type"].replace("NodeSocket", "")
                    default = param.get("default", "-")
                    if isinstance(default, list):
                        default = str([round(v, 2) if isinstance(v, float) else v for v in default])
                    lines.append(f"| {param['name']} | {param['socket_id']} | {ptype} | {default} |")
                lines.append("")
            
            if gn.get("current_values"):
                lines.append("#### Current Values\n")
                for obj_name, values in gn["current_values"].items():
                    lines.append(f"**{obj_name}:**\n")
                    lines.append("| Parameter | Value |")
                    lines.append("|-----------|-------|")
                    for name, val in values.items():
                        if isinstance(val, float):
                            lines.append(f"| {name} | {val:.4f} |")
                        else:
                            lines.append(f"| {name} | {val} |")
                    lines.append("")
        
        # Materials Section
        lines.append("## Materials\n")
        
        for mat in analysis.get("materials", []):
            lines.append(f"### {mat['name']}\n")
            lines.append(f"- **Node count:** {mat['node_count']}")
            lines.append(f"- **Blend method:** {mat['blend_method']}")
            lines.append(f"- **Used by:** {', '.join(mat['used_by']) or 'None'}\n")
        
        # Objects Section
        lines.append("## Objects\n")
        
        by_type = {}
        for obj in analysis.get("objects", []):
            obj_type = obj["type"]
            if obj_type not in by_type:
                by_type[obj_type] = []
            by_type[obj_type].append(obj)
        
        for obj_type, objects in by_type.items():
            lines.append(f"### {obj_type} ({len(objects)})\n")
            lines.append("| Name | Location | Modifiers | Materials |")
            lines.append("|------|----------|-----------|-----------|")
            for obj in objects:
                loc = f"({obj['location'][0]:.1f}, {obj['location'][1]:.1f}, {obj['location'][2]:.1f})"
                mods = ", ".join([m["name"] for m in obj["modifiers"]]) or "-"
                mats = ", ".join(obj["materials"]) or "-"
                lines.append(f"| {obj['name']} | {loc} | {mods} | {mats} |")
            lines.append("")
        
        content = "\n".join(lines)
        
        if filepath:
            with open(filepath, 'w') as f:
                f.write(content)
            return f"Report exported to {filepath}"
        
        return content


def analyze_scene(output_format: str = "text", filepath: str = None) -> str:
    """
    Convenience function to analyze the current Blender scene.
    
    Args:
        output_format: "text" for console output, "markdown" for markdown format
        filepath: Optional path to save the report
    
    Returns:
        The analysis report as a string
    """
    analyzer = SceneAnalyzer()
    
    if output_format == "markdown":
        return analyzer.export_to_markdown(filepath)
    else:
        analysis = analyzer.full_analysis()
        report = analyzer.print_report(analysis)
        
        if filepath:
            with open(filepath, 'w') as f:
                f.write(report)
            return f"Report saved to {filepath}\n\n{report}"
        
        return report


def quick_geonodes_summary() -> str:
    """Get a quick summary of geometry nodes in the scene"""
    analyzer = SceneAnalyzer()
    gn_data = analyzer.analyze_geometry_nodes()
    
    lines = ["Geometry Node Groups:"]
    for gn in gn_data:
        lines.append(f"  {gn['name']}: {gn['node_count']} nodes, {len(gn['parameters'])} params")
        if gn['used_by']:
            lines.append(f"    Used by: {', '.join(gn['used_by'])}")
        if gn.get('frames'):
            lines.append(f"    Frames: {', '.join([f['label'] for f in gn['frames']])}")
    
    return "\n".join(lines)


def inspect_frame(node_group_name: str, frame_label: str = None) -> str:
    """
    Inspect a specific frame or all frames in a geometry node group.
    
    Use this when you've wrapped nodes in a frame labeled "look here" or similar
    to get detailed information about those specific nodes.
    
    Args:
        node_group_name: Name of the geometry node group (e.g., "PlantSystem")
        frame_label: Optional label to filter (e.g., "look here"). Case-insensitive partial match.
    
    Returns:
        Detailed report of the frame(s) and their contents
    """
    analyzer = SceneAnalyzer()
    frames = analyzer.get_frame_details(node_group_name, frame_label)
    
    if not frames:
        return f"No frames found in '{node_group_name}'" + (f" matching '{frame_label}'" if frame_label else "")
    
    lines = []
    for frame in frames:
        lines.append("=" * 60)
        lines.append(f"FRAME: {frame['label']}")
        if frame.get('color'):
            lines.append(f"Color: RGB({frame['color'][0]:.2f}, {frame['color'][1]:.2f}, {frame['color'][2]:.2f})")
        lines.append("=" * 60)
        
        lines.append(f"\n📦 NODES ({len(frame['nodes'])}):")
        for node in frame['nodes']:
            lines.append(f"\n  [{node['type']}] {node['name']}")
            if node['label'] != node['name']:
                lines.append(f"    Label: {node['label']}")
            
            # Show inputs with values
            if node['inputs']:
                connected_inputs = [i for i in node['inputs'] if i.get('connected')]
                value_inputs = [i for i in node['inputs'] if not i.get('connected') and 'value' in i]
                
                if connected_inputs:
                    lines.append(f"    Inputs (connected): {', '.join([i['name'] for i in connected_inputs])}")
                if value_inputs:
                    for inp in value_inputs[:3]:  # Limit to first 3
                        val = inp['value']
                        if isinstance(val, float):
                            lines.append(f"    {inp['name']}: {val:.4f}")
                        elif isinstance(val, list):
                            lines.append(f"    {inp['name']}: {[round(v, 2) if isinstance(v, float) else v for v in val]}")
                        else:
                            lines.append(f"    {inp['name']}: {val}")
            
            # Show outputs
            if node['outputs']:
                connected_outputs = [o for o in node['outputs'] if o.get('connected')]
                if connected_outputs:
                    lines.append(f"    Outputs (connected): {', '.join([o['name'] for o in connected_outputs])}")
        
        # Show internal connections
        if frame.get('internal_links'):
            lines.append(f"\n🔗 INTERNAL CONNECTIONS ({len(frame['internal_links'])}):")
            for link in frame['internal_links'][:10]:  # Limit display
                lines.append(f"    {link['from']} → {link['to']}")
            if len(frame['internal_links']) > 10:
                lines.append(f"    ... and {len(frame['internal_links']) - 10} more")
        
        # Show external connections
        if frame.get('incoming_links'):
            lines.append(f"\n⬇️ INCOMING ({len(frame['incoming_links'])}):")
            for link in frame['incoming_links'][:5]:
                lines.append(f"    {link['from']} → {link['to']}")
        
        if frame.get('outgoing_links'):
            lines.append(f"\n⬆️ OUTGOING ({len(frame['outgoing_links'])}):")
            for link in frame['outgoing_links'][:5]:
                lines.append(f"    {link['from']} → {link['to']}")
        
        lines.append("")
    
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze Blender scene")
    parser.add_argument("--format", choices=["text", "markdown"], default="text",
                        help="Output format")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--quick", action="store_true",
                        help="Quick geometry nodes summary only")
    
    args = parser.parse_args()
    
    if args.quick:
        print(quick_geonodes_summary())
    else:
        print(analyze_scene(args.format, args.output))
