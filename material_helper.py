#!/usr/bin/env python3
"""
Material Helpers for BlenderMCP
Provides utilities for creating and modifying shader materials, including
connecting geometry node attributes to shader inputs.
"""

from typing import Dict, List, Any, Optional, Tuple
from copilot_bridge import BlenderCopilotBridge


class MaterialHelper:
    """Helper class for creating and modifying shader materials"""

    def __init__(self, host='127.0.0.1', port=9876):
        self.bridge = BlenderCopilotBridge(host, port)

    def connect_attribute_to_shader(
        self,
        material_name: str,
        attribute_name: str,
        target_node: str,
        target_input: str,
        attribute_type: str = "FAC",
        create_if_missing: bool = True
    ) -> Dict[str, Any]:
        """
        Connect a geometry nodes named attribute to a shader input.
        
        Creates an Attribute node that reads the named attribute and connects
        its output to the specified shader node input.
        
        Args:
            material_name: Name of the material to modify
            attribute_name: Name of the attribute to read (e.g., "hydration", "clodScale")
            target_node: Name of the shader node to connect to (e.g., "Principled BSDF", "Mix")
            target_input: Name of the input socket on target node (e.g., "Factor", "Roughness")
            attribute_type: Output type to use - "FAC" for float, "COLOR" for vector, "ALPHA" for alpha
            create_if_missing: If True, create the Attribute node if it doesn't exist
        
        Returns:
            Dict with success status, created node name, and connection details
        """
        code = f'''
import bpy

result = {{"success": False, "attr_node": None, "connection": None, "message": ""}}

mat = bpy.data.materials.get("{material_name}")
if not mat:
    result["message"] = "Material not found: {material_name}"
elif not mat.use_nodes:
    result["message"] = "Material does not use nodes: {material_name}"
else:
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Find target node
    target = nodes.get("{target_node}")
    if not target:
        result["message"] = "Target node not found: {target_node}"
    else:
        # Find target input
        target_input = target.inputs.get("{target_input}")
        if not target_input:
            result["message"] = "Target input not found: {target_input} on {target_node}"
        else:
            # Look for existing attribute node with this name
            attr_node = None
            for node in nodes:
                if node.type == "ATTRIBUTE" and node.attribute_name == "{attribute_name}":
                    attr_node = node
                    break
            
            # Create if not found and allowed
            if not attr_node:
                if {str(create_if_missing).lower()}:
                    attr_node = nodes.new("ShaderNodeAttribute")
                    attr_node.attribute_name = "{attribute_name}"
                    attr_node.name = "Attr_{attribute_name}"
                    attr_node.label = "{attribute_name}"
                    # Position near target node
                    attr_node.location = (target.location[0] - 300, target.location[1])
                    result["attr_node"] = attr_node.name
                else:
                    result["message"] = "Attribute node not found and create_if_missing=False"
            else:
                result["attr_node"] = attr_node.name
            
            if attr_node:
                # Determine output socket
                output_name = "{attribute_type.upper()}"
                if output_name == "FAC":
                    output_socket = attr_node.outputs.get("Fac")
                elif output_name == "COLOR":
                    output_socket = attr_node.outputs.get("Color")
                elif output_name == "ALPHA":
                    output_socket = attr_node.outputs.get("Alpha")
                else:
                    output_socket = attr_node.outputs.get("Fac")  # Default to Fac
                
                if output_socket:
                    # Remove any existing connection to target input
                    for link in list(links):
                        if link.to_socket == target_input:
                            links.remove(link)
                    
                    # Create new connection
                    links.new(output_socket, target_input)
                    result["success"] = True
                    result["connection"] = "{attribute_name} -> {target_node}.{target_input}"
                    result["message"] = "Connected successfully"
                else:
                    result["message"] = "Could not find output socket: {attribute_type}"

print(result)
'''
        result_str = self.bridge.execute_blender_code(code)
        try:
            import ast
            return ast.literal_eval(result_str.strip())
        except Exception as e:
            return {"success": False, "message": f"Failed to parse result: {e}"}

    def list_shader_attributes(self, material_name: str) -> Dict[str, Any]:
        """
        List all Attribute nodes in a material and what they're connected to.
        
        Args:
            material_name: Name of the material to inspect
        
        Returns:
            Dict with list of attributes and their connections
        """
        code = f'''
import bpy

result = {{"success": False, "attributes": [], "message": ""}}

mat = bpy.data.materials.get("{material_name}")
if not mat:
    result["message"] = "Material not found: {material_name}"
elif not mat.use_nodes:
    result["message"] = "Material does not use nodes: {material_name}"
else:
    for node in mat.node_tree.nodes:
        if node.type == "ATTRIBUTE":
            attr_info = {{
                "node_name": node.name,
                "attribute_name": node.attribute_name,
                "connections": []
            }}
            for out in node.outputs:
                for link in out.links:
                    attr_info["connections"].append({{
                        "output": out.name,
                        "to_node": link.to_node.name,
                        "to_input": link.to_socket.name
                    }})
            result["attributes"].append(attr_info)
    result["success"] = True
    result["message"] = str(len(result["attributes"])) + " attribute nodes found"

print(result)
'''
        result_str = self.bridge.execute_blender_code(code)
        try:
            import ast
            return ast.literal_eval(result_str.strip())
        except Exception as e:
            return {"success": False, "message": f"Failed to parse result: {e}"}

    def disconnect_attribute(self, material_name: str, attribute_name: str, 
                            remove_node: bool = False) -> Dict[str, Any]:
        """
        Disconnect an attribute from all shader inputs, optionally removing the node.
        
        Args:
            material_name: Name of the material
            attribute_name: Name of the attribute to disconnect
            remove_node: If True, also remove the Attribute node
        
        Returns:
            Dict with success status and what was disconnected
        """
        code = f'''
import bpy

result = {{"success": False, "disconnected": [], "removed": False, "message": ""}}

mat = bpy.data.materials.get("{material_name}")
if not mat:
    result["message"] = "Material not found: {material_name}"
elif not mat.use_nodes:
    result["message"] = "Material does not use nodes: {material_name}"
else:
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Find attribute node
    attr_node = None
    for node in nodes:
        if node.type == "ATTRIBUTE" and node.attribute_name == "{attribute_name}":
            attr_node = node
            break
    
    if not attr_node:
        result["message"] = "Attribute node not found: {attribute_name}"
    else:
        # Remove all outgoing links
        for out in attr_node.outputs:
            for link in list(out.links):
                result["disconnected"].append(link.to_node.name + "." + link.to_socket.name)
                links.remove(link)
        
        # Remove node if requested
        if {str(remove_node).lower()}:
            nodes.remove(attr_node)
            result["removed"] = True
        
        result["success"] = True
        result["message"] = "Disconnected " + str(len(result["disconnected"])) + " connections"

print(result)
'''
        result_str = self.bridge.execute_blender_code(code)
        try:
            import ast
            return ast.literal_eval(result_str.strip())
        except Exception as e:
            return {"success": False, "message": f"Failed to parse result: {e}"}

    def setup_triplanar_projection(
        self,
        material_name: str,
        image_name: str,
        connect_to_base_color: bool = True,
        connect_to_bump: bool = True,
        bump_strength: float = 0.3,
        mapping_node: str = None
    ) -> Dict[str, Any]:
        """
        Set up triplanar (box) projection for a texture in a material.
        
        Creates 3 texture samples projected from X, Y, Z axes and blends them
        based on surface normal direction. Eliminates texture stretching on
        procedural geometry like Volume-to-Mesh clods.
        
        Args:
            material_name: Name of the material to modify
            image_name: Name of the image texture to use
            connect_to_base_color: If True, connect result to Principled BSDF Base Color
            connect_to_bump: If True, also create bump mapping from the triplanar result
            bump_strength: Strength of bump effect (default 0.3)
            mapping_node: Name of existing Mapping node to use, or None to create new one
        
        Returns:
            Dict with success status and created node names
        """
        code = f'''
import bpy

result = {{"success": False, "nodes_created": [], "message": ""}}

mat = bpy.data.materials.get("{material_name}")
if not mat:
    result["message"] = "Material not found: {material_name}"
elif not mat.use_nodes:
    result["message"] = "Material does not use nodes: {material_name}"
else:
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Get the image
    img = bpy.data.images.get("{image_name}")
    if not img:
        result["message"] = "Image not found: {image_name}"
    else:
        bsdf = nodes.get("Principled BSDF")
        if not bsdf:
            result["message"] = "Principled BSDF not found"
        else:
            # Get or create Mapping node
            mapping = nodes.get("{mapping_node}") if "{mapping_node}" != "None" else None
            if not mapping:
                mapping = nodes.new("ShaderNodeMapping")
                mapping.name = "TriplanarMapping"
                mapping.location = (-800, 0)
                result["nodes_created"].append("TriplanarMapping")
                
                # Create Texture Coordinate node
                tex_coord = nodes.new("ShaderNodeTexCoord")
                tex_coord.name = "TriplanarTexCoord"
                tex_coord.location = (-1000, 0)
                result["nodes_created"].append("TriplanarTexCoord")
                
                # Connect Generated coordinates to Mapping
                links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
            
            # Create Geometry node for normals
            geo = nodes.new("ShaderNodeNewGeometry")
            geo.name = "TriplanarGeometry"
            geo.location = (-800, -300)
            result["nodes_created"].append("TriplanarGeometry")
            
            # Separate normal XYZ
            sep_normal = nodes.new("ShaderNodeSeparateXYZ")
            sep_normal.name = "SeparateNormal"
            sep_normal.location = (-600, -300)
            links.new(geo.outputs["Normal"], sep_normal.inputs["Vector"])
            result["nodes_created"].append("SeparateNormal")
            
            # Absolute value nodes for blending weights
            abs_x = nodes.new("ShaderNodeMath")
            abs_x.name = "AbsX"
            abs_x.operation = "ABSOLUTE"
            abs_x.location = (-400, -250)
            links.new(sep_normal.outputs["X"], abs_x.inputs[0])
            
            abs_y = nodes.new("ShaderNodeMath")
            abs_y.name = "AbsY"
            abs_y.operation = "ABSOLUTE"
            abs_y.location = (-400, -300)
            links.new(sep_normal.outputs["Y"], abs_y.inputs[0])
            
            abs_z = nodes.new("ShaderNodeMath")
            abs_z.name = "AbsZ"
            abs_z.operation = "ABSOLUTE"
            abs_z.location = (-400, -350)
            links.new(sep_normal.outputs["Z"], abs_z.inputs[0])
            result["nodes_created"].extend(["AbsX", "AbsY", "AbsZ"])
            
            # Separate position for projections
            sep_pos = nodes.new("ShaderNodeSeparateXYZ")
            sep_pos.name = "SeparatePosition"
            sep_pos.location = (-600, 0)
            links.new(mapping.outputs["Vector"], sep_pos.inputs["Vector"])
            result["nodes_created"].append("SeparatePosition")
            
            # Create coordinate projections (YZ for X-face, XZ for Y-face, XY for Z-face)
            combine_yz = nodes.new("ShaderNodeCombineXYZ")
            combine_yz.name = "CombineYZ"
            combine_yz.location = (-400, 100)
            links.new(sep_pos.outputs["Y"], combine_yz.inputs["X"])
            links.new(sep_pos.outputs["Z"], combine_yz.inputs["Y"])
            
            combine_xz = nodes.new("ShaderNodeCombineXYZ")
            combine_xz.name = "CombineXZ"
            combine_xz.location = (-400, 0)
            links.new(sep_pos.outputs["X"], combine_xz.inputs["X"])
            links.new(sep_pos.outputs["Z"], combine_xz.inputs["Y"])
            
            combine_xy = nodes.new("ShaderNodeCombineXYZ")
            combine_xy.name = "CombineXY"
            combine_xy.location = (-400, -100)
            links.new(sep_pos.outputs["X"], combine_xy.inputs["X"])
            links.new(sep_pos.outputs["Y"], combine_xy.inputs["Y"])
            result["nodes_created"].extend(["CombineYZ", "CombineXZ", "CombineXY"])
            
            # Create 3 texture samples
            tex_x = nodes.new("ShaderNodeTexImage")
            tex_x.name = "TexX"
            tex_x.label = "Texture X-Face"
            tex_x.image = img
            tex_x.location = (-200, 100)
            links.new(combine_yz.outputs["Vector"], tex_x.inputs["Vector"])
            
            tex_y = nodes.new("ShaderNodeTexImage")
            tex_y.name = "TexY"
            tex_y.label = "Texture Y-Face"
            tex_y.image = img
            tex_y.location = (-200, 0)
            links.new(combine_xz.outputs["Vector"], tex_y.inputs["Vector"])
            
            tex_z = nodes.new("ShaderNodeTexImage")
            tex_z.name = "TexZ"
            tex_z.label = "Texture Z-Face"
            tex_z.image = img
            tex_z.location = (-200, -100)
            links.new(combine_xy.outputs["Vector"], tex_z.inputs["Vector"])
            result["nodes_created"].extend(["TexX", "TexY", "TexZ"])
            
            # Blending weight calculations
            add_xy = nodes.new("ShaderNodeMath")
            add_xy.name = "AddXYWeight"
            add_xy.operation = "ADD"
            add_xy.location = (-200, -250)
            links.new(abs_x.outputs["Value"], add_xy.inputs[0])
            links.new(abs_y.outputs["Value"], add_xy.inputs[1])
            
            div_xy = nodes.new("ShaderNodeMath")
            div_xy.name = "DivXY"
            div_xy.operation = "DIVIDE"
            div_xy.location = (-50, -250)
            links.new(abs_y.outputs["Value"], div_xy.inputs[0])
            links.new(add_xy.outputs["Value"], div_xy.inputs[1])
            
            add_xyz = nodes.new("ShaderNodeMath")
            add_xyz.name = "AddXYZWeight"
            add_xyz.operation = "ADD"
            add_xyz.location = (-200, -350)
            links.new(add_xy.outputs["Value"], add_xyz.inputs[0])
            links.new(abs_z.outputs["Value"], add_xyz.inputs[1])
            
            div_xyz = nodes.new("ShaderNodeMath")
            div_xyz.name = "DivXYZ"
            div_xyz.operation = "DIVIDE"
            div_xyz.location = (-50, -350)
            links.new(abs_z.outputs["Value"], div_xyz.inputs[0])
            links.new(add_xyz.outputs["Value"], div_xyz.inputs[1])
            result["nodes_created"].extend(["AddXYWeight", "DivXY", "AddXYZWeight", "DivXYZ"])
            
            # Mix nodes for blending
            mix_xy = nodes.new("ShaderNodeMix")
            mix_xy.name = "MixXY"
            mix_xy.data_type = "RGBA"
            mix_xy.location = (100, 50)
            links.new(tex_x.outputs["Color"], mix_xy.inputs["A"])
            links.new(tex_y.outputs["Color"], mix_xy.inputs["B"])
            links.new(div_xy.outputs["Value"], mix_xy.inputs["Factor"])
            
            mix_xyz = nodes.new("ShaderNodeMix")
            mix_xyz.name = "MixXYZ"
            mix_xyz.data_type = "RGBA"
            mix_xyz.location = (300, 0)
            links.new(mix_xy.outputs["Result"], mix_xyz.inputs["A"])
            links.new(tex_z.outputs["Color"], mix_xyz.inputs["B"])
            links.new(div_xyz.outputs["Value"], mix_xyz.inputs["Factor"])
            result["nodes_created"].extend(["MixXY", "MixXYZ"])
            
            # Connect to Base Color if requested
            if {connect_to_base_color}:
                # Remove existing Base Color connection
                for link in list(links):
                    if link.to_node == bsdf and link.to_socket.name == "Base Color":
                        links.remove(link)
                links.new(mix_xyz.outputs["Result"], bsdf.inputs["Base Color"])
            
            # Create bump if requested
            if {connect_to_bump}:
                bump = nodes.new("ShaderNodeBump")
                bump.name = "TriplanarBump"
                bump.location = (300, -200)
                bump.inputs["Strength"].default_value = {bump_strength}
                links.new(mix_xyz.outputs["Result"], bump.inputs["Height"])
                links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
                result["nodes_created"].append("TriplanarBump")
            
            result["success"] = True
            result["message"] = "Triplanar projection created with " + str(len(result["nodes_created"])) + " nodes"

print(result)
'''
        result_str = self.bridge.execute_blender_code(code)
        try:
            import ast
            return ast.literal_eval(result_str.strip())
        except Exception as e:
            return {"success": False, "message": f"Failed to parse result: {e}"}

    def ensure_material_slots(
        self,
        object_name: str,
        material_names: List[str],
        create_missing: bool = False
    ) -> Dict[str, Any]:
        """
        Ensure an object has material slots for the specified materials.
        
        This is required before using Set Material nodes in geometry nodes,
        which can only apply materials that exist in the object's slots.
        
        Args:
            object_name: Name of the object to modify
            material_names: List of material names to ensure are in slots
            create_missing: If True, create materials that don't exist
        
        Returns:
            Dict with success status and which materials were added/created
        """
        material_names_str = str(material_names)
        code = f'''
import bpy

result = {{"success": False, "added": [], "created": [], "already_present": [], "message": ""}}

obj = bpy.data.objects.get("{object_name}")
if not obj:
    result["message"] = "Object not found: {object_name}"
elif not hasattr(obj.data, "materials"):
    result["message"] = "Object does not support materials: {object_name}"
else:
    material_names = {material_names_str}
    
    for mat_name in material_names:
        mat = bpy.data.materials.get(mat_name)
        
        if not mat:
            if {str(create_missing).lower()}:
                mat = bpy.data.materials.new(name=mat_name)
                mat.use_nodes = True
                result["created"].append(mat_name)
            else:
                continue
        
        # Check if already in slots
        found = False
        for slot in obj.material_slots:
            if slot.material == mat:
                found = True
                result["already_present"].append(mat_name)
                break
        
        if not found:
            obj.data.materials.append(mat)
            result["added"].append(mat_name)
    
    result["success"] = True
    total_slots = len(obj.material_slots)
    result["message"] = "Object now has " + str(total_slots) + " material slots"

print(result)
'''
        result_str = self.bridge.execute_blender_code(code)
        try:
            import ast
            return ast.literal_eval(result_str.strip())
        except Exception as e:
            return {"success": False, "message": f"Failed to parse result: {e}"}

    def list_material_slots(self, object_name: str) -> Dict[str, Any]:
        """
        List all material slots on an object.
        
        Args:
            object_name: Name of the object to inspect
        
        Returns:
            Dict with list of material slot names
        """
        code = f'''
import bpy

result = {{"success": False, "slots": [], "message": ""}}

obj = bpy.data.objects.get("{object_name}")
if not obj:
    result["message"] = "Object not found: {object_name}"
elif not hasattr(obj.data, "materials"):
    result["message"] = "Object does not support materials: {object_name}"
else:
    for i, slot in enumerate(obj.material_slots):
        mat_name = slot.material.name if slot.material else None
        result["slots"].append({{"index": i, "material": mat_name}})
    result["success"] = True
    result["message"] = str(len(result["slots"])) + " material slots"

print(result)
'''
        result_str = self.bridge.execute_blender_code(code)
        try:
            import ast
            return ast.literal_eval(result_str.strip())
        except Exception as e:
            return {"success": False, "message": f"Failed to parse result: {e}"}


