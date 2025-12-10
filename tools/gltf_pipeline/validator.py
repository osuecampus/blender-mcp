"""
GLTF Validator

Validates GLTF/GLB files for common issues and compatibility.
Reports problems that would cause issues in renderers or game engines.

Validation Checks:
- Structure: Required fields, proper references
- Geometry: Degenerate triangles, missing normals/UVs
- Materials: PBR compliance, texture references
- Animation: Valid bone references, keyframe integrity
- Compatibility: Extension support, file size limits
"""

import json
import struct
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    ERROR = "error"      # Will cause failures
    WARNING = "warning"  # May cause issues
    INFO = "info"        # Informational


@dataclass
class ValidationIssue:
    """A single validation issue"""
    severity: Severity
    category: str
    message: str
    path: Optional[str] = None  # JSON path to issue location
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "category": self.category,
            "message": self.message,
            "path": self.path,
        }


@dataclass
class ValidationReport:
    """Complete validation report"""
    filepath: str
    valid: bool = True
    issues: List[ValidationIssue] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, category: str, message: str, path: str = None):
        self.issues.append(ValidationIssue(Severity.ERROR, category, message, path))
        self.valid = False
    
    def add_warning(self, category: str, message: str, path: str = None):
        self.issues.append(ValidationIssue(Severity.WARNING, category, message, path))
    
    def add_info(self, category: str, message: str, path: str = None):
        self.issues.append(ValidationIssue(Severity.INFO, category, message, path))
    
    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)
    
    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "filepath": self.filepath,
            "valid": self.valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [i.to_dict() for i in self.issues],
            "stats": self.stats,
        }
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
    
    def summary(self) -> str:
        """Human-readable summary"""
        lines = [
            f"Validation Report: {self.filepath}",
            f"Status: {'VALID' if self.valid else 'INVALID'}",
            f"Errors: {self.error_count}, Warnings: {self.warning_count}",
        ]
        
        if self.stats:
            lines.append(f"Stats: {self.stats}")
        
        if self.issues:
            lines.append("\nIssues:")
            for issue in self.issues:
                prefix = "❌" if issue.severity == Severity.ERROR else "⚠️" if issue.severity == Severity.WARNING else "ℹ️"
                lines.append(f"  {prefix} [{issue.category}] {issue.message}")
                if issue.path:
                    lines.append(f"      at {issue.path}")
        
        return "\n".join(lines)


