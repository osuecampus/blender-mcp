"""
OBJ to GLTF Converter

Parses OBJ files (with MTL materials) and converts to optimized GLTF/GLB.
Handles common OBJ quirks and produces clean, standardized output.

OBJ Format Notes:
- Text-based, simple geometry
- Separate MTL file for materials
- No animation support (geometry only)
- Various face formats: triangles, quads, n-gons
- Optional: normals, UVs, vertex colors (via extension)
"""

import os
import re
import json
import struct
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field


@dataclass
class OBJVertex:
    """Vertex with position, normal, and UV indices"""
    position_idx: int
    normal_idx: Optional[int] = None
    uv_idx: Optional[int] = None


@dataclass
class OBJFace:
    """Face with vertex references"""
    vertices: List[OBJVertex] = field(default_factory=list)
    material: Optional[str] = None


@dataclass
class OBJMaterial:
    """Material parsed from MTL file"""
    name: str
    # Ambient, Diffuse, Specular
    ambient: Tuple[float, float, float] = (0.2, 0.2, 0.2)
    diffuse: Tuple[float, float, float] = (0.8, 0.8, 0.8)
    specular: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    emission: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    # Shininess, transparency
    shininess: float = 0.0
    transparency: float = 1.0  # 1.0 = opaque
    ior: float = 1.0
    # Illumination model
    illum: int = 2
    # Textures
    map_diffuse: Optional[str] = None
    map_ambient: Optional[str] = None
    map_specular: Optional[str] = None
    map_bump: Optional[str] = None
    map_normal: Optional[str] = None
    map_opacity: Optional[str] = None
    
    def to_pbr(self) -> Dict[str, Any]:
        """Convert to PBR material properties for GLTF"""
        # Approximate roughness from shininess (Ns)
        # High shininess = low roughness
        roughness = 1.0 - min(1.0, self.shininess / 1000.0)
        
        # Metallic is hard to determine from OBJ
        # Use specular intensity as a rough approximation
        spec_intensity = sum(self.specular) / 3.0
        metallic = max(0.0, min(1.0, spec_intensity - 0.5)) if spec_intensity > 0.5 else 0.0
        
        return {
            "base_color": list(self.diffuse) + [self.transparency],
            "metallic": metallic,
            "roughness": roughness,
            "emission": list(self.emission),
            "ior": self.ior,
            "textures": {
                "diffuse": self.map_diffuse,
                "normal": self.map_normal or self.map_bump,
                "specular": self.map_specular,
                "ambient_occlusion": self.map_ambient,
                "opacity": self.map_opacity,
            }
        }


@dataclass 
class OBJMesh:
    """Parsed OBJ mesh data"""
    name: str
    positions: List[Tuple[float, float, float]] = field(default_factory=list)
    normals: List[Tuple[float, float, float]] = field(default_factory=list)
    uvs: List[Tuple[float, float]] = field(default_factory=list)
    faces: List[OBJFace] = field(default_factory=list)
    materials: Dict[str, OBJMaterial] = field(default_factory=dict)
    
    # Groups/objects for organization
    groups: Dict[str, List[int]] = field(default_factory=dict)  # group name -> face indices


