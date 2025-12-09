"""
Texture Baker - Complete Procedural to Baked Texture Workflow

A robust tool for baking procedural Blender materials to texture maps
and optionally replacing the procedural nodes with image textures.

CRITICAL: Always specify BOTH material_name AND object_name explicitly.
Auto-detection can bake the wrong object.

Usage:
    from texture_baker_v2 import TextureBaker
    
    baker = TextureBaker()
    
    # Step 1: List materials to find the right one
    baker.list_all_materials()
    
    # Step 2: Bake with explicit names
    result = baker.bake_and_replace(
        material_name="MyProcedural",
        object_name="MyObject",
        resolution=2048
    )
    
    # Or just bake (don't modify material)
    result = baker.bake_only(
        material_name="MyProcedural",
        object_name="MyObject",
        resolution=2048
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
    Complete texture baking utility.
    
    Workflow:
    1. list_all_materials() - See all materials and their objects
    2. bake_only() - Bake textures without modifying material
    3. replace_with_baked() - Replace procedural nodes with baked images
    
    Or use bake_and_replace() to do both in one step.
    """
    
    BAKE_TYPES = {
        'DIFFUSE': {'type': 'DIFFUSE', 'suffix': 'diffuse', 'color_space': 'sRGB'},
        'NORMAL': {'type': 'NORMAL', 'suffix': 'normal', 'color_space': 'Non-Color'},
        'ROUGHNESS': {'type': 'ROUGHNESS', 'suffix': 'roughness', 'color_space': 'Non-Color'},
        'METALLIC': {'type': 'EMIT', 'suffix': 'metallic', 'color_space': 'Non-Color'},
        'AO': {'type': 'AO', 'suffix': 'ao', 'color_space': 'Non-Color'},
        'EMISSION': {'type': 'EMIT', 'suffix': 'emission', 'color_space': 'sRGB'},
    }
    
    DEFAULT_OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "baked_textures")
    
    def __init__(self):
        if not BlenderCopilotBridge:
            raise RuntimeError("BlenderCopilotBridge not available")
        self.bridge = BlenderCopilotBridge()
    
    def list_all_materials(self) -> str:
        """List ALL materials and objects - always run this first to verify names."""
        code = """
import bpy

print("=== ALL MATERIALS ===")
for mat in bpy.data.materials:
    print(f"  {mat.name}")

print()
print("=== ALL MESH OBJECTS WITH MATERIALS ===")
for obj in bpy.data.objects:
    if obj.type == "MESH" and obj.data.materials:
        mats = [slot.material.name if slot.material else "None" for slot in obj.material_slots]
        has_uv = len(obj.data.uv_layers) > 0
        render = not obj.hide_render
        print(f"  {obj.name}: UV={has_uv}, Render={render}, materials={mats}")
"""
        result = self.bridge.execute_blender_code(code)
        print(result)
        return result
    
    def _bake_single_type(
        self, 
        material_name: str, 
        object_name: str, 
        bake_type: str, 
        resolution: int, 
        output_path: str,
        samples: int = 16
    ) -> Dict[str, Any]:
        """Bake a single texture type safely (no permanent material changes)."""
        
        config = self.BAKE_TYPES.get(bake_type)
        if not config:
            return {"success": False, "error": f"Unknown bake type: {bake_type}"}
        
        image_name = f"_bake_temp_{config['suffix']}"
        
        # Build pass filter for diffuse (color only, no lighting)
        pass_settings = ""
        if bake_type == "DIFFUSE":
            pass_settings = """
    bpy.context.scene.render.bake.use_pass_direct = False
    bpy.context.scene.render.bake.use_pass_indirect = False
    bpy.context.scene.render.bake.use_pass_color = True
"""
        
        code = f"""
import bpy
import os

obj = bpy.data.objects.get("{object_name}")
mat = bpy.data.materials.get("{material_name}")

if not obj:
    print("ERROR:Object '{object_name}' not found")
elif not mat:
    print("ERROR:Material '{material_name}' not found")
else:
    # Enable for rendering
    orig_hide_render = obj.hide_render
    obj.hide_render = False
    
    # Make active
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    
    # Create bake image
    img = bpy.data.images.get("{image_name}")
    if img:
        bpy.data.images.remove(img)
    
    img = bpy.data.images.new(
        name="{image_name}",
        width={resolution},
        height={resolution},
        alpha=False
    )
    img.colorspace_settings.name = "{config['color_space']}"
    
    # Add temp node to material
    nodes = mat.node_tree.nodes
    orig_active = nodes.active
    
    temp_node = nodes.new('ShaderNodeTexImage')
    temp_node.name = "_TEMP_BAKE_TARGET_"
    temp_node.image = img
    temp_node.location = (-600, -600)
    nodes.active = temp_node
    
    # Configure render
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = {samples}
    bpy.context.scene.cycles.use_denoising = False
    bpy.context.scene.render.bake.margin = 16
    bpy.context.scene.render.bake.margin_type = 'EXTEND'
    {pass_settings}
    
    try:
        bpy.ops.object.bake(type='{config["type"]}')
        
        # Ensure directory exists
        os.makedirs(os.path.dirname("{output_path}"), exist_ok=True)
        
        # Save
        img.filepath_raw = "{output_path}"
        img.file_format = 'PNG'
        img.save()
        
        print("SUCCESS:{output_path}")
    except Exception as e:
        print(f"ERROR:{{str(e)}}")
    
    # CLEANUP - remove temp node
    nodes.remove(temp_node)
    if orig_active and orig_active.name in nodes:
        nodes.active = nodes[orig_active.name]
    
    # Restore render state
    obj.hide_render = orig_hide_render
    
    # Remove temp image
    if img:
        bpy.data.images.remove(img)
"""
        
        result = self.bridge.execute_blender_code(code)
        
        if "SUCCESS:" in result:
            return {"success": True, "path": output_path}
        elif "ERROR:" in result:
            error = result.split("ERROR:")[1].split('\n')[0]
            return {"success": False, "error": error}
        else:
            return {"success": False, "error": f"Unknown: {result}"}
    
    def bake_only(
        self,
        material_name: str,
        object_name: str,
        resolution: int = 2048,
        output_dir: Optional[str] = None,
        bake_types: Optional[List[str]] = None,
        prefix: Optional[str] = None,
        samples: int = 16
    ) -> Dict[str, Any]:
        """
        Bake material to texture files WITHOUT modifying the material.
        
        Args:
            material_name: EXACT name of material (run list_all_materials first!)
            object_name: EXACT name of object (run list_all_materials first!)
            resolution: Texture resolution (512, 1024, 2048, 4096)
            output_dir: Where to save files (default: blender-mcp/baked_textures)
            bake_types: List of types ['DIFFUSE', 'NORMAL', 'ROUGHNESS']
            prefix: Filename prefix (default: material name)
            samples: Render samples (default: 16)
        
        Returns:
            Dict with success status and paths to baked files
        """
        if bake_types is None:
            bake_types = ['DIFFUSE', 'NORMAL', 'ROUGHNESS']
        
        if output_dir is None:
            output_dir = self.DEFAULT_OUTPUT_DIR
        
        if prefix is None:
            prefix = material_name.replace(" ", "_")
        
        os.makedirs(output_dir, exist_ok=True)
        
        results = {
            "success": True,
            "material": material_name,
            "object": object_name,
            "resolution": resolution,
            "output_dir": output_dir,
            "textures": {}
        }
        
        print(f"=== Baking {material_name} ===")
        print(f"Object: {object_name}")
        print(f"Resolution: {resolution}x{resolution}")
        print(f"Output: {output_dir}")
        print()
        
        for bake_type in bake_types:
            if bake_type not in self.BAKE_TYPES:
                print(f"  ✗ {bake_type}: Unknown type")
                results["textures"][bake_type] = {"success": False, "error": "Unknown type"}
                continue
            
            suffix = self.BAKE_TYPES[bake_type]['suffix']
            output_path = os.path.join(output_dir, f"{prefix}_{suffix}.png")
            
            print(f"  Baking {bake_type}...", end=" ", flush=True)
            bake_result = self._bake_single_type(
                material_name=material_name,
                object_name=object_name,
                bake_type=bake_type,
                resolution=resolution,
                output_path=output_path,
                samples=samples
            )
            
            results["textures"][bake_type] = bake_result
            
            if bake_result["success"]:
                print(f"✓")
            else:
                print(f"✗ {bake_result.get('error', 'Unknown error')}")
                results["success"] = False
        
        return results
    
    def replace_with_baked(
        self,
        material_name: str,
        texture_paths: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Replace procedural nodes in material with baked image textures.
        
        Args:
            material_name: Name of material to modify
            texture_paths: Dict mapping type to path, e.g.:
                {"DIFFUSE": "/path/to/diffuse.png", "NORMAL": "/path/to/normal.png"}
        
        Returns:
            Dict with success status
        """
        diffuse_path = texture_paths.get("DIFFUSE", "")
        normal_path = texture_paths.get("NORMAL", "")
        roughness_path = texture_paths.get("ROUGHNESS", "")
        
        code = f"""
import bpy

mat = bpy.data.materials.get("{material_name}")
if not mat:
    print("ERROR:Material not found")
else:
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Find Principled BSDF
    bsdf = None
    for node in nodes:
        if node.type == "BSDF_PRINCIPLED":
            bsdf = node
            break
    
    if not bsdf:
        print("ERROR:No Principled BSDF found")
    else:
        # Identify nodes to keep
        keep_nodes = set(["Principled BSDF", "Material Output", bsdf.name])
        for node in nodes:
            if node.type == "OUTPUT_MATERIAL":
                keep_nodes.add(node.name)
        
        # Collect procedural nodes to remove
        to_remove = [n.name for n in nodes if n.name not in keep_nodes]
        
        # Disconnect BSDF inputs
        for inp in bsdf.inputs:
            if inp.is_linked:
                for link in list(inp.links):
                    links.remove(link)
        
        # Add baked texture nodes
        x_pos = -400
        
        # Diffuse
        if "{diffuse_path}":
            diffuse_tex = nodes.new("ShaderNodeTexImage")
            diffuse_tex.name = "Baked Diffuse"
            diffuse_tex.label = "Baked Diffuse"
            diffuse_tex.location = (x_pos, 300)
            diffuse_img = bpy.data.images.load("{diffuse_path}")
            diffuse_img.colorspace_settings.name = 'sRGB'
            diffuse_tex.image = diffuse_img
            links.new(diffuse_tex.outputs["Color"], bsdf.inputs["Base Color"])
        
        # Normal
        if "{normal_path}":
            normal_tex = nodes.new("ShaderNodeTexImage")
            normal_tex.name = "Baked Normal"
            normal_tex.label = "Baked Normal"
            normal_tex.location = (x_pos, 0)
            normal_img = bpy.data.images.load("{normal_path}")
            normal_img.colorspace_settings.name = 'Non-Color'
            normal_tex.image = normal_img
            
            normal_map = nodes.new("ShaderNodeNormalMap")
            normal_map.name = "Normal Map"
            normal_map.location = (x_pos + 300, 0)
            
            links.new(normal_tex.outputs["Color"], normal_map.inputs["Color"])
            links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
        
        # Roughness
        if "{roughness_path}":
            roughness_tex = nodes.new("ShaderNodeTexImage")
            roughness_tex.name = "Baked Roughness"
            roughness_tex.label = "Baked Roughness"
            roughness_tex.location = (x_pos, -300)
            roughness_img = bpy.data.images.load("{roughness_path}")
            roughness_img.colorspace_settings.name = 'Non-Color'
            roughness_tex.image = roughness_img
            links.new(roughness_tex.outputs["Color"], bsdf.inputs["Roughness"])
        
        # Remove old procedural nodes
        for node_name in to_remove:
            if node_name in nodes:
                nodes.remove(nodes[node_name])
        
        print("SUCCESS:Replaced procedural nodes with baked textures")
"""
        
        result = self.bridge.execute_blender_code(code)
        
        if "SUCCESS:" in result:
            return {"success": True, "message": "Material updated with baked textures"}
        else:
            error = result.split("ERROR:")[1].split('\n')[0] if "ERROR:" in result else result
            return {"success": False, "error": error}
    
    def bake_and_replace(
        self,
        material_name: str,
        object_name: str,
        resolution: int = 2048,
        output_dir: Optional[str] = None,
        bake_types: Optional[List[str]] = None,
        prefix: Optional[str] = None,
        samples: int = 16
    ) -> Dict[str, Any]:
        """
        Complete workflow: Bake textures AND replace procedural nodes.
        
        Args:
            material_name: EXACT material name
            object_name: EXACT object name
            resolution: Texture resolution
            output_dir: Output directory
            bake_types: Types to bake (default: DIFFUSE, NORMAL, ROUGHNESS)
            prefix: Filename prefix
            samples: Render samples
        
        Returns:
            Dict with bake results and replacement status
        """
        # Step 1: Bake
        print("=" * 50)
        print("STEP 1: BAKING TEXTURES")
        print("=" * 50)
        
        bake_result = self.bake_only(
            material_name=material_name,
            object_name=object_name,
            resolution=resolution,
            output_dir=output_dir,
            bake_types=bake_types,
            prefix=prefix,
            samples=samples
        )
        
        if not bake_result["success"]:
            return bake_result
        
        # Step 2: Build texture paths
        texture_paths = {}
        for bake_type, info in bake_result["textures"].items():
            if info.get("success") and info.get("path"):
                texture_paths[bake_type] = info["path"]
        
        # Step 3: Replace nodes
        print()
        print("=" * 50)
        print("STEP 2: REPLACING PROCEDURAL NODES")
        print("=" * 50)
        
        replace_result = self.replace_with_baked(material_name, texture_paths)
        
        bake_result["replacement"] = replace_result
        bake_result["success"] = bake_result["success"] and replace_result["success"]
        
        if replace_result["success"]:
            print("  ✓ Material now uses baked textures")
        else:
            print(f"  ✗ {replace_result.get('error', 'Unknown error')}")
        
        return bake_result


# Convenience functions
def bake_material(material_name: str, object_name: str, resolution: int = 2048) -> Dict[str, Any]:
    """Quick bake without replacing nodes."""
    baker = TextureBaker()
    return baker.bake_only(material_name, object_name, resolution)


def bake_and_replace(material_name: str, object_name: str, resolution: int = 2048) -> Dict[str, Any]:
    """Quick bake AND replace procedural nodes."""
    baker = TextureBaker()
    return baker.bake_and_replace(material_name, object_name, resolution)


def list_materials():
    """List all materials and objects."""
    baker = TextureBaker()
    return baker.list_all_materials()


# CLI
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Bake procedural materials to textures")
    parser.add_argument("--list", "-l", action="store_true", help="List all materials and objects")
    parser.add_argument("--material", "-m", help="Material name (exact)")
    parser.add_argument("--object", "-o", help="Object name (exact)")
    parser.add_argument("--resolution", "-r", type=int, default=2048, help="Resolution")
    parser.add_argument("--replace", action="store_true", help="Replace procedural nodes after baking")
    parser.add_argument("--output", "-d", help="Output directory")
    
    args = parser.parse_args()
    
    baker = TextureBaker()
    
    if args.list:
        baker.list_all_materials()
    elif args.material and args.object:
        if args.replace:
            result = baker.bake_and_replace(
                material_name=args.material,
                object_name=args.object,
                resolution=args.resolution,
                output_dir=args.output
            )
        else:
            result = baker.bake_only(
                material_name=args.material,
                object_name=args.object,
                resolution=args.resolution,
                output_dir=args.output
            )
        
        print()
        print("=== RESULT ===")
        print(f"Success: {result['success']}")
        if result.get('textures'):
            for t, info in result['textures'].items():
                status = "✓" if info.get('success') else "✗"
                print(f"  {status} {t}: {info.get('path', info.get('error', 'N/A'))}")
    else:
        parser.print_help()
        print()
        print("IMPORTANT: Always run --list first to get exact material and object names!")