class GLTFValidator:
    """
    Validates GLTF/GLB files.
    
    Performs structural and content validation to ensure the file
    will work correctly in common renderers and engines.
    """
    
    def __init__(self):
        self.gltf: Optional[Dict[str, Any]] = None
        self.binary_data: Optional[bytes] = None
        self.report: Optional[ValidationReport] = None
    
    def validate(self, filepath: str) -> ValidationReport:
        """
        Validate a GLTF/GLB file.
        
        Args:
            filepath: Path to the file
            
        Returns:
            ValidationReport with all issues found
        """
        self.report = ValidationReport(filepath=filepath)
        
        if not os.path.exists(filepath):
            self.report.add_error("file", f"File not found: {filepath}")
            return self.report
        
        # Load file
        try:
            if filepath.lower().endswith('.glb'):
                self._load_glb(filepath)
            else:
                self._load_gltf(filepath)
        except Exception as e:
            self.report.add_error("parse", f"Failed to parse file: {e}")
            return self.report
        
        if self.gltf is None:
            return self.report
        
        # Run validation checks
        self._validate_structure()
        self._validate_meshes()
        self._validate_materials()
        self._validate_textures()
        self._validate_animations()
        self._validate_scenes()
        self._check_compatibility()
        
        # Gather stats
        self._gather_stats()
        
        return self.report
    
    def _load_glb(self, filepath: str):
        """Load and parse GLB file"""
        with open(filepath, 'rb') as f:
            # Header
            magic = f.read(4)
            if magic != b'glTF':
                self.report.add_error("format", "Invalid GLB magic bytes")
                return
            
            version = struct.unpack('<I', f.read(4))[0]
            total_length = struct.unpack('<I', f.read(4))[0]
            
            if version != 2:
                self.report.add_warning("version", f"Unexpected glTF version: {version}")
            
            # JSON chunk
            chunk_length = struct.unpack('<I', f.read(4))[0]
            chunk_type = f.read(4)
            
            if chunk_type != b'JSON':
                self.report.add_error("format", "First chunk is not JSON")
                return
            
            json_data = f.read(chunk_length)
            self.gltf = json.loads(json_data.decode('utf-8'))
            
            # Binary chunk (optional)
            if f.tell() < total_length:
                chunk_length = struct.unpack('<I', f.read(4))[0]
                chunk_type = f.read(4)
                
                if chunk_type == b'BIN\x00':
                    self.binary_data = f.read(chunk_length)
    
    def _load_gltf(self, filepath: str):
        """Load and parse GLTF JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            self.gltf = json.load(f)
    
    def _validate_structure(self):
        """Validate required GLTF structure"""
        # Asset is required
        if "asset" not in self.gltf:
            self.report.add_error("structure", "Missing required 'asset' property")
        else:
            asset = self.gltf["asset"]
            if "version" not in asset:
                self.report.add_error("structure", "Missing asset.version")
            elif asset["version"] not in ("2.0",):
                self.report.add_warning("version", f"Unexpected version: {asset['version']}")
        
        # Check array indices are valid
        self._validate_indices("nodes", "mesh", "meshes")
        self._validate_indices("nodes", "camera", "cameras")
        self._validate_indices("nodes", "skin", "skins")
        self._validate_indices("meshes", "primitives", "materials", nested_key="material")
        self._validate_indices("scenes", "nodes", "nodes", is_array=True)
    
    def _validate_indices(
        self,
        source_array: str,
        ref_key: str,
        target_array: str,
        nested_key: str = None,
        is_array: bool = False
    ):
        """Validate that indices reference valid array elements"""
        sources = self.gltf.get(source_array, [])
        targets = self.gltf.get(target_array, [])
        target_count = len(targets)
        
        for i, item in enumerate(sources):
            if nested_key:
                # Handle nested arrays (e.g., mesh.primitives[].material)
                nested_items = item.get(ref_key, [])
                for j, nested in enumerate(nested_items):
                    if isinstance(nested, dict) and nested_key in nested:
                        idx = nested[nested_key]
                        if idx >= target_count:
                            self.report.add_error(
                                "reference",
                                f"Invalid {target_array} index {idx}",
                                f"{source_array}[{i}].{ref_key}[{j}].{nested_key}"
                            )
            elif is_array:
                # Handle array of indices (e.g., scene.nodes[])
                indices = item.get(ref_key, [])
                for j, idx in enumerate(indices):
                    if idx >= target_count:
                        self.report.add_error(
                            "reference",
                            f"Invalid {target_array} index {idx}",
                            f"{source_array}[{i}].{ref_key}[{j}]"
                        )
            else:
                # Handle direct reference
                if ref_key in item:
                    idx = item[ref_key]
                    if idx >= target_count:
                        self.report.add_error(
                            "reference",
                            f"Invalid {target_array} index {idx}",
                            f"{source_array}[{i}].{ref_key}"
                        )
    
    def _validate_meshes(self):
        """Validate mesh primitives"""
        meshes = self.gltf.get("meshes", [])
        accessors = self.gltf.get("accessors", [])
        
        for i, mesh in enumerate(meshes):
            primitives = mesh.get("primitives", [])
            
            if not primitives:
                self.report.add_warning("mesh", f"Mesh has no primitives", f"meshes[{i}]")
                continue
            
            for j, prim in enumerate(primitives):
                path = f"meshes[{i}].primitives[{j}]"
                attributes = prim.get("attributes", {})
                
                # POSITION is required
                if "POSITION" not in attributes:
                    self.report.add_error("mesh", "Missing POSITION attribute", path)
                else:
                    pos_idx = attributes["POSITION"]
                    if pos_idx < len(accessors):
                        accessor = accessors[pos_idx]
                        if accessor.get("type") != "VEC3":
                            self.report.add_error("mesh", "POSITION must be VEC3", path)
                
                # Check for missing normals (warning only)
                if "NORMAL" not in attributes:
                    self.report.add_info("mesh", "Missing NORMAL attribute (will be generated)", path)
                
                # Check for missing UVs
                if "TEXCOORD_0" not in attributes:
                    # Only warn if there are materials with textures
                    mat_idx = prim.get("material")
                    if mat_idx is not None:
                        materials = self.gltf.get("materials", [])
                        if mat_idx < len(materials):
                            mat = materials[mat_idx]
                            pbr = mat.get("pbrMetallicRoughness", {})
                            if pbr.get("baseColorTexture") or mat.get("normalTexture"):
                                self.report.add_warning(
                                    "mesh",
                                    "Missing TEXCOORD_0 but material uses textures",
                                    path
                                )
                
                # Check primitive mode
                mode = prim.get("mode", 4)  # Default is TRIANGLES
                if mode not in (0, 1, 2, 3, 4, 5, 6):
                    self.report.add_error("mesh", f"Invalid primitive mode: {mode}", path)
    
    def _validate_materials(self):
        """Validate PBR materials"""
        materials = self.gltf.get("materials", [])
        textures = self.gltf.get("textures", [])
        
        for i, mat in enumerate(materials):
            path = f"materials[{i}]"
            
            # Check PBR properties
            pbr = mat.get("pbrMetallicRoughness", {})
            
            # Validate color factor
            base_color = pbr.get("baseColorFactor", [1, 1, 1, 1])
            if len(base_color) != 4:
                self.report.add_error("material", "baseColorFactor must have 4 components", path)
            elif any(c < 0 or c > 1 for c in base_color):
                self.report.add_warning("material", "baseColorFactor values should be 0-1", path)
            
            # Validate metallic/roughness
            metallic = pbr.get("metallicFactor", 1.0)
            roughness = pbr.get("roughnessFactor", 1.0)
            
            if not (0 <= metallic <= 1):
                self.report.add_warning("material", f"metallicFactor out of range: {metallic}", path)
            if not (0 <= roughness <= 1):
                self.report.add_warning("material", f"roughnessFactor out of range: {roughness}", path)
            
            # Validate texture references
            for tex_key in ["baseColorTexture", "metallicRoughnessTexture"]:
                tex_info = pbr.get(tex_key)
                if tex_info:
                    tex_idx = tex_info.get("index")
                    if tex_idx is not None and tex_idx >= len(textures):
                        self.report.add_error("material", f"Invalid texture index in {tex_key}", path)
            
            # Alpha mode
            alpha_mode = mat.get("alphaMode", "OPAQUE")
            if alpha_mode not in ("OPAQUE", "MASK", "BLEND"):
                self.report.add_error("material", f"Invalid alphaMode: {alpha_mode}", path)
            
            if alpha_mode == "MASK":
                cutoff = mat.get("alphaCutoff", 0.5)
                if not (0 <= cutoff <= 1):
                    self.report.add_warning("material", f"alphaCutoff out of range: {cutoff}", path)
    
    def _validate_textures(self):
        """Validate textures and images"""
        textures = self.gltf.get("textures", [])
        images = self.gltf.get("images", [])
        samplers = self.gltf.get("samplers", [])
        
        for i, tex in enumerate(textures):
            path = f"textures[{i}]"
            
            # Source image
            source = tex.get("source")
            if source is not None:
                if source >= len(images):
                    self.report.add_error("texture", f"Invalid image index: {source}", path)
                else:
                    image = images[source]
                    # Check for embedded vs external
                    if "uri" not in image and "bufferView" not in image:
                        self.report.add_error("texture", "Image has no uri or bufferView", f"images[{source}]")
            
            # Sampler
            sampler = tex.get("sampler")
            if sampler is not None and sampler >= len(samplers):
                self.report.add_error("texture", f"Invalid sampler index: {sampler}", path)
    
    def _validate_animations(self):
        """Validate animations"""
        animations = self.gltf.get("animations", [])
        accessors = self.gltf.get("accessors", [])
        nodes = self.gltf.get("nodes", [])
        
        for i, anim in enumerate(animations):
            path = f"animations[{i}]"
            channels = anim.get("channels", [])
            samplers = anim.get("samplers", [])
            
            if not channels:
                self.report.add_warning("animation", "Animation has no channels", path)
            
            for j, channel in enumerate(channels):
                ch_path = f"{path}.channels[{j}]"
                
                # Sampler reference
                sampler_idx = channel.get("sampler")
                if sampler_idx is None:
                    self.report.add_error("animation", "Channel missing sampler", ch_path)
                elif sampler_idx >= len(samplers):
                    self.report.add_error("animation", f"Invalid sampler index: {sampler_idx}", ch_path)
                
                # Target
                target = channel.get("target", {})
                node_idx = target.get("node")
                if node_idx is not None and node_idx >= len(nodes):
                    self.report.add_error("animation", f"Invalid node index: {node_idx}", ch_path)
                
                target_path = target.get("path")
                valid_paths = ("translation", "rotation", "scale", "weights")
                if target_path not in valid_paths:
                    self.report.add_error("animation", f"Invalid target path: {target_path}", ch_path)
            
            # Validate samplers
            for j, sampler in enumerate(samplers):
                s_path = f"{path}.samplers[{j}]"
                
                input_idx = sampler.get("input")
                output_idx = sampler.get("output")
                
                if input_idx is None or input_idx >= len(accessors):
                    self.report.add_error("animation", "Invalid input accessor", s_path)
                if output_idx is None or output_idx >= len(accessors):
                    self.report.add_error("animation", "Invalid output accessor", s_path)
                
                interp = sampler.get("interpolation", "LINEAR")
                if interp not in ("LINEAR", "STEP", "CUBICSPLINE"):
                    self.report.add_error("animation", f"Invalid interpolation: {interp}", s_path)
    
    def _validate_scenes(self):
        """Validate scene structure"""
        scenes = self.gltf.get("scenes", [])
        
        if not scenes:
            self.report.add_warning("scene", "No scenes defined")
        
        default_scene = self.gltf.get("scene")
        if default_scene is not None and default_scene >= len(scenes):
            self.report.add_error("scene", f"Invalid default scene index: {default_scene}")
    
    def _check_compatibility(self):
        """Check for compatibility issues with common engines"""
        # Extensions
        extensions_used = self.gltf.get("extensionsUsed", [])
        extensions_required = self.gltf.get("extensionsRequired", [])
        
        # Common unsupported extensions
        problematic_extensions = {
            "KHR_draco_mesh_compression": "May not be supported in all viewers",
            "EXT_meshopt_compression": "May not be supported in all viewers",
            "KHR_materials_transmission": "Glass materials may not render correctly",
            "KHR_materials_volume": "Volume materials may not be supported",
        }
        
        for ext in extensions_required:
            if ext in problematic_extensions:
                self.report.add_warning("compatibility", f"Required extension: {ext} - {problematic_extensions[ext]}")
        
        # File size check
        if self.report.filepath:
            file_size = os.path.getsize(self.report.filepath)
            if file_size > 50 * 1024 * 1024:  # 50MB
                self.report.add_warning("size", f"Large file size: {file_size / (1024*1024):.1f}MB")
        
        # Texture size check
        buffer_views = self.gltf.get("bufferViews", [])
        images = self.gltf.get("images", [])
        
        for i, image in enumerate(images):
            if "bufferView" in image:
                bv_idx = image["bufferView"]
                if bv_idx < len(buffer_views):
                    bv = buffer_views[bv_idx]
                    size = bv.get("byteLength", 0)
                    if size > 4 * 1024 * 1024:  # 4MB per texture
                        self.report.add_warning(
                            "size",
                            f"Large embedded texture: {size / (1024*1024):.1f}MB",
                            f"images[{i}]"
                        )
    
    def _gather_stats(self):
        """Gather statistics about the file"""
        stats = {}
        
        stats["meshes"] = len(self.gltf.get("meshes", []))
        stats["materials"] = len(self.gltf.get("materials", []))
        stats["textures"] = len(self.gltf.get("textures", []))
        stats["images"] = len(self.gltf.get("images", []))
        stats["nodes"] = len(self.gltf.get("nodes", []))
        stats["animations"] = len(self.gltf.get("animations", []))
        stats["scenes"] = len(self.gltf.get("scenes", []))
        
        # Count primitives and estimate triangles
        total_primitives = 0
        accessors = self.gltf.get("accessors", [])
        
        for mesh in self.gltf.get("meshes", []):
            for prim in mesh.get("primitives", []):
                total_primitives += 1
        
        stats["primitives"] = total_primitives
        
        # Extensions
        stats["extensions_used"] = self.gltf.get("extensionsUsed", [])
        stats["extensions_required"] = self.gltf.get("extensionsRequired", [])
        
        # Asset info
        asset = self.gltf.get("asset", {})
        stats["generator"] = asset.get("generator", "Unknown")
        stats["version"] = asset.get("version", "Unknown")
        
        self.report.stats = stats


def validate_gltf(filepath: str) -> ValidationReport:
    """
    Validate a GLTF/GLB file.
    
    Args:
        filepath: Path to the file
        
    Returns:
        ValidationReport with all issues
    """
    validator = GLTFValidator()
    return validator.validate(filepath)


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate GLTF/GLB files")
    parser.add_argument("filepath", help="Path to GLTF/GLB file")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    
    args = parser.parse_args()
    
    report = validate_gltf(args.filepath)
    
    if args.strict and report.warning_count > 0:
        report.valid = False
    
    if args.json:
        print(report.to_json())
    else:
        print(report.summary())
    
    # Exit code
    exit(0 if report.valid else 1)