class OBJParser:
    """
    Parses OBJ files into structured data.
    
    Handles:
    - Vertices (v), normals (vn), UVs (vt)
    - Faces with various formats (v, v/vt, v/vt/vn, v//vn)
    - Groups (g) and objects (o)
    - Material library (mtllib) and usage (usemtl)
    - Negative indices (relative to end)
    """
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset parser state"""
        self.positions: List[Tuple[float, float, float]] = []
        self.normals: List[Tuple[float, float, float]] = []
        self.uvs: List[Tuple[float, float]] = []
        self.faces: List[OBJFace] = []
        self.materials: Dict[str, OBJMaterial] = {}
        self.groups: Dict[str, List[int]] = {}
        self.current_group: str = "default"
        self.current_material: Optional[str] = None
        self.mtl_files: List[str] = []
        self.warnings: List[str] = []
        self.base_path: Path = Path(".")
    
    def parse(self, filepath: str) -> OBJMesh:
        """
        Parse an OBJ file.
        
        Args:
            filepath: Path to .obj file
            
        Returns:
            OBJMesh with parsed data
        """
        self.reset()
        self.base_path = Path(filepath).parent
        
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        
        for line_num, line in enumerate(lines, 1):
            try:
                self._parse_line(line.strip(), line_num)
            except Exception as e:
                self.warnings.append(f"Line {line_num}: {e}")
        
        # Load referenced MTL files
        for mtl_file in self.mtl_files:
            mtl_path = self.base_path / mtl_file
            if mtl_path.exists():
                self._parse_mtl(str(mtl_path))
            else:
                self.warnings.append(f"MTL file not found: {mtl_file}")
        
        # Build mesh
        mesh = OBJMesh(
            name=Path(filepath).stem,
            positions=self.positions,
            normals=self.normals,
            uvs=self.uvs,
            faces=self.faces,
            materials=self.materials,
            groups=self.groups,
        )
        
        return mesh
    
    def _parse_line(self, line: str, line_num: int):
        """Parse a single OBJ line"""
        if not line or line.startswith('#'):
            return
        
        parts = line.split()
        if not parts:
            return
        
        cmd = parts[0].lower()
        args = parts[1:]
        
        if cmd == 'v':
            # Vertex position
            if len(args) >= 3:
                self.positions.append((
                    float(args[0]),
                    float(args[1]),
                    float(args[2])
                ))
        
        elif cmd == 'vn':
            # Vertex normal
            if len(args) >= 3:
                self.normals.append((
                    float(args[0]),
                    float(args[1]),
                    float(args[2])
                ))
        
        elif cmd == 'vt':
            # Texture coordinate
            if len(args) >= 2:
                self.uvs.append((
                    float(args[0]),
                    float(args[1])
                ))
        
        elif cmd == 'f':
            # Face
            face = self._parse_face(args)
            face.material = self.current_material
            self.faces.append(face)
            
            # Track in current group
            face_idx = len(self.faces) - 1
            if self.current_group not in self.groups:
                self.groups[self.current_group] = []
            self.groups[self.current_group].append(face_idx)
        
        elif cmd == 'g' or cmd == 'o':
            # Group or object
            self.current_group = args[0] if args else "default"
        
        elif cmd == 'usemtl':
            # Use material
            self.current_material = args[0] if args else None
        
        elif cmd == 'mtllib':
            # Material library
            self.mtl_files.extend(args)
        
        elif cmd == 's':
            # Smoothing group (we'll handle this in optimization)
            pass
    
    def _parse_face(self, args: List[str]) -> OBJFace:
        """Parse face vertices"""
        face = OBJFace()
        
        for vert_str in args:
            parts = vert_str.split('/')
            
            # Position index (required)
            pos_idx = int(parts[0])
            if pos_idx < 0:
                pos_idx = len(self.positions) + pos_idx + 1
            
            # UV index (optional)
            uv_idx = None
            if len(parts) > 1 and parts[1]:
                uv_idx = int(parts[1])
                if uv_idx < 0:
                    uv_idx = len(self.uvs) + uv_idx + 1
            
            # Normal index (optional)
            normal_idx = None
            if len(parts) > 2 and parts[2]:
                normal_idx = int(parts[2])
                if normal_idx < 0:
                    normal_idx = len(self.normals) + normal_idx + 1
            
            face.vertices.append(OBJVertex(
                position_idx=pos_idx,
                uv_idx=uv_idx,
                normal_idx=normal_idx
            ))
        
        return face
    
    def _parse_mtl(self, filepath: str):
        """Parse MTL material file"""
        current_material: Optional[OBJMaterial] = None
        
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split()
                if not parts:
                    continue
                
                cmd = parts[0].lower()
                args = parts[1:]
                
                if cmd == 'newmtl':
                    # Save previous material
                    if current_material:
                        self.materials[current_material.name] = current_material
                    # Start new material
                    name = ' '.join(args)
                    current_material = OBJMaterial(name=name)
                
                elif current_material:
                    if cmd == 'ka':
                        current_material.ambient = tuple(float(x) for x in args[:3])
                    elif cmd == 'kd':
                        current_material.diffuse = tuple(float(x) for x in args[:3])
                    elif cmd == 'ks':
                        current_material.specular = tuple(float(x) for x in args[:3])
                    elif cmd == 'ke':
                        current_material.emission = tuple(float(x) for x in args[:3])
                    elif cmd == 'ns':
                        current_material.shininess = float(args[0])
                    elif cmd == 'd':
                        current_material.transparency = float(args[0])
                    elif cmd == 'tr':
                        current_material.transparency = 1.0 - float(args[0])
                    elif cmd == 'ni':
                        current_material.ior = float(args[0])
                    elif cmd == 'illum':
                        current_material.illum = int(args[0])
                    elif cmd == 'map_kd':
                        current_material.map_diffuse = ' '.join(args)
                    elif cmd == 'map_ka':
                        current_material.map_ambient = ' '.join(args)
                    elif cmd == 'map_ks':
                        current_material.map_specular = ' '.join(args)
                    elif cmd in ('map_bump', 'bump'):
                        current_material.map_bump = ' '.join(args)
                    elif cmd == 'map_d':
                        current_material.map_opacity = ' '.join(args)
                    elif cmd == 'norm':
                        current_material.map_normal = ' '.join(args)
        
        # Save last material
        if current_material:
            self.materials[current_material.name] = current_material


class OBJConverter:
    """
    Converts OBJ files to GLTF/GLB format.
    
    Pipeline:
    1. Parse OBJ + MTL files
    2. Triangulate n-gon faces
    3. Generate missing normals
    4. Build indexed vertex buffer
    5. Convert materials to PBR
    6. Export as GLTF/GLB
    """
    
    def __init__(self):
        self.parser = OBJParser()
        self.warnings: List[str] = []
        self.stats: Dict[str, Any] = {}
    
    def convert(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        binary: bool = True,
        optimize: bool = True,
        generate_normals: bool = True,
        flip_uv_y: bool = True,
    ) -> str:
        """
        Convert OBJ to GLTF/GLB.
        
        Args:
            input_path: Path to .obj file
            output_path: Output path (default: same name with .glb/.gltf)
            binary: Output GLB (True) or GLTF (False)
            optimize: Apply mesh optimization
            generate_normals: Generate normals if missing
            flip_uv_y: Flip UV Y coordinate (OBJ vs GLTF convention)
            
        Returns:
            Path to output file
        """
        # Parse OBJ
        mesh = self.parser.parse(input_path)
        self.warnings.extend(self.parser.warnings)
        
        # Determine output path
        if output_path is None:
            ext = '.glb' if binary else '.gltf'
            output_path = str(Path(input_path).with_suffix(ext))
        
        # Triangulate faces
        triangulated_faces = self._triangulate(mesh.faces)
        
        # Build vertex buffer (de-duplicate by vertex signature)
        vertices, indices, has_normals, has_uvs = self._build_vertex_buffer(
            mesh, triangulated_faces, flip_uv_y
        )
        
        # Generate normals if needed
        if generate_normals and not has_normals:
            vertices = self._generate_normals(vertices, indices)
            has_normals = True
        
        # Build GLTF structure
        gltf = self._build_gltf(
            mesh.name,
            vertices,
            indices,
            has_normals,
            has_uvs,
            mesh.materials,
            mesh.groups
        )
        
        # Record stats
        self.stats = {
            "input_vertices": len(mesh.positions),
            "input_faces": len(mesh.faces),
            "output_vertices": len(vertices),
            "output_triangles": len(indices) // 3,
            "materials": len(mesh.materials),
            "groups": len(mesh.groups),
            "warnings": len(self.warnings),
        }
        
        # Write output
        if binary:
            self._write_glb(gltf, output_path)
        else:
            self._write_gltf(gltf, output_path)
        
        return output_path
    
    def _triangulate(self, faces: List[OBJFace]) -> List[OBJFace]:
        """Convert n-gon faces to triangles"""
        result = []
        
        for face in faces:
            if len(face.vertices) < 3:
                self.warnings.append(f"Degenerate face with {len(face.vertices)} vertices")
                continue
            
            if len(face.vertices) == 3:
                result.append(face)
            else:
                # Fan triangulation (works well for convex polygons)
                for i in range(1, len(face.vertices) - 1):
                    tri = OBJFace(
                        vertices=[
                            face.vertices[0],
                            face.vertices[i],
                            face.vertices[i + 1]
                        ],
                        material=face.material
                    )
                    result.append(tri)
        
        return result
    
    def _build_vertex_buffer(
        self,
        mesh: OBJMesh,
        faces: List[OBJFace],
        flip_uv_y: bool
    ) -> Tuple[List[Dict], List[int], bool, bool]:
        """
        Build indexed vertex buffer.
        
        Returns:
            (vertices, indices, has_normals, has_uvs)
        """
        # Vertex signature -> index
        vertex_map: Dict[Tuple, int] = {}
        vertices: List[Dict] = []
        indices: List[int] = []
        
        has_normals = len(mesh.normals) > 0
        has_uvs = len(mesh.uvs) > 0
        
        for face in faces:
            for vert in face.vertices:
                # Build vertex signature for deduplication
                pos_idx = vert.position_idx - 1  # OBJ is 1-indexed
                pos = mesh.positions[pos_idx] if pos_idx < len(mesh.positions) else (0, 0, 0)
                
                normal = None
                if vert.normal_idx is not None:
                    n_idx = vert.normal_idx - 1
                    if n_idx < len(mesh.normals):
                        normal = mesh.normals[n_idx]
                
                uv = None
                if vert.uv_idx is not None:
                    uv_idx = vert.uv_idx - 1
                    if uv_idx < len(mesh.uvs):
                        uv = mesh.uvs[uv_idx]
                        if flip_uv_y:
                            uv = (uv[0], 1.0 - uv[1])
                
                # Create signature
                sig = (pos, normal, uv)
                
                if sig in vertex_map:
                    indices.append(vertex_map[sig])
                else:
                    idx = len(vertices)
                    vertex_map[sig] = idx
                    indices.append(idx)
                    
                    vertices.append({
                        "position": pos,
                        "normal": normal,
                        "uv": uv,
                    })
        
        return vertices, indices, has_normals, has_uvs
    
    def _generate_normals(
        self,
        vertices: List[Dict],
        indices: List[int]
    ) -> List[Dict]:
        """Generate smooth vertex normals from face normals"""
        import math
        
        # Initialize normals to zero
        for v in vertices:
            v["normal"] = [0.0, 0.0, 0.0]
        
        # Accumulate face normals
        for i in range(0, len(indices), 3):
            i0, i1, i2 = indices[i], indices[i+1], indices[i+2]
            
            p0 = vertices[i0]["position"]
            p1 = vertices[i1]["position"]
            p2 = vertices[i2]["position"]
            
            # Calculate face normal
            v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
            v2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
            
            normal = (
                v1[1] * v2[2] - v1[2] * v2[1],
                v1[2] * v2[0] - v1[0] * v2[2],
                v1[0] * v2[1] - v1[1] * v2[0]
            )
            
            # Add to vertex normals
            for idx in (i0, i1, i2):
                n = vertices[idx]["normal"]
                vertices[idx]["normal"] = [
                    n[0] + normal[0],
                    n[1] + normal[1],
                    n[2] + normal[2]
                ]
        
        # Normalize
        for v in vertices:
            n = v["normal"]
            length = math.sqrt(n[0]**2 + n[1]**2 + n[2]**2)
            if length > 0:
                v["normal"] = tuple(x / length for x in n)
            else:
                v["normal"] = (0.0, 1.0, 0.0)  # Default up
        
        return vertices
    
    def _build_gltf(
        self,
        name: str,
        vertices: List[Dict],
        indices: List[int],
        has_normals: bool,
        has_uvs: bool,
        materials: Dict[str, OBJMaterial],
        groups: Dict[str, List[int]]
    ) -> Dict[str, Any]:
        """Build GLTF JSON structure with embedded binary data"""
        
        # Build binary buffer
        buffer_data = bytearray()
        
        # Positions
        positions_offset = len(buffer_data)
        pos_min = [float('inf')] * 3
        pos_max = [float('-inf')] * 3
        
        for v in vertices:
            p = v["position"]
            buffer_data.extend(struct.pack('<fff', *p))
            for i in range(3):
                pos_min[i] = min(pos_min[i], p[i])
                pos_max[i] = max(pos_max[i], p[i])
        
        positions_length = len(buffer_data) - positions_offset
        
        # Normals
        normals_offset = None
        normals_length = 0
        if has_normals:
            normals_offset = len(buffer_data)
            for v in vertices:
                n = v.get("normal", (0, 1, 0))
                buffer_data.extend(struct.pack('<fff', *n))
            normals_length = len(buffer_data) - normals_offset
        
        # UVs
        uvs_offset = None
        uvs_length = 0
        if has_uvs:
            uvs_offset = len(buffer_data)
            for v in vertices:
                uv = v.get("uv", (0, 0))
                if uv:
                    buffer_data.extend(struct.pack('<ff', *uv))
                else:
                    buffer_data.extend(struct.pack('<ff', 0.0, 0.0))
            uvs_length = len(buffer_data) - uvs_offset
        
        # Indices
        indices_offset = len(buffer_data)
        # Use uint16 if possible, otherwise uint32
        use_uint32 = len(vertices) > 65535
        for idx in indices:
            if use_uint32:
                buffer_data.extend(struct.pack('<I', idx))
            else:
                buffer_data.extend(struct.pack('<H', idx))
        indices_length = len(buffer_data) - indices_offset
        
        # Build GLTF structure
        gltf = {
            "asset": {
                "version": "2.0",
                "generator": "BlenderMCP GLTF Pipeline"
            },
            "scene": 0,
            "scenes": [{"name": name, "nodes": [0]}],
            "nodes": [{"name": name, "mesh": 0}],
            "meshes": [{
                "name": name,
                "primitives": [{
                    "attributes": {"POSITION": 0},
                    "indices": 1 if not has_normals else (2 if not has_uvs else 3),
                    "mode": 4  # TRIANGLES
                }]
            }],
            "accessors": [],
            "bufferViews": [],
            "buffers": [{
                "byteLength": len(buffer_data)
            }]
        }
        
        # Track accessor index
        accessor_idx = 0
        buffer_view_idx = 0
        
        # Position accessor
        gltf["bufferViews"].append({
            "buffer": 0,
            "byteOffset": positions_offset,
            "byteLength": positions_length,
            "target": 34962  # ARRAY_BUFFER
        })
        gltf["accessors"].append({
            "bufferView": buffer_view_idx,
            "componentType": 5126,  # FLOAT
            "count": len(vertices),
            "type": "VEC3",
            "min": pos_min,
            "max": pos_max
        })
        accessor_idx += 1
        buffer_view_idx += 1
        
        # Normal accessor
        if has_normals:
            gltf["meshes"][0]["primitives"][0]["attributes"]["NORMAL"] = accessor_idx
            gltf["bufferViews"].append({
                "buffer": 0,
                "byteOffset": normals_offset,
                "byteLength": normals_length,
                "target": 34962
            })
            gltf["accessors"].append({
                "bufferView": buffer_view_idx,
                "componentType": 5126,
                "count": len(vertices),
                "type": "VEC3"
            })
            accessor_idx += 1
            buffer_view_idx += 1
        
        # UV accessor
        if has_uvs:
            gltf["meshes"][0]["primitives"][0]["attributes"]["TEXCOORD_0"] = accessor_idx
            gltf["bufferViews"].append({
                "buffer": 0,
                "byteOffset": uvs_offset,
                "byteLength": uvs_length,
                "target": 34962
            })
            gltf["accessors"].append({
                "bufferView": buffer_view_idx,
                "componentType": 5126,
                "count": len(vertices),
                "type": "VEC2"
            })
            accessor_idx += 1
            buffer_view_idx += 1
        
        # Index accessor
        gltf["meshes"][0]["primitives"][0]["indices"] = accessor_idx
        gltf["bufferViews"].append({
            "buffer": 0,
            "byteOffset": indices_offset,
            "byteLength": indices_length,
            "target": 34963  # ELEMENT_ARRAY_BUFFER
        })
        gltf["accessors"].append({
            "bufferView": buffer_view_idx,
            "componentType": 5125 if use_uint32 else 5123,  # UINT or USHORT
            "count": len(indices),
            "type": "SCALAR"
        })
        
        # Materials
        if materials:
            gltf["materials"] = []
            mat_indices = {}
            
            for mat_name, mat in materials.items():
                pbr = mat.to_pbr()
                mat_indices[mat_name] = len(gltf["materials"])
                
                gltf_mat = {
                    "name": mat_name,
                    "pbrMetallicRoughness": {
                        "baseColorFactor": pbr["base_color"],
                        "metallicFactor": pbr["metallic"],
                        "roughnessFactor": pbr["roughness"]
                    }
                }
                
                if sum(pbr["emission"]) > 0:
                    gltf_mat["emissiveFactor"] = pbr["emission"]
                
                if pbr["base_color"][3] < 1.0:
                    gltf_mat["alphaMode"] = "BLEND"
                
                gltf["materials"].append(gltf_mat)
            
            # Assign first material to primitive (simplified - full impl would split by material)
            if mat_indices:
                gltf["meshes"][0]["primitives"][0]["material"] = 0
        
        # Store binary data for writing
        gltf["_binary_data"] = bytes(buffer_data)
        
        return gltf
    
    def _write_glb(self, gltf: Dict[str, Any], filepath: str):
        """Write GLB binary file"""
        binary_data = gltf.pop("_binary_data", b"")
        json_str = json.dumps(gltf, separators=(',', ':'))
        
        # Pad JSON to 4-byte alignment
        json_bytes = json_str.encode('utf-8')
        json_padding = (4 - len(json_bytes) % 4) % 4
        json_bytes += b' ' * json_padding
        
        # Pad binary to 4-byte alignment
        bin_padding = (4 - len(binary_data) % 4) % 4
        binary_data += b'\x00' * bin_padding
        
        # GLB structure
        total_length = 12 + 8 + len(json_bytes) + 8 + len(binary_data)
        
        with open(filepath, 'wb') as f:
            # Header
            f.write(b'glTF')  # Magic
            f.write(struct.pack('<I', 2))  # Version
            f.write(struct.pack('<I', total_length))  # Total length
            
            # JSON chunk
            f.write(struct.pack('<I', len(json_bytes)))  # Chunk length
            f.write(b'JSON')  # Chunk type
            f.write(json_bytes)
            
            # Binary chunk
            f.write(struct.pack('<I', len(binary_data)))  # Chunk length
            f.write(b'BIN\x00')  # Chunk type
            f.write(binary_data)
    
    def _write_gltf(self, gltf: Dict[str, Any], filepath: str):
        """Write GLTF JSON file with separate .bin"""
        binary_data = gltf.pop("_binary_data", b"")
        
        # Write binary buffer
        bin_path = Path(filepath).with_suffix('.bin')
        with open(bin_path, 'wb') as f:
            f.write(binary_data)
        
        # Reference binary file in GLTF
        gltf["buffers"][0]["uri"] = bin_path.name
        
        # Write JSON
        with open(filepath, 'w') as f:
            json.dump(gltf, f, indent=2)


# ============================================================================
# Convenience Functions
# ============================================================================

def obj_to_gltf(
    input_path: str,
    output_path: Optional[str] = None,
    binary: bool = True,
    **kwargs
) -> Tuple[str, Dict[str, Any]]:
    """
    Convert OBJ to GLTF/GLB.
    
    Args:
        input_path: Path to .obj file
        output_path: Output path (optional)
        binary: Output GLB (True) or GLTF (False)
        **kwargs: Additional options for OBJConverter.convert()
        
    Returns:
        (output_path, stats_dict)
    """
    converter = OBJConverter()
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
    
    parser = argparse.ArgumentParser(description="Convert OBJ to GLTF/GLB")
    parser.add_argument("input", help="Input OBJ file")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("--gltf", action="store_true", help="Output GLTF instead of GLB")
    parser.add_argument("--no-normals", action="store_true", help="Don't generate normals")
    parser.add_argument("--no-flip-uv", action="store_true", help="Don't flip UV Y coordinate")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    output, info = obj_to_gltf(
        args.input,
        args.output,
        binary=not args.gltf,
        generate_normals=not args.no_normals,
        flip_uv_y=not args.no_flip_uv,
    )
    
    print(f"Converted: {args.input} -> {output}")
    print(f"Stats: {info['stats']}")
    
    if args.verbose and info['warnings']:
        print("\nWarnings:")
        for w in info['warnings']:
            print(f"  - {w}")
