"""
GLTF Optimizer

Post-processing optimization for GLTF/GLB files.
Cleans up converted models and prepares them for production use.

Optimization Features:
- Mesh: decimation, vertex deduplication, normal recalculation
- Materials: PBR standardization, unused material removal
- Textures: compression, resizing, format conversion
- Scene: hierarchy cleanup, transform baking
"""

import json
import struct
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from copilot_bridge import BlenderCopilotBridge


@dataclass
class OptimizationSettings:
    """Settings for GLTF optimization"""
    
    # Mesh optimization
    decimate: bool = False
    decimate_ratio: float = 0.5  # Target ratio (0.5 = half the faces)
    decimate_min_faces: int = 1000  # Only decimate if above this
    
    merge_vertices: bool = True
    merge_distance: float = 0.0001
    
    recalculate_normals: bool = False
    
    remove_doubles: bool = True
    
    # Material optimization
    remove_unused_materials: bool = True
    standardize_pbr: bool = True
    
    # Texture optimization
    max_texture_size: int = 2048  # Max dimension
    convert_to_webp: bool = False
    texture_quality: int = 90  # For lossy compression
    
    # Scene optimization
    apply_transforms: bool = True
    merge_by_material: bool = False  # Merge meshes with same material
    remove_empty_nodes: bool = True
    
    # Animation optimization
    simplify_animations: bool = False
    animation_tolerance: float = 0.001


class MeshOptimizer:
    """Optimizes mesh geometry"""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 9876):
        self.bridge = BlenderCopilotBridge(host, port)
    
    def optimize_mesh(
        self,
        object_name: str,
        decimate: bool = False,
        decimate_ratio: float = 0.5,
        remove_doubles: bool = True,
        merge_distance: float = 0.0001,
        recalculate_normals: bool = False,
    ) -> Dict[str, Any]:
        """
        Optimize a single mesh object in Blender.
        
        Returns stats about the optimization.
        """
        code = f'''
import bpy
import json

result = {{
    "success": False,
    "object": "{object_name}",
    "before": {{}},
    "after": {{}},
    "operations": []
}}

obj = bpy.data.objects.get("{object_name}")
if not obj or obj.type != "MESH":
    result["error"] = f"Object '{{object_name}}' not found or not a mesh"
else:
    mesh = obj.data
    
    # Record before stats
    result["before"] = {{
        "vertices": len(mesh.vertices),
        "faces": len(mesh.polygons),
        "edges": len(mesh.edges),
    }}
    
    # Make active and enter edit mode
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    
    # Remove doubles
    if {str(remove_doubles).lower()}:
        bpy.ops.mesh.remove_doubles(threshold={merge_distance})
        result["operations"].append("remove_doubles")
    
    # Recalculate normals
    if {str(recalculate_normals).lower()}:
        bpy.ops.mesh.normals_make_consistent(inside=False)
        result["operations"].append("recalculate_normals")
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Decimate
    if {str(decimate).lower()} and len(mesh.polygons) > 100:
        decimate_mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
        decimate_mod.ratio = {decimate_ratio}
        bpy.ops.object.modifier_apply(modifier="Decimate")
        result["operations"].append(f"decimate_{{decimate_ratio}}")
    
    # Record after stats
    mesh = obj.data  # Refresh reference
    result["after"] = {{
        "vertices": len(mesh.vertices),
        "faces": len(mesh.polygons),
        "edges": len(mesh.edges),
    }}
    
    result["reduction"] = {{
        "vertices": result["before"]["vertices"] - result["after"]["vertices"],
        "faces": result["before"]["faces"] - result["after"]["faces"],
        "percent": round((1 - result["after"]["faces"] / max(1, result["before"]["faces"])) * 100, 1)
    }}
    
    result["success"] = True

print(json.dumps(result))
'''
        result_str = self.bridge.execute_blender_code(code)
        try:
            return json.loads(result_str.strip())
        except json.JSONDecodeError:
            return {"error": f"Failed to parse result: {result_str}"}
    
    def optimize_all_meshes(self, settings: OptimizationSettings) -> Dict[str, Any]:
        """Optimize all mesh objects in the scene"""
        code = f'''
import bpy
import json

results = {{
    "optimized": [],
    "total_reduction": {{
        "vertices": 0,
        "faces": 0,
    }},
    "errors": []
}}

mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]

for obj in mesh_objects:
    try:
        mesh = obj.data
        before_verts = len(mesh.vertices)
        before_faces = len(mesh.polygons)
        
        # Skip small meshes for decimation
        if before_faces < {settings.decimate_min_faces}:
            continue
        
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        
        # Edit mode operations
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        
        if {str(settings.remove_doubles).lower()}:
            bpy.ops.mesh.remove_doubles(threshold={settings.merge_distance})
        
        if {str(settings.recalculate_normals).lower()}:
            bpy.ops.mesh.normals_make_consistent(inside=False)
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Decimate
        if {str(settings.decimate).lower()}:
            decimate_mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
            decimate_mod.ratio = {settings.decimate_ratio}
            bpy.ops.object.modifier_apply(modifier="Decimate")
        
        mesh = obj.data
        after_verts = len(mesh.vertices)
        after_faces = len(mesh.polygons)
        
        results["optimized"].append({{
            "name": obj.name,
            "before": {{"vertices": before_verts, "faces": before_faces}},
            "after": {{"vertices": after_verts, "faces": after_faces}},
        }})
        
        results["total_reduction"]["vertices"] += before_verts - after_verts
        results["total_reduction"]["faces"] += before_faces - after_faces
        
        obj.select_set(False)
        
    except Exception as e:
        results["errors"].append(f"{{obj.name}}: {{str(e)}}")
        bpy.ops.object.mode_set(mode='OBJECT')

print(json.dumps(results))
'''
        result_str = self.bridge.execute_blender_code(code)
        try:
            return json.loads(result_str.strip())
        except json.JSONDecodeError:
            return {"error": f"Failed to parse result: {result_str}"}


