"""
FBX to GLTF Converter

Converts FBX files to optimized GLTF/GLB using Blender as the conversion engine.
FBX is a complex binary format - Blender handles the parsing, we handle optimization.

FBX Format Notes:
- Binary or ASCII format (we handle both via Blender)
- Full scene support: geometry, materials, lights, cameras, animation
- Skeletal animation and skinning
- Various coordinate systems and unit scales
- Embedded textures possible
"""

import os
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from copilot_bridge import BlenderCopilotBridge


@dataclass
class FBXImportSettings:
    """Settings for FBX import"""
    # Transform
    global_scale: float = 1.0
    apply_transform: bool = True
    
    # Axis conversion (FBX can use various systems)
    axis_forward: str = '-Z'  # Blender default
    axis_up: str = 'Y'
    
    # Animation
    import_animation: bool = True
    animation_offset: float = 1.0
    
    # Armature
    import_armature: bool = True
    ignore_leaf_bones: bool = False
    automatic_bone_orientation: bool = True
    
    # Mesh
    import_mesh: bool = True
    
    # Materials
    import_materials: bool = True


@dataclass
class GLTFExportSettings:
    """Settings for GLTF export"""
    # Format
    export_format: str = 'GLB'  # GLB or GLTF_SEPARATE
    
    # Include
    export_textures: bool = True
    export_normals: bool = True
    export_tangents: bool = False
    export_colors: bool = True
    export_materials: bool = True
    export_cameras: bool = True
    export_lights: bool = True
    export_animations: bool = True
    
    # Transform
    export_yup: bool = True  # GLTF uses Y-up
    
    # Compression
    export_draco: bool = False
    draco_compression_level: int = 6
    
    # Optimization
    export_apply_modifiers: bool = True
    use_mesh_edges: bool = False
    use_mesh_vertices: bool = False


