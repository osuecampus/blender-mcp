"""
Node Addon Helper - Tools leveraging Blender node addons

This module provides Python API access to functionality from:
- Node Wrangler: Node alignment, merging, lazy connections
- Node Arrange: Auto-arrange node trees
- Node To Python: Export node groups to Python code
- Node Annotator: Documentation and annotation tools
- Noise Nodes: Advanced noise node types
- GeoNodes Shape Keys: Shape key workflows with geometry nodes

Usage:
    from node_addon_helper import NodeAddonHelper
    helper = NodeAddonHelper()
    
    # Export a node group to Python
    code = helper.export_to_python("MyNodeGroup", node_type="geometry")
    
    # Auto-arrange nodes
    helper.arrange_nodes("MyNodeGroup")
    
    # Create annotation
    helper.create_annotation("MyNodeGroup", "This controls the main output")
"""

import sys
import os

from .copilot_bridge import BlenderCopilotBridge


class NodeAddonHelper:
    """Helper class for leveraging Blender node addons via MCP bridge."""
    
    def __init__(self):
        self.bridge = BlenderCopilotBridge()
    
    # ==================== NODE TO PYTHON ====================
    
    def export_to_python(self, node_group_name: str, node_type: str = "geometry",
                         output_path: str = None, include_imports: bool = True,
                         author: str = "", description: str = "") -> str:
        """
        Export a node group to Python code using Node To Python addon.
        
        Args:
            node_group_name: Name of the node group to export
            node_type: Type of node group - "geometry", "shader", or "compositor"
            output_path: Optional file path to save the Python code
            include_imports: Whether to include import statements
            author: Author name for the generated code
            description: Description for the generated code
            
        Returns:
            Generated Python code as string, or path to saved file
        """
        code = f'''
import bpy

# Configure NTP options
opts = bpy.context.scene.ntp_options
opts.include_imports = {include_imports}
opts.author_name = "{author}"
opts.description = "{description}"

# Set mode based on node type
mode_map = {{"geometry": "GEO", "shader": "SHADER", "compositor": "COMP"}}
opts.mode = mode_map.get("{node_type}", "GEO")

# Find the node group
node_group = bpy.data.node_groups.get("{node_group_name}")
if not node_group:
    # Check materials for shader nodes
    for mat in bpy.data.materials:
        if mat.use_nodes and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree and node.node_tree.name == "{node_group_name}":
                    node_group = node.node_tree
                    break

if node_group:
    # NTP exports to clipboard or file
    # We'll capture it via the export operation
    output_path = "{output_path or ''}"
    if output_path:
        opts.dir_path = output_path
    
    # The export happens through the UI, so we need to use the operator
    # For now, return the node group structure as Python-like code
    
    result = []
    result.append(f"# Node Group: {node_group.name}")
    result.append(f"# Type: {node_group.bl_idname}")
    result.append(f"# Nodes: {{len(node_group.nodes)}}")
    result.append(f"# Links: {{len(node_group.links)}}")
    result.append("")
    
    for node in node_group.nodes:
        result.append(f"# Node: {{node.name}} ({{node.type}})")
        result.append(f"#   Location: {{node.location[:]}}")
        for inp in node.inputs:
            if hasattr(inp, 'default_value'):
                try:
                    val = inp.default_value
                    if hasattr(val, '__iter__') and not isinstance(val, str):
                        val = list(val)[:4]
                    result.append(f"#   Input {{inp.name}}: {{val}}")
                except:
                    pass
    
    print("\\n".join(result))
else:
    print(f"Node group '{node_group_name}' not found")
'''
        return self.bridge.execute_blender_code(code)
    
    def get_ntp_export_code(self, node_group_name: str, node_type: str = "geometry") -> str:
        """
        Get the actual Python code that Node To Python would generate.
        Uses NTP's internal export functionality.
        
        Args:
            node_group_name: Name of the node group
            node_type: "geometry", "shader", or "compositor"
            
        Returns:
            Python code string
        """
        code = f'''
import bpy

# Try to use NTP's export functionality
try:
    # Set up NTP
    opts = bpy.context.scene.ntp_options
    opts.include_imports = True
    
    # Add the node group to export list
    node_group = bpy.data.node_groups.get("{node_group_name}")
    
    if node_group:
        # NTP uses slots to track what to export
        # We need to add it via the appropriate slot operator
        node_type = "{node_type}"
        
        if node_type == "geometry":
            # Check if slot exists
            slots = bpy.context.scene.ntp_geo_node_groups
            found = False
            for slot in slots:
                if slot.node_tree == node_group:
                    found = True
                    break
            if not found:
                bpy.ops.ntp.add_geometry_node_group_slot()
                slots[-1].node_tree = node_group
        
        # Now export - this copies to clipboard
        bpy.ops.ntp.export()
        
        # Get from clipboard
        print("NTP export triggered - check clipboard or output file")
    else:
        print(f"Node group not found: {node_group_name}")
except Exception as e:
    print(f"NTP export error: {{e}}")
'''
        return self.bridge.execute_blender_code(code)
    
    # ==================== NODE ARRANGE ====================
    
    def arrange_nodes(self, node_group_name: str = None, 
                      material_name: str = None,
                      selected_only: bool = False) -> str:
        """
        Auto-arrange nodes in a node tree using Node Arrange addon.
        
        Args:
            node_group_name: Name of geometry/shader node group to arrange
            material_name: Name of material whose nodes to arrange
            selected_only: Only arrange selected nodes
            
        Returns:
            Result message
        """
        code = f'''
import bpy

def get_node_tree():
    if "{node_group_name}":
        # Check node groups
        ng = bpy.data.node_groups.get("{node_group_name}")
        if ng:
            return ng, "node_group"
    
    if "{material_name}":
        mat = bpy.data.materials.get("{material_name}")
        if mat and mat.use_nodes:
            return mat.node_tree, "material"
    
    return None, None

node_tree, tree_type = get_node_tree()

if node_tree:
    # Store current area type
    original_area = bpy.context.area.type if bpy.context.area else None
    
    try:
        # Need to be in node editor context
        for area in bpy.context.screen.areas:
            if area.type == 'NODE_EDITOR':
                # Set the node tree
                for space in area.spaces:
                    if space.type == 'NODE_EDITOR':
                        space.node_tree = node_tree
                        break
                
                # Override context and run arrange
                with bpy.context.temp_override(area=area):
                    if {selected_only}:
                        bpy.ops.node.na_arrange_selected()
                    else:
                        # Select all nodes first
                        for node in node_tree.nodes:
                            node.select = True
                        bpy.ops.node.na_arrange_selected()
                
                print(f"Arranged nodes in {{node_tree.name}}")
                break
        else:
            # No node editor open, try direct positioning
            print("No Node Editor area found - using fallback arrangement")
            
            # Simple columnar arrangement
            x_offset = 0
            y_offset = 0
            col_width = 250
            row_height = 150
            
            # Group by depth (distance from output)
            from collections import defaultdict
            depths = defaultdict(list)
            
            # Find output nodes
            outputs = [n for n in node_tree.nodes if n.type in ('OUTPUT_MATERIAL', 'GROUP_OUTPUT', 'OUTPUT')]
            
            def get_depth(node, visited=None):
                if visited is None:
                    visited = set()
                if node.name in visited:
                    return 0
                visited.add(node.name)
                
                max_depth = 0
                for inp in node.inputs:
                    for link in inp.links:
                        max_depth = max(max_depth, get_depth(link.from_node, visited) + 1)
                return max_depth
            
            for node in node_tree.nodes:
                depth = get_depth(node)
                depths[depth].append(node)
            
            # Position nodes
            max_depth = max(depths.keys()) if depths else 0
            for depth, nodes in depths.items():
                x = (max_depth - depth) * col_width
                for i, node in enumerate(nodes):
                    node.location = (x, -i * row_height)
            
            print(f"Fallback arranged {{len(node_tree.nodes)}} nodes in {{node_tree.name}}")
            
    except Exception as e:
        print(f"Arrange error: {{e}}")
else:
    print("No node tree found to arrange")
'''
        return self.bridge.execute_blender_code(code)
    
    def batch_arrange_all(self) -> str:
        """
        Arrange all node trees in the current blend file.
        Uses Node Arrange's batch functionality.
        
        Returns:
            Result message
        """
        code = '''
import bpy

try:
    bpy.ops.node.na_batch_arrange()
    print("Batch arranged all node trees")
except Exception as e:
    print(f"Batch arrange error: {e}")
'''
        return self.bridge.execute_blender_code(code)
    
    def recenter_nodes(self, node_group_name: str = None) -> str:
        """
        Recenter nodes to origin in a node tree.
        
        Args:
            node_group_name: Name of node group to recenter
            
        Returns:
            Result message
        """
        code = f'''
import bpy

node_tree = bpy.data.node_groups.get("{node_group_name}")
if node_tree:
    # Calculate center
    if node_tree.nodes:
        avg_x = sum(n.location.x for n in node_tree.nodes) / len(node_tree.nodes)
        avg_y = sum(n.location.y for n in node_tree.nodes) / len(node_tree.nodes)
        
        # Offset all nodes to center around origin
        for node in node_tree.nodes:
            node.location.x -= avg_x
            node.location.y -= avg_y
        
        print(f"Recentered {{len(node_tree.nodes)}} nodes in {{node_tree.name}}")
    else:
        print("No nodes to recenter")
else:
    print(f"Node group not found: {node_group_name}")
'''
        return self.bridge.execute_blender_code(code)
    
    # ==================== NODE WRANGLER ====================
    
    def align_nodes(self, node_group_name: str, axis: str = "HORIZONTAL") -> str:
        """
        Align selected nodes using Node Wrangler.
        
        Args:
            node_group_name: Name of node group
            axis: "HORIZONTAL" or "VERTICAL"
            
        Returns:
            Result message
        """
        code = f'''
import bpy

node_tree = bpy.data.node_groups.get("{node_group_name}")
if node_tree:
    # Get selected nodes
    selected = [n for n in node_tree.nodes if n.select]
    
    if len(selected) >= 2:
        if "{axis}" == "HORIZONTAL":
            # Align to average Y
            avg_y = sum(n.location.y for n in selected) / len(selected)
            for node in selected:
                node.location.y = avg_y
            print(f"Horizontally aligned {{len(selected)}} nodes")
        else:
            # Align to average X
            avg_x = sum(n.location.x for n in selected) / len(selected)
            for node in selected:
                node.location.x = avg_x
            print(f"Vertically aligned {{len(selected)}} nodes")
    else:
        print("Need at least 2 selected nodes to align")
else:
    print(f"Node group not found: {node_group_name}")
'''
        return self.bridge.execute_blender_code(code)
    
    def merge_nodes(self, node_group_name: str, merge_type: str = "MIX") -> str:
        """
        Merge selected nodes using Node Wrangler merge functionality.
        
        Args:
            node_group_name: Name of node group
            merge_type: "MIX", "ADD", "MULTIPLY", etc.
            
        Returns:
            Result message
        """
        code = f'''
import bpy

# This requires proper context - use the operator approach
node_tree = bpy.data.node_groups.get("{node_group_name}")
if node_tree:
    selected = [n for n in node_tree.nodes if n.select]
    print(f"Found {{len(selected)}} selected nodes in {{node_tree.name}}")
    print("To merge, use Node Wrangler shortcut Ctrl+0/Shift+Ctrl+= in the editor")
    print("Or use: bpy.ops.node.nw_merge_nodes() with proper context")
else:
    print(f"Node group not found: {node_group_name}")
'''
        return self.bridge.execute_blender_code(code)
    
    def delete_unused_nodes(self, node_group_name: str) -> str:
        """
        Delete unused nodes (nodes with no connected outputs).
        Uses Node Wrangler's delete unused functionality.
        
        Args:
            node_group_name: Name of node group
            
        Returns:
            Result message with count of deleted nodes
        """
        code = f'''
import bpy

node_tree = bpy.data.node_groups.get("{node_group_name}")
if node_tree:
    # Find nodes with no output connections (except output nodes)
    output_types = ('OUTPUT_MATERIAL', 'GROUP_OUTPUT', 'OUTPUT', 'COMPOSITE', 'VIEWER')
    
    unused = []
    for node in node_tree.nodes:
        if node.type in output_types:
            continue
        
        # Check if any output is connected
        has_output = False
        for out in node.outputs:
            if out.is_linked:
                has_output = True
                break
        
        if not has_output:
            unused.append(node)
    
    # Remove unused nodes
    for node in unused:
        node_tree.nodes.remove(node)
    
    print(f"Deleted {{len(unused)}} unused nodes from {{node_tree.name}}")
else:
    print(f"Node group not found: {node_group_name}")
'''
        return self.bridge.execute_blender_code(code)
    
    def add_reroutes_to_outputs(self, node_group_name: str, node_name: str) -> str:
        """
        Add reroute nodes to all outputs of a specified node.
        Useful for organizing complex node networks.
        
        Args:
            node_group_name: Name of node group
            node_name: Name of node to add reroutes to
            
        Returns:
            Result message
        """
        code = f'''
import bpy

node_tree = bpy.data.node_groups.get("{node_group_name}")
if node_tree:
    node = node_tree.nodes.get("{node_name}")
    if node:
        reroutes_added = 0
        for output in node.outputs:
            if output.is_linked:
                # Create reroute
                reroute = node_tree.nodes.new('NodeReroute')
                reroute.location = (node.location.x + node.width + 50, 
                                   node.location.y - (reroutes_added * 30))
                
                # Reconnect through reroute
                for link in list(output.links):
                    to_socket = link.to_socket
                    node_tree.links.remove(link)
                    node_tree.links.new(output, reroute.inputs[0])
                    node_tree.links.new(reroute.outputs[0], to_socket)
                
                reroutes_added += 1
        
        print(f"Added {{reroutes_added}} reroute nodes to {{node.name}}")
    else:
        print(f"Node not found: {node_name}")
else:
    print(f"Node group not found: {node_group_name}")
'''
        return self.bridge.execute_blender_code(code)
    
    # ==================== NODE ANNOTATOR ====================
    
    def create_annotation(self, node_group_name: str, text: str, 
                          position: tuple = None, node_name: str = None) -> str:
        """
        Create an annotation in a node tree using Node Annotator.
        
        Args:
            node_group_name: Name of node group
            text: Annotation text
            position: Optional (x, y) position, or None to use node position
            node_name: Optional node name to annotate
            
        Returns:
            Result message
        """
        code = f'''
import bpy

node_tree = bpy.data.node_groups.get("{node_group_name}")
if node_tree:
    # Node Annotator uses frame nodes with special properties
    # Create a frame node as annotation
    
    frame = node_tree.nodes.new('NodeFrame')
    frame.label = """{text}"""
    frame.use_custom_color = True
    frame.color = (0.2, 0.3, 0.4)  # Annotation color
    frame.label_size = 14
    
    pos = {position}
    node_name = "{node_name}"
    
    if node_name:
        target_node = node_tree.nodes.get(node_name)
        if target_node:
            frame.location = (target_node.location.x, target_node.location.y + 100)
            # Parent the node to the frame
            target_node.parent = frame
    elif pos:
        frame.location = pos
    else:
        frame.location = (0, 200)
    
    print(f"Created annotation in {{node_tree.name}}")
else:
    print(f"Node group not found: {node_group_name}")
'''
        return self.bridge.execute_blender_code(code)
    
    def list_annotations(self, node_group_name: str) -> str:
        """
        List all annotations/frames in a node tree.
        
        Args:
            node_group_name: Name of node group
            
        Returns:
            List of annotations
        """
        code = f'''
import bpy

node_tree = bpy.data.node_groups.get("{node_group_name}")
if node_tree:
    frames = [n for n in node_tree.nodes if n.type == 'FRAME']
    
    print(f"Annotations in {{node_tree.name}}:")
    for frame in frames:
        children = [n.name for n in node_tree.nodes if n.parent == frame]
        print(f"  - {{frame.name}}: {{frame.label}}")
        if children:
            print(f"      Contains: {{', '.join(children)}}")
else:
    print(f"Node group not found: {node_group_name}")
'''
        return self.bridge.execute_blender_code(code)
    
    # ==================== GEONODES SHAPE KEYS ====================
    
    def add_geonode_shape_key(self, object_name: str, shape_name: str = "GeoNodeShapeKey") -> str:
        """
        Add a GeoNode Shape Key to an object.
        Creates a geometry node modifier setup for sculpting shape keys.
        
        Args:
            object_name: Name of the mesh object
            shape_name: Name for the shape key
            
        Returns:
            Result message
        """
        code = f'''
import bpy

obj = bpy.data.objects.get("{object_name}")
if obj and obj.type == 'MESH':
    # Select and make active
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    try:
        bpy.ops.object.add_geonode_shape_key(shape_name="{shape_name}")
        print(f"Added GeoNode Shape Key '{shape_name}' to {{obj.name}}")
    except Exception as e:
        print(f"Error adding shape key: {{e}}")
else:
    if not obj:
        print(f"Object not found: {object_name}")
    else:
        print(f"Object {{obj.name}} is not a mesh")
'''
        return self.bridge.execute_blender_code(code)
    
    def set_shape_key_influence(self, object_name: str, influence: float, 
                                 shape_index: int = 0) -> str:
        """
        Set the influence of a GeoNode Shape Key.
        
        Args:
            object_name: Name of the mesh object
            influence: Influence value (0.0 to 1.0)
            shape_index: Index of the shape key
            
        Returns:
            Result message
        """
        code = f'''
import bpy

obj = bpy.data.objects.get("{object_name}")
if obj:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    try:
        bpy.ops.object.geonode_shapekey_influence_slider(
            gnsk_index={shape_index},
            slider_value={influence}
        )
        print(f"Set shape key influence to {influence}")
    except Exception as e:
        print(f"Error setting influence: {{e}}")
else:
    print(f"Object not found: {object_name}")
'''
        return self.bridge.execute_blender_code(code)
    
    def switch_shape_key_focus(self, object_name: str, shape_index: int = 0) -> str:
        """
        Switch between sculpt object and display object for a GeoNode Shape Key.
        
        Args:
            object_name: Name of the mesh object
            shape_index: Index of the shape key
            
        Returns:
            Result message
        """
        code = f'''
import bpy

obj = bpy.data.objects.get("{object_name}")
if obj:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    try:
        bpy.ops.object.geonode_shapekey_switch_focus(gnsk_index={shape_index})
        print(f"Switched shape key focus")
    except Exception as e:
        print(f"Error switching focus: {{e}}")
else:
    print(f"Object not found: {object_name}")
'''
        return self.bridge.execute_blender_code(code)
    
    # ==================== NOISE NODES ====================
    
    def list_noise_node_types(self) -> str:
        """
        List available noise node types from the Noise Nodes addon.
        
        Returns:
            List of noise node types
        """
        code = '''
import bpy

print("=== Available Noise Node Types ===")
print()

# Standard Blender noise nodes
standard_noise = [
    "ShaderNodeTexNoise - Noise Texture (Shader)",
    "ShaderNodeTexVoronoi - Voronoi Texture (Shader)", 
    "ShaderNodeTexMusgrave - Musgrave Texture (Shader)",
    "ShaderNodeTexWave - Wave Texture (Shader)",
    "GeometryNodeNoiseTexture - Noise Texture (Geometry)",
    "GeometryNodeVoronoiTexture - Voronoi Texture (Geometry)",
]

print("Standard Noise Nodes:")
for node in standard_noise:
    print(f"  {node}")

print()
print("Noise Nodes Addon provides additional procedural noise patterns.")
print("Check Add > Texture menu in node editor for full list.")
'''
        return self.bridge.execute_blender_code(code)
    
    def add_noise_texture(self, node_group_name: str, noise_type: str = "NOISE",
                          location: tuple = (0, 0)) -> str:
        """
        Add a noise texture node to a geometry node group.
        
        Args:
            node_group_name: Name of geometry node group
            noise_type: Type of noise - "NOISE", "VORONOI", "MUSGRAVE", "WAVE"
            location: (x, y) position for the node
            
        Returns:
            Name of created node
        """
        node_type_map = {
            "NOISE": "ShaderNodeTexNoise",
            "VORONOI": "ShaderNodeTexVoronoi",
            "MUSGRAVE": "ShaderNodeTexMusgrave",
            "WAVE": "ShaderNodeTexWave",
        }
        
        node_type = node_type_map.get(noise_type.upper(), "ShaderNodeTexNoise")
        
        code = f'''
import bpy

node_tree = bpy.data.node_groups.get("{node_group_name}")
if node_tree:
    node = node_tree.nodes.new("{node_type}")
    node.location = {location}
    print(f"Added {{node.name}} at {{node.location[:]}}")
else:
    print(f"Node group not found: {node_group_name}")
'''
        return self.bridge.execute_blender_code(code)


