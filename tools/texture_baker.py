"""
Texture Baker Helper for Blender MCP

A comprehensive tool for baking procedural materials to texture maps.
Supports baking diffuse, normal, roughness, metallic, emission, and AO maps.

Usage:
    from texture_baker import TextureBaker, bake_material, quick_bake
    
    # Quick bake with defaults
    result = quick_bake("MaterialName")
    
    # Full control
    baker = TextureBaker()
    result = baker.bake_material(
        material_name="potato",
        resolution=2048,
        output_dir="/path/to/output",
        bake_types=['DIFFUSE', 'NORMAL', 'ROUGHNESS']
    )
"""

import sys
import os
import json
from typing import Optional, List, Dict, Any

try:
    from .copilot_bridge import BlenderCopilotBridge
except ImportError:
    BlenderCopilotBridge = None


class TextureBaker:
    """
    Comprehensive texture baking utility for Blender.
    
    Bakes procedural materials to image textures for use in game engines,
    real-time renderers, or other applications that don't support procedural textures.
    """
    
    # Standard bake types and their settings
    BAKE_TYPES = {
        'DIFFUSE': {
            'type': 'DIFFUSE',
            'suffix': 'diffuse',
            'pass_filter': {'use_pass_direct': False, 'use_pass_indirect': False, 'use_pass_color': True},
            'color_space': 'sRGB'
        },
        'NORMAL': {
            'type': 'NORMAL',
            'suffix': 'normal',
            'pass_filter': {},
            'color_space': 'Non-Color'
        },
        'ROUGHNESS': {
            'type': 'ROUGHNESS',
            'suffix': 'roughness',
            'pass_filter': {},
            'color_space': 'Non-Color'
        },
        'METALLIC': {
            'type': 'EMIT',  # Bake metallic via emission trick
            'suffix': 'metallic',
            'pass_filter': {},
            'color_space': 'Non-Color',
            'requires_setup': True
        },
        'AO': {
            'type': 'AO',
            'suffix': 'ao',
            'pass_filter': {},
            'color_space': 'Non-Color'
        },
        'EMISSION': {
            'type': 'EMIT',
            'suffix': 'emission',
            'pass_filter': {},
            'color_space': 'sRGB'
        },
        'COMBINED': {
            'type': 'COMBINED',
            'suffix': 'combined',
            'pass_filter': {},
            'color_space': 'sRGB'
        }
    }
    
    # Common resolution presets
    RESOLUTION_PRESETS = {
        'low': 512,
        'medium': 1024,
        'high': 2048,
        'ultra': 4096
    }
    
    def __init__(self, bridge: Optional['BlenderCopilotBridge'] = None):
        """Initialize the texture baker with an optional bridge connection."""
        self.bridge = bridge or (BlenderCopilotBridge() if BlenderCopilotBridge else None)
        if not self.bridge:
            raise RuntimeError("BlenderCopilotBridge not available. Ensure copilot_bridge.py is accessible.")
    
    def get_material_info(self, material_name: str) -> Dict[str, Any]:
        """Get information about a material and its bake requirements."""
        code = f'''
import bpy

mat = bpy.data.materials.get("{material_name}")
if not mat:
    print("ERROR: Material not found")
else:
    info = {{
        "name": mat.name,
        "use_nodes": mat.use_nodes,
        "node_count": len(mat.node_tree.nodes) if mat.use_nodes else 0,
        "has_bsdf": False,
        "has_image_textures": False,
        "objects_using": []
    }}
    
    if mat.use_nodes:
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                info["has_bsdf"] = True
            if node.type == 'TEX_IMAGE':
                info["has_image_textures"] = True
    
    # Find objects using this material
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.data.materials:
            for slot in obj.material_slots:
                if slot.material and slot.material.name == "{material_name}":
                    info["objects_using"].append({{
                        "name": obj.name,
                        "has_uv": len(obj.data.uv_layers) > 0,
                        "uv_names": [uv.name for uv in obj.data.uv_layers]
                    }})
                    break
    
    import json
    print("MATERIAL_INFO:" + json.dumps(info))
'''
        result = self.bridge.execute_blender_code(code)
        
        # Parse the result
        for line in result.split('\n'):
            if line.startswith('MATERIAL_INFO:'):
                return json.loads(line[14:])
        
        if 'ERROR: Material not found' in result:
            raise ValueError(f"Material '{material_name}' not found in Blender")
        
        return {"error": "Could not parse material info", "raw": result}
    
    def list_bakeable_materials(self) -> List[Dict[str, Any]]:
        """List all materials that can be baked (have nodes and are used by mesh objects)."""
        code = '''
import bpy
import json

materials = []
for mat in bpy.data.materials:
    if mat.use_nodes:
        # Check if used by any mesh with UVs
        objects_using = []
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj.data.materials:
                for slot in obj.material_slots:
                    if slot.material and slot.material.name == mat.name:
                        if len(obj.data.uv_layers) > 0:
                            objects_using.append(obj.name)
                        break
        
        if objects_using:
            materials.append({
                "name": mat.name,
                "node_count": len(mat.node_tree.nodes),
                "objects": objects_using[:3]  # First 3 objects
            })

print("MATERIALS:" + json.dumps(materials))
'''
        result = self.bridge.execute_blender_code(code)
        
        for line in result.split('\n'):
            if line.startswith('MATERIALS:'):
                return json.loads(line[10:])
        
        return []
    
    def ensure_uv_map(self, object_name: str) -> str:
        """Ensure object has a UV map, create one if needed. Returns UV map name."""
        code = f'''
import bpy

obj = bpy.data.objects.get("{object_name}")
if not obj or obj.type != 'MESH':
    print("ERROR: Object not found or not a mesh")
else:
    if len(obj.data.uv_layers) == 0:
        # Create UV map using smart UV project
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.02)
        bpy.ops.object.mode_set(mode='OBJECT')
        print("UV_CREATED:" + obj.data.uv_layers.active.name)
    else:
        print("UV_EXISTS:" + obj.data.uv_layers.active.name)
'''
        result = self.bridge.execute_blender_code(code)
        
        for line in result.split('\n'):
            if line.startswith('UV_CREATED:') or line.startswith('UV_EXISTS:'):
                return line.split(':')[1]
        
        raise RuntimeError(f"Failed to ensure UV map for {object_name}")
    
    def setup_bake_image_node(self, material_name: str, image_name: str) -> bool:
        """Add an image texture node to the material for baking target."""
        code = f'''
import bpy

mat = bpy.data.materials.get("{material_name}")
if not mat or not mat.use_nodes:
    print("ERROR: Material not found or doesn't use nodes")
else:
    nodes = mat.node_tree.nodes
    
    # Remove existing bake target nodes
    for node in list(nodes):
        if node.name.startswith("BakeTarget_"):
            nodes.remove(node)
    
    # Create new image texture node
    img = bpy.data.images.get("{image_name}")
    if not img:
        print("ERROR: Image not found")
    else:
        tex_node = nodes.new('ShaderNodeTexImage')
        tex_node.name = "BakeTarget_{image_name}"
        tex_node.label = "Bake Target"
        tex_node.image = img
        tex_node.location = (-400, 0)
        
        # Select and make active (required for baking)
        for n in nodes:
            n.select = False
        tex_node.select = True
        nodes.active = tex_node
        
        print("SUCCESS: Bake target node created")
'''
        result = self.bridge.execute_blender_code(code)
        return "SUCCESS" in result
    
    def cleanup_bake_nodes(self, material_name: str) -> bool:
        """Remove temporary bake target nodes from material."""
        code = f'''
import bpy

mat = bpy.data.materials.get("{material_name}")
if mat and mat.use_nodes:
    nodes = mat.node_tree.nodes
    removed = 0
    for node in list(nodes):
        if node.name.startswith("BakeTarget_"):
            nodes.remove(node)
            removed += 1
    print(f"CLEANED: Removed {{removed}} bake target nodes")
else:
    print("ERROR: Material not found")
'''
        result = self.bridge.execute_blender_code(code)
        return "CLEANED" in result
    
    def bake_single_type(
        self,
        object_name: str,
        material_name: str,
        bake_type: str,
        resolution: int,
        output_path: str,
        samples: int = 16
    ) -> Dict[str, Any]:
        """Bake a single texture type."""
        
        if bake_type not in self.BAKE_TYPES:
            return {"success": False, "error": f"Unknown bake type: {bake_type}"}
        
        config = self.BAKE_TYPES[bake_type]
        image_name = f"bake_{material_name}_{config['suffix']}"
        
        # Build pass filter settings
        pass_filter_code = ""
        for key, value in config.get('pass_filter', {}).items():
            pass_filter_code += f"    bpy.context.scene.render.bake.{key} = {value}\n"
        
        code = f'''
import bpy
import os

# Ensure output directory exists
output_dir = os.path.dirname("{output_path}")
os.makedirs(output_dir, exist_ok=True)

# Get object and set as active
obj = bpy.data.objects.get("{object_name}")
if not obj:
    print("ERROR: Object not found")
else:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    
    # Create or get bake image
    img = bpy.data.images.get("{image_name}")
    if img:
        bpy.data.images.remove(img)
    
    img = bpy.data.images.new(
        name="{image_name}",
        width={resolution},
        height={resolution},
        alpha=False,
        float_buffer=False
    )
    img.colorspace_settings.name = "{config['color_space']}"
    
    # Setup bake target node in material
    mat = bpy.data.materials.get("{material_name}")
    if mat and mat.use_nodes:
        nodes = mat.node_tree.nodes
        
        # Remove old bake target
        for node in list(nodes):
            if node.name.startswith("BakeTarget_"):
                nodes.remove(node)
        
        # Create new bake target
        tex_node = nodes.new('ShaderNodeTexImage')
        tex_node.name = "BakeTarget_{image_name}"
        tex_node.image = img
        tex_node.location = (-400, 0)
        
        # Make active
        for n in nodes:
            n.select = False
        tex_node.select = True
        nodes.active = tex_node
    
    # Configure render settings for baking
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = {samples}
    bpy.context.scene.cycles.use_denoising = False
    
    # Configure bake settings
    bpy.context.scene.render.bake.use_pass_direct = False
    bpy.context.scene.render.bake.use_pass_indirect = False
    bpy.context.scene.render.bake.use_pass_color = True
    bpy.context.scene.render.bake.margin = 16
    bpy.context.scene.render.bake.margin_type = 'EXTEND'
{pass_filter_code}
    
    # Perform bake
    try:
        bpy.ops.object.bake(type='{config["type"]}')
        
        # Save the image
        img.filepath_raw = "{output_path}"
        img.file_format = 'PNG'
        img.save()
        
        print("BAKE_SUCCESS:{output_path}")
    except Exception as e:
        print(f"BAKE_ERROR:{{str(e)}}")
'''
        result = self.bridge.execute_blender_code(code)
        
        if "BAKE_SUCCESS:" in result:
            return {
                "success": True,
                "type": bake_type,
                "path": output_path,
                "resolution": resolution
            }
        elif "BAKE_ERROR:" in result:
            error = result.split("BAKE_ERROR:")[1].split('\n')[0]
            return {"success": False, "type": bake_type, "error": error}
        else:
            return {"success": False, "type": bake_type, "error": result}
    
    def bake_material(
        self,
        material_name: str,
        object_name: Optional[str] = None,
        resolution: int = 2048,
        output_dir: Optional[str] = None,
        bake_types: Optional[List[str]] = None,
        samples: int = 16,
        filename_prefix: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Bake a complete material to texture maps.
        
        Args:
            material_name: Name of the material to bake
            object_name: Optional specific object (auto-detected if not provided)
            resolution: Texture resolution (default 2048)
            output_dir: Output directory (default: blend file location/baked_textures)
            bake_types: List of types to bake (default: DIFFUSE, NORMAL, ROUGHNESS)
            samples: Render samples for baking (default 16)
            filename_prefix: Prefix for output files (default: material name)
        
        Returns:
            Dictionary with bake results for each type
        """
        
        # Default bake types
        if bake_types is None:
            bake_types = ['DIFFUSE', 'NORMAL', 'ROUGHNESS']
        
        # Get material info
        mat_info = self.get_material_info(material_name)
        if "error" in mat_info:
            return {"success": False, "error": mat_info.get("error", "Unknown error")}
        
        # Auto-detect object if not provided
        if object_name is None:
            if mat_info.get("objects_using"):
                # Find object with UVs
                for obj_info in mat_info["objects_using"]:
                    if obj_info.get("has_uv"):
                        object_name = obj_info["name"]
                        break
                if object_name is None:
                    object_name = mat_info["objects_using"][0]["name"]
            else:
                return {"success": False, "error": "No objects using this material"}
        
        # Ensure UV map exists
        try:
            uv_name = self.ensure_uv_map(object_name)
        except RuntimeError as e:
            return {"success": False, "error": str(e)}
        
        # Determine output directory
        if output_dir is None:
            output_dir = self._get_default_output_dir(material_name)
        
        # Filename prefix
        prefix = filename_prefix or material_name
        
        # Bake each type
        results = {
            "success": True,
            "material": material_name,
            "object": object_name,
            "resolution": resolution,
            "output_dir": output_dir,
            "textures": {}
        }
        
        for bake_type in bake_types:
            if bake_type not in self.BAKE_TYPES:
                results["textures"][bake_type] = {"success": False, "error": f"Unknown type: {bake_type}"}
                continue
            
            suffix = self.BAKE_TYPES[bake_type]['suffix']
            output_path = os.path.join(output_dir, f"{prefix}_{suffix}.png")
            
            bake_result = self.bake_single_type(
                object_name=object_name,
                material_name=material_name,
                bake_type=bake_type,
                resolution=resolution,
                output_path=output_path,
                samples=samples
            )
            
            results["textures"][bake_type] = bake_result
            
            if not bake_result.get("success"):
                results["success"] = False
        
        # Cleanup bake nodes
        self.cleanup_bake_nodes(material_name)
        
        return results
    
    def _get_default_output_dir(self, material_name: str) -> str:
        """Get the default output directory based on blend file location."""
        code = '''
import bpy
import os

blend_path = bpy.data.filepath
if blend_path:
    blend_dir = os.path.dirname(blend_path)
    output_dir = os.path.join(blend_dir, "baked_textures")
else:
    output_dir = "/tmp/blender_bakes"

print("OUTPUT_DIR:" + output_dir)
'''
        result = self.bridge.execute_blender_code(code)
        
        for line in result.split('\n'):
            if line.startswith('OUTPUT_DIR:'):
                return line[11:]
        
        return "/tmp/blender_bakes"
    
    def bake_all_materials(
        self,
        resolution: int = 2048,
        output_dir: Optional[str] = None,
        bake_types: Optional[List[str]] = None,
        samples: int = 16
    ) -> Dict[str, Any]:
        """
        Bake all bakeable materials in the scene.
        
        Returns a dictionary with results for each material.
        """
        materials = self.list_bakeable_materials()
        
        if not materials:
            return {"success": False, "error": "No bakeable materials found"}
        
        results = {
            "success": True,
            "materials": {}
        }
        
        for mat_info in materials:
            mat_name = mat_info["name"]
            result = self.bake_material(
                material_name=mat_name,
                resolution=resolution,
                output_dir=output_dir,
                bake_types=bake_types,
                samples=samples
            )
            
            results["materials"][mat_name] = result
            
            if not result.get("success"):
                results["success"] = False
        
        return results


# Convenience functions for quick access

def bake_material(
    material_name: str,
    resolution: int = 2048,
    bake_types: Optional[List[str]] = None,
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Quick function to bake a material.
    
    Example:
        result = bake_material("potato", resolution=2048)
        print(result["textures"]["DIFFUSE"]["path"])
    """
    baker = TextureBaker()
    return baker.bake_material(
        material_name=material_name,
        resolution=resolution,
        bake_types=bake_types,
        output_dir=output_dir
    )


def quick_bake(material_name: str, resolution: int = 1024) -> Dict[str, Any]:
    """
    Quickest way to bake a material with sensible defaults.
    Bakes diffuse, normal, and roughness at 1024px.
    
    Example:
        result = quick_bake("MyMaterial")
    """
    return bake_material(material_name, resolution=resolution)


def list_materials() -> List[Dict[str, Any]]:
    """List all materials that can be baked."""
    baker = TextureBaker()
    return baker.list_bakeable_materials()


def bake_all(resolution: int = 2048) -> Dict[str, Any]:
    """Bake all materials in the scene."""
    baker = TextureBaker()
    return baker.bake_all_materials(resolution=resolution)


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Bake Blender materials to textures")
    parser.add_argument("material", nargs="?", help="Material name to bake")
    parser.add_argument("-r", "--resolution", type=int, default=2048, help="Texture resolution")
    parser.add_argument("-o", "--output", help="Output directory")
    parser.add_argument("-t", "--types", nargs="+", default=["DIFFUSE", "NORMAL", "ROUGHNESS"],
                        help="Bake types (DIFFUSE, NORMAL, ROUGHNESS, METALLIC, AO, EMISSION)")
    parser.add_argument("-l", "--list", action="store_true", help="List bakeable materials")
    parser.add_argument("-a", "--all", action="store_true", help="Bake all materials")
    parser.add_argument("-s", "--samples", type=int, default=16, help="Render samples")
    
    args = parser.parse_args()
    
    baker = TextureBaker()
    
    if args.list:
        materials = baker.list_bakeable_materials()
        print("\n=== Bakeable Materials ===")
        for mat in materials:
            print(f"  • {mat['name']} ({mat['node_count']} nodes) - Used by: {', '.join(mat['objects'])}")
        print()
    
    elif args.all:
        print(f"\nBaking all materials at {args.resolution}px...")
        result = baker.bake_all_materials(
            resolution=args.resolution,
            output_dir=args.output,
            bake_types=args.types,
            samples=args.samples
        )
        
        for mat_name, mat_result in result.get("materials", {}).items():
            print(f"\n{mat_name}:")
            for tex_type, tex_result in mat_result.get("textures", {}).items():
                if tex_result.get("success"):
                    print(f"  ✓ {tex_type}: {tex_result.get('path')}")
                else:
                    print(f"  ✗ {tex_type}: {tex_result.get('error')}")
    
    elif args.material:
        print(f"\nBaking {args.material} at {args.resolution}px...")
        result = baker.bake_material(
            material_name=args.material,
            resolution=args.resolution,
            output_dir=args.output,
            bake_types=args.types,
            samples=args.samples
        )
        
        print(f"\nOutput: {result.get('output_dir')}")
        for tex_type, tex_result in result.get("textures", {}).items():
            if tex_result.get("success"):
                print(f"  ✓ {tex_type}: {tex_result.get('path')}")
            else:
                print(f"  ✗ {tex_type}: {tex_result.get('error')}")
    
    else:
        parser.print_help()
