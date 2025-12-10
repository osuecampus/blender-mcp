"""
GLTF Conversion Pipeline

Converts various 3D formats to optimized GLB/GLTF (the canonical format).
Handles messy inputs and produces clean, standardized output.

Supported input formats (in priority order):
1. OBJ (.obj + .mtl)
2. FBX (.fbx)  
3. More to come...

Features:
- Geometry: vertices, normals, UVs, vertex colors
- Materials: PBR conversion, texture handling
- Lighting: point, spot, directional, area
- Animation: skeletal, keyframe
- Optimization: mesh cleanup, texture compression, LOD generation

Quick Start:
    from tools.gltf_pipeline import convert_to_gltf
    
    # Convert any supported format to GLTF
    output, report = convert_to_gltf("model.obj")
    output, report = convert_to_gltf("character.fbx", optimize=True)
    
    # Check the result
    print(report.summary())
"""

from .obj_converter import OBJConverter, obj_to_gltf
from .fbx_converter import FBXConverter, fbx_to_gltf, FBXImportSettings, GLTFExportSettings
from .optimizer import MeshOptimizer, MaterialOptimizer, optimize_gltf, OptimizationSettings
from .validator import validate_gltf, ValidationReport
from .pipeline import convert_to_gltf, batch_convert, get_supported_formats, ConversionReport

__all__ = [
    # Main entry point
    'convert_to_gltf',
    'batch_convert',
    'get_supported_formats',
    'ConversionReport',
    # Converters
    'OBJConverter',
    'FBXConverter',
    'obj_to_gltf',
    'fbx_to_gltf',
    'FBXImportSettings',
    'GLTFExportSettings',
    # Optimization
    'MeshOptimizer',
    'MaterialOptimizer', 
    'optimize_gltf',
    'OptimizationSettings',
    # Validation
    'validate_gltf',
    'ValidationReport',
]