# Convenience functions for direct use
def connect_attribute_to_shader(
    material_name: str,
    attribute_name: str,
    target_node: str,
    target_input: str,
    attribute_type: str = "FAC"
) -> Dict[str, Any]:
    """
    Connect a geometry nodes named attribute to a shader input.
    
    Example:
        connect_attribute_to_shader("clodMaterial", "hydration", "Mix", "Factor")
        connect_attribute_to_shader("clodMaterial", "clodScale", "Mapping", "Scale", "COLOR")
    """
    helper = MaterialHelper()
    return helper.connect_attribute_to_shader(
        material_name, attribute_name, target_node, target_input, attribute_type
    )


def list_shader_attributes(material_name: str) -> Dict[str, Any]:
    """List all attribute nodes in a material."""
    helper = MaterialHelper()
    return helper.list_shader_attributes(material_name)


def setup_triplanar_projection(
    material_name: str,
    image_name: str,
    connect_to_base_color: bool = True,
    connect_to_bump: bool = True,
    bump_strength: float = 0.3
) -> Dict[str, Any]:
    """
    Set up triplanar (box) projection for a texture in a material.
    
    Example:
        setup_triplanar_projection("clodMaterial", "soilTexture.png")
    """
    helper = MaterialHelper()
    return helper.setup_triplanar_projection(
        material_name, image_name, connect_to_base_color, connect_to_bump, bump_strength
    )


def ensure_material_slots(
    object_name: str,
    material_names: List[str],
    create_missing: bool = False
) -> Dict[str, Any]:
    """
    Ensure an object has material slots for the specified materials.
    
    Example:
        ensure_material_slots("templateSoilPlane", ["clodMaterial", "biomassMaterial", "rootMaterial"])
    """
    helper = MaterialHelper()
    return helper.ensure_material_slots(object_name, material_names, create_missing)


def list_material_slots(object_name: str) -> Dict[str, Any]:
    """List all material slots on an object."""
    helper = MaterialHelper()
    return helper.list_material_slots(object_name)


if __name__ == "__main__":
    # Test the helper
    import sys
    
    if len(sys.argv) > 1:
        material = sys.argv[1]
        result = list_shader_attributes(material)
        print(f"Attributes in {material}:")
        for attr in result.get("attributes", []):
            print(f"  {attr['attribute_name']}: {attr['connections']}")
    else:
        print("Usage: python material_helper.py <material_name>")
        print("       Lists all attribute nodes in the specified material")