class FBXConverter:
    """
    Converts FBX files to GLTF/GLB using Blender.
    
    Pipeline:
    1. Import FBX into Blender (handles all FBX complexity)
    2. Clean up scene (apply transforms, fix materials)
    3. Optimize (optional mesh decimation, texture compression)
    4. Export as GLTF/GLB
    
    Requires: Blender with MCP addon running
    """
    
    def __init__(self, host: str = '127.0.0.1', port: int = 9876):
        self.bridge = BlenderCopilotBridge(host, port)
        self.warnings: List[str] = []
        self.stats: Dict[str, Any] = {}
    
    def convert(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        binary: bool = True,
        import_settings: Optional[FBXImportSettings] = None,
        export_settings: Optional[GLTFExportSettings] = None,
        clear_scene: bool = True,
        optimize: bool = True,
    ) -> str:
        """
        Convert FBX to GLTF/GLB.
        
        Args:
            input_path: Path to .fbx file
            output_path: Output path (default: same name with .glb/.gltf)
            binary: Output GLB (True) or GLTF (False)
            import_settings: FBX import settings
            export_settings: GLTF export settings
            clear_scene: Clear Blender scene before import
            optimize: Apply optimization passes
            
        Returns:
            Path to output file
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"FBX file not found: {input_path}")
        
        input_path = os.path.abspath(input_path)
        
        # Determine output path
        if output_path is None:
            ext = '.glb' if binary else '.gltf'
            output_path = str(Path(input_path).with_suffix(ext))
        output_path = os.path.abspath(output_path)
        
        # Default settings
        if import_settings is None:
            import_settings = FBXImportSettings()
        if export_settings is None:
            export_settings = GLTFExportSettings()
            export_settings.export_format = 'GLB' if binary else 'GLTF_SEPARATE'
        
        # Build conversion script
        code = self._build_conversion_script(
            input_path,
            output_path,
            import_settings,
            export_settings,
            clear_scene,
            optimize
        )
        
        # Execute in Blender
        result_str = self.bridge.execute_blender_code(code)
        
        try:
            result = json.loads(result_str.strip())
        except json.JSONDecodeError:
            raise RuntimeError(f"Failed to parse conversion result: {result_str}")
        
        if result.get("error"):
            raise RuntimeError(f"Conversion failed: {result['error']}")
        
        self.warnings = result.get("warnings", [])
        self.stats = result.get("stats", {})
        
        return output_path
    
    def _build_conversion_script(
        self,
        input_path: str,
        output_path: str,
        import_settings: FBXImportSettings,
        export_settings: GLTFExportSettings,
        clear_scene: bool,
        optimize: bool
    ) -> str:
        """Build Blender Python script for conversion"""
        
        # Escape paths
        input_escaped = input_path.replace("\\", "\\\\").replace("'", "\\'")
        output_escaped = output_path.replace("\\", "\\\\").replace("'", "\\'")
        
        script = f'''
import bpy
import json
import os
from mathutils import Vector

result = {{
    "success": False,
    "warnings": [],
    "stats": {{}},
    "error": None
}}

try:
    # Clear scene
    if {str(clear_scene).lower()}:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        
        # Clear orphan data
        for block in bpy.data.meshes:
            if block.users == 0:
                bpy.data.meshes.remove(block)
        for block in bpy.data.materials:
            if block.users == 0:
                bpy.data.materials.remove(block)
        for block in bpy.data.images:
            if block.users == 0:
                bpy.data.images.remove(block)
        for block in bpy.data.armatures:
            if block.users == 0:
                bpy.data.armatures.remove(block)
        for block in bpy.data.actions:
            if block.users == 0:
                bpy.data.actions.remove(block)
    
    # Record pre-import state
    pre_objects = set(obj.name for obj in bpy.data.objects)
    
    # Import FBX
    bpy.ops.import_scene.fbx(
        filepath='{input_escaped}',
        global_scale={import_settings.global_scale},
        use_custom_normals=True,
        use_image_search=True,
        use_alpha_decals=False,
        decal_offset=0.0,
        use_anim={str(import_settings.import_animation).lower()},
        anim_offset={import_settings.animation_offset},
        use_subsurf=False,
        use_custom_props=True,
        use_custom_props_enum_as_string=True,
        ignore_leaf_bones={str(import_settings.ignore_leaf_bones).lower()},
        force_connect_children=False,
        automatic_bone_orientation={str(import_settings.automatic_bone_orientation).lower()},
        primary_bone_axis='Y',
        secondary_bone_axis='X',
        use_prepost_rot=True,
        axis_forward='{import_settings.axis_forward}',
        axis_up='{import_settings.axis_up}',
    )
    
    # Find imported objects
    new_objects = [obj for obj in bpy.data.objects if obj.name not in pre_objects]
    
    # Collect stats
    mesh_count = 0
    total_verts = 0
    total_faces = 0
    armature_count = 0
    animation_count = len(bpy.data.actions)
    material_count = 0
    light_count = 0
    camera_count = 0
    
    for obj in new_objects:
        if obj.type == 'MESH':
            mesh_count += 1
            if obj.data:
                total_verts += len(obj.data.vertices)
                total_faces += len(obj.data.polygons)
                material_count += len(obj.data.materials)
        elif obj.type == 'ARMATURE':
            armature_count += 1
        elif obj.type == 'LIGHT':
            light_count += 1
        elif obj.type == 'CAMERA':
            camera_count += 1
    
    result["stats"]["imported"] = {{
        "objects": len(new_objects),
        "meshes": mesh_count,
        "vertices": total_verts,
        "faces": total_faces,
        "armatures": armature_count,
        "animations": animation_count,
        "materials": material_count,
        "lights": light_count,
        "cameras": camera_count,
    }}
    
    # Optimization pass
    if {str(optimize).lower()}:
        for obj in new_objects:
            if obj.type == 'MESH' and obj.data:
                # Check for issues
                mesh = obj.data
                
                # Missing UVs
                if len(mesh.uv_layers) == 0:
                    result["warnings"].append(f"Object '{{obj.name}}' has no UV coordinates")
                
                # Non-manifold check (simplified)
                loose_verts = sum(1 for v in mesh.vertices if len(v.link_edges) == 0)
                if loose_verts > 0:
                    result["warnings"].append(f"Object '{{obj.name}}' has {{loose_verts}} loose vertices")
                
                # Apply transforms for cleaner export
                if {str(import_settings.apply_transform).lower()}:
                    obj.select_set(True)
                    bpy.context.view_layer.objects.active = obj
        
        # Apply transforms to selected
        if {str(import_settings.apply_transform).lower()}:
            try:
                bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
            except:
                pass
    
    # Fix materials for GLTF compatibility
    for mat in bpy.data.materials:
        if mat.use_nodes and mat.node_tree:
            # Ensure Principled BSDF exists
            has_principled = any(n.type == 'BSDF_PRINCIPLED' for n in mat.node_tree.nodes)
            if not has_principled:
                result["warnings"].append(f"Material '{{mat.name}}' may not export correctly (no Principled BSDF)")
    
    # Select all imported objects for export
    bpy.ops.object.select_all(action='DESELECT')
    for obj in new_objects:
        obj.select_set(True)
    
    # Export GLTF
    bpy.ops.export_scene.gltf(
        filepath='{output_escaped}',
        export_format='{export_settings.export_format}',
        export_texcoords=True,
        export_normals={str(export_settings.export_normals).lower()},
        export_tangents={str(export_settings.export_tangents).lower()},
        export_materials='EXPORT' if {str(export_settings.export_materials).lower()} else 'NONE',
        export_colors={str(export_settings.export_colors).lower()},
        export_cameras={str(export_settings.export_cameras).lower()},
        export_lights={str(export_settings.export_lights).lower()},
        export_animations={str(export_settings.export_animations).lower()},
        export_yup={str(export_settings.export_yup).lower()},
        export_apply={str(export_settings.export_apply_modifiers).lower()},
        use_selection=True,
    )
    
    # Final stats
    result["stats"]["output"] = {{
        "format": '{export_settings.export_format}',
        "filepath": '{output_escaped}',
    }}
    
    result["success"] = True

except Exception as e:
    result["error"] = str(e)
    import traceback
    result["traceback"] = traceback.format_exc()

print(json.dumps(result))
'''
        return script
    
    def get_fbx_info(self, filepath: str) -> Dict[str, Any]:
        """
        Get information about an FBX file without full conversion.
        
        Imports FBX and gathers stats, then clears the scene.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"FBX file not found: {filepath}")
        
        filepath_escaped = filepath.replace("\\", "\\\\").replace("'", "\\'")
        
        code = f'''
import bpy
import json
import os

result = {{}}

try:
    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # Import FBX
    bpy.ops.import_scene.fbx(filepath='{filepath_escaped}')
    
    # Gather info
    result["filepath"] = '{filepath_escaped}'
    result["file_size_mb"] = round(os.path.getsize('{filepath_escaped}') / (1024*1024), 2)
    
    result["objects"] = len(bpy.data.objects)
    result["meshes"] = len([o for o in bpy.data.objects if o.type == 'MESH'])
    result["armatures"] = len([o for o in bpy.data.objects if o.type == 'ARMATURE'])
    result["lights"] = len([o for o in bpy.data.objects if o.type == 'LIGHT'])
    result["cameras"] = len([o for o in bpy.data.objects if o.type == 'CAMERA'])
    
    result["materials"] = len(bpy.data.materials)
    result["textures"] = len(bpy.data.images)
    result["animations"] = len(bpy.data.actions)
    
    total_verts = 0
    total_faces = 0
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.data:
            total_verts += len(obj.data.vertices)
            total_faces += len(obj.data.polygons)
    
    result["total_vertices"] = total_verts
    result["total_faces"] = total_faces
    
    # Bone info
    total_bones = 0
    for arm in bpy.data.armatures:
        total_bones += len(arm.bones)
    result["total_bones"] = total_bones
    
    # Animation info
    if bpy.data.actions:
        result["animation_info"] = []
        for action in bpy.data.actions:
            result["animation_info"].append({{
                "name": action.name,
                "frame_range": list(action.frame_range),
                "curves": len(action.fcurves),
            }})
    
    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

except Exception as e:
    result["error"] = str(e)

print(json.dumps(result))
'''
        
        result_str = self.bridge.execute_blender_code(code)
        
        try:
            return json.loads(result_str.strip())
        except json.JSONDecodeError:
            return {"error": f"Failed to parse result: {result_str}"}