class MaterialOptimizer:
    """Optimizes materials for GLTF export"""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 9876):
        self.bridge = BlenderCopilotBridge(host, port)
    
    def standardize_materials(self) -> Dict[str, Any]:
        """
        Ensure all materials use Principled BSDF for GLTF compatibility.
        """
        code = '''
import bpy
import json

results = {
    "processed": [],
    "converted": [],
    "warnings": []
}

for mat in bpy.data.materials:
    if not mat.use_nodes:
        mat.use_nodes = True
        results["converted"].append(mat.name)
    
    if mat.node_tree:
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        
        # Find Principled BSDF
        principled = None
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled = node
                break
        
        # Find Material Output
        output = None
        for node in nodes:
            if node.type == 'OUTPUT_MATERIAL':
                output = node
                break
        
        if not principled:
            # Create Principled BSDF
            principled = nodes.new('ShaderNodeBsdfPrincipled')
            principled.location = (0, 0)
            
            # Try to preserve existing color
            for node in nodes:
                if node.type == 'BSDF_DIFFUSE':
                    color = node.inputs['Color'].default_value[:]
                    principled.inputs['Base Color'].default_value = color
                    break
            
            results["converted"].append(mat.name)
        
        if not output:
            output = nodes.new('ShaderNodeOutputMaterial')
            output.location = (300, 0)
        
        # Ensure Principled is connected to output
        surface_input = output.inputs.get('Surface')
        if surface_input and not surface_input.is_linked:
            links.new(principled.outputs['BSDF'], surface_input)
        
        results["processed"].append(mat.name)

print(json.dumps(results))
'''
        result_str = self.bridge.execute_blender_code(code)
        try:
            return json.loads(result_str.strip())
        except json.JSONDecodeError:
            return {"error": f"Failed to parse result: {result_str}"}
    
    def remove_unused_materials(self) -> Dict[str, Any]:
        """Remove materials not used by any object"""
        code = '''
import bpy
import json

# Find used materials
used_materials = set()
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.data:
        for mat_slot in obj.material_slots:
            if mat_slot.material:
                used_materials.add(mat_slot.material.name)

# Remove unused
removed = []
for mat in list(bpy.data.materials):
    if mat.name not in used_materials and mat.users == 0:
        removed.append(mat.name)
        bpy.data.materials.remove(mat)

result = {
    "removed": removed,
    "remaining": len(bpy.data.materials)
}

print(json.dumps(result))
'''
        result_str = self.bridge.execute_blender_code(code)
        try:
            return json.loads(result_str.strip())
        except json.JSONDecodeError:
            return {"error": f"Failed to parse result: {result_str}"}