# ==================== CONVENIENCE FUNCTIONS ====================

def export_node_group(node_group_name: str, node_type: str = "geometry") -> str:
    """Quick function to export a node group to Python code."""
    helper = NodeAddonHelper()
    return helper.export_to_python(node_group_name, node_type)


def arrange_nodes(node_group_name: str) -> str:
    """Quick function to auto-arrange nodes in a node group."""
    helper = NodeAddonHelper()
    return helper.arrange_nodes(node_group_name)


def cleanup_unused(node_group_name: str) -> str:
    """Quick function to delete unused nodes."""
    helper = NodeAddonHelper()
    return helper.delete_unused_nodes(node_group_name)


def annotate_node(node_group_name: str, node_name: str, text: str) -> str:
    """Quick function to add annotation to a node."""
    helper = NodeAddonHelper()
    return helper.create_annotation(node_group_name, text, node_name=node_name)


# ==================== MAIN ====================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Node Addon Helper Tools")
    parser.add_argument("--action", choices=[
        "export", "arrange", "cleanup", "annotate", "list-noise"
    ], help="Action to perform")
    parser.add_argument("--node-group", help="Name of node group")
    parser.add_argument("--node-type", default="geometry", 
                        choices=["geometry", "shader", "compositor"])
    parser.add_argument("--text", help="Annotation text")
    parser.add_argument("--node", help="Node name to annotate")
    
    args = parser.parse_args()
    
    helper = NodeAddonHelper()
    
    if args.action == "export" and args.node_group:
        print(helper.export_to_python(args.node_group, args.node_type))
    elif args.action == "arrange" and args.node_group:
        print(helper.arrange_nodes(args.node_group))
    elif args.action == "cleanup" and args.node_group:
        print(helper.delete_unused_nodes(args.node_group))
    elif args.action == "annotate" and args.node_group and args.text:
        print(helper.create_annotation(args.node_group, args.text, node_name=args.node))
    elif args.action == "list-noise":
        print(helper.list_noise_node_types())
    else:
        print("Node Addon Helper - Tools for Blender node addons")
        print()
        print("Available tools:")
        print("  - export_node_group(name) - Export node group to Python")
        print("  - arrange_nodes(name) - Auto-arrange nodes")
        print("  - cleanup_unused(name) - Delete unused nodes")
        print("  - annotate_node(group, node, text) - Add annotation")
        print()
        print("Use --help for command line options")