# ============================================================================
# Convenience Functions
# ============================================================================

def fbx_to_gltf(
    input_path: str,
    output_path: Optional[str] = None,
    binary: bool = True,
    **kwargs
) -> Tuple[str, Dict[str, Any]]:
    """
    Convert FBX to GLTF/GLB.
    
    Args:
        input_path: Path to .fbx file
        output_path: Output path (optional)
        binary: Output GLB (True) or GLTF (False)
        **kwargs: Additional options for FBXConverter.convert()
        
    Returns:
        (output_path, info_dict)
    """
    converter = FBXConverter()
    output = converter.convert(input_path, output_path, binary=binary, **kwargs)
    
    return output, {
        "stats": converter.stats,
        "warnings": converter.warnings
    }


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert FBX to GLTF/GLB")
    parser.add_argument("input", help="Input FBX file")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("--gltf", action="store_true", help="Output GLTF instead of GLB")
    parser.add_argument("--info", action="store_true", help="Show file info without converting")
    parser.add_argument("--no-optimize", action="store_true", help="Skip optimization")
    parser.add_argument("--no-animation", action="store_true", help="Don't import animations")
    parser.add_argument("--scale", type=float, default=1.0, help="Global scale factor")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    converter = FBXConverter()
    
    if args.info:
        info = converter.get_fbx_info(args.input)
        print(json.dumps(info, indent=2))
    else:
        import_settings = FBXImportSettings(
            global_scale=args.scale,
            import_animation=not args.no_animation,
        )
        
        output, info = fbx_to_gltf(
            args.input,
            args.output,
            binary=not args.gltf,
            import_settings=import_settings,
            optimize=not args.no_optimize,
        )
        
        print(f"Converted: {args.input} -> {output}")
        print(f"Stats: {json.dumps(info['stats'], indent=2)}")
        
        if args.verbose and info['warnings']:
            print("\nWarnings:")
            for w in info['warnings']:
                print(f"  - {w}")