def optimize_gltf(
    input_path: str,
    output_path: Optional[str] = None,
    settings: Optional[OptimizationSettings] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Optimize a GLTF/GLB file.
    
    Loads the file into Blender, applies optimizations, and re-exports.
    
    Args:
        input_path: Path to input GLTF/GLB
        output_path: Output path (default: overwrite input)
        settings: Optimization settings
        
    Returns:
        (output_path, stats_dict)
    """
    if settings is None:
        settings = OptimizationSettings()
    
    if output_path is None:
        output_path = input_path
    
    bridge = BlenderCopilotBridge()
    
    # Determine format
    is_glb = input_path.lower().endswith('.glb')
    
    input_escaped = input_path.replace("\\", "\\\\").replace("'", "\\'")
    output_escaped = output_path.replace("\\", "\\\\").replace("'", "\\'")
    
    code = f'''
import bpy
import json

result = {{
    "success": False,
    "stats": {{}},
    "warnings": []
}}

try:
    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # Import GLTF
    bpy.ops.import_scene.gltf(filepath='{input_escaped}')
    
    # Record before stats
    total_verts_before = sum(len(obj.data.vertices) for obj in bpy.data.objects if obj.type == 'MESH' and obj.data)
    total_faces_before = sum(len(obj.data.polygons) for obj in bpy.data.objects if obj.type == 'MESH' and obj.data)
    
    result["stats"]["before"] = {{
        "vertices": total_verts_before,
        "faces": total_faces_before,
        "materials": len(bpy.data.materials),
    }}
    
    # Apply optimizations
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.data:
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            
            # Apply transforms
            if {str(settings.apply_transforms).lower()}:
                bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
            
            # Mesh cleanup
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            
            if {str(settings.remove_doubles).lower()}:
                bpy.ops.mesh.remove_doubles(threshold={settings.merge_distance})
            
            if {str(settings.recalculate_normals).lower()}:
                bpy.ops.mesh.normals_make_consistent(inside=False)
            
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Decimate high-poly meshes
            if {str(settings.decimate).lower()} and len(obj.data.polygons) > {settings.decimate_min_faces}:
                decimate_mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
                decimate_mod.ratio = {settings.decimate_ratio}
                bpy.ops.object.modifier_apply(modifier="Decimate")
            
            obj.select_set(False)
    
    # Material optimization
    if {str(settings.remove_unused_materials).lower()}:
        used_mats = set()
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                for slot in obj.material_slots:
                    if slot.material:
                        used_mats.add(slot.material.name)
        
        for mat in list(bpy.data.materials):
            if mat.name not in used_mats and mat.users == 0:
                bpy.data.materials.remove(mat)
    
    # Record after stats
    total_verts_after = sum(len(obj.data.vertices) for obj in bpy.data.objects if obj.type == 'MESH' and obj.data)
    total_faces_after = sum(len(obj.data.polygons) for obj in bpy.data.objects if obj.type == 'MESH' and obj.data)
    
    result["stats"]["after"] = {{
        "vertices": total_verts_after,
        "faces": total_faces_after,
        "materials": len(bpy.data.materials),
    }}
    
    result["stats"]["reduction"] = {{
        "vertices": total_verts_before - total_verts_after,
        "faces": total_faces_before - total_faces_after,
        "percent": round((1 - total_faces_after / max(1, total_faces_before)) * 100, 1)
    }}
    
    # Export
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(
        filepath='{output_escaped}',
        export_format='{"GLB" if is_glb else "GLTF_SEPARATE"}',
        use_selection=True,
        export_apply=True,
    )
    
    result["success"] = True
    result["output"] = '{output_escaped}'

except Exception as e:
    result["error"] = str(e)

print(json.dumps(result))
'''
    
    result_str = bridge.execute_blender_code(code)
    
    try:
        result = json.loads(result_str.strip())
        return output_path, result
    except json.JSONDecodeError:
        return output_path, {"error": f"Failed to parse result: {result_str}"}


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Optimize GLTF/GLB files")
    parser.add_argument("input", help="Input GLTF/GLB file")
    parser.add_argument("-o", "--output", help="Output file (default: overwrite)")
    parser.add_argument("--decimate", type=float, help="Decimate ratio (e.g., 0.5)")
    parser.add_argument("--remove-doubles", action="store_true", help="Remove duplicate vertices")
    parser.add_argument("--recalc-normals", action="store_true", help="Recalculate normals")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    settings = OptimizationSettings(
        decimate=args.decimate is not None,
        decimate_ratio=args.decimate or 0.5,
        remove_doubles=args.remove_doubles,
        recalculate_normals=args.recalc_normals,
    )
    
    output, result = optimize_gltf(args.input, args.output, settings)
    
    if result.get("success"):
        print(f"Optimized: {args.input} -> {output}")
        print(f"Stats: {json.dumps(result.get('stats', {}), indent=2)}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
