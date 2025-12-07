#!/usr/bin/env python3
"""
GitHub Copilot Bridge for BlenderMCP
Provides a Python interface to all BlenderMCP tools for use with GitHub Copilot
"""

import socket
import json
import tempfile
import os
from typing import Dict, List, Any, Optional
from pathlib import Path


class BlenderCopilotBridge:
    """Bridge between GitHub Copilot and BlenderMCP tools"""

    def __init__(self, host='127.0.0.1', port=9876):
        self.host = host
        self.port = port

    def _send_command(self, command_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a command to the Blender MCP server"""
        command = {
            "type": command_type,
            "params": params or {}
        }

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(30)  # 30 second timeout
                s.connect((self.host, self.port))
                s.sendall(json.dumps(command).encode('utf-8'))
                
                # Receive all data (responses can be large for complex node groups)
                chunks = []
                while True:
                    try:
                        chunk = s.recv(65536)  # 64KB chunks
                        if not chunk:
                            break
                        chunks.append(chunk)
                        # If we got less than buffer size, likely done
                        if len(chunk) < 65536:
                            break
                    except socket.timeout:
                        break
                
                response = b''.join(chunks)
                result = json.loads(response.decode('utf-8'))

                if result.get("status") == "error":
                    raise Exception(result.get("message", "Unknown error"))

                return result.get("result", {})
        except Exception as e:
            raise Exception(f"Failed to communicate with Blender: {str(e)}")

    # Scene Management
    def get_scene_info(self) -> Dict[str, Any]:
        """Get comprehensive information about the current Blender scene"""
        return self._send_command("get_scene_info")

    def get_object_info(self, object_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific object"""
        return self._send_command("get_object_info", {"name": object_name})

    def capture_viewport_screenshot(self, max_size: int = 800) -> str:
        """Capture a screenshot of the Blender viewport and return the file path"""
        temp_path = os.path.join(
            tempfile.gettempdir(), f"blender_screenshot_{os.getpid()}.png")
        result = self._send_command("get_viewport_screenshot", {
            "max_size": max_size,
            "filepath": temp_path,
            "format": "png"
        })

        if "error" in result:
            raise Exception(result["error"])

        return temp_path

    # Code Execution
    def execute_blender_code(self, code: str) -> str:
        """Execute Python code in Blender"""
        result = self._send_command("execute_code", {"code": code})
        return result.get("result", "")

    # Asset Management - PolyHaven
    def get_polyhaven_status(self) -> Dict[str, Any]:
        """Check if PolyHaven integration is enabled"""
        return self._send_command("get_polyhaven_status")

    def search_polyhaven_assets(self, asset_type: str = "all", categories: str = None) -> List[Dict]:
        """Search for assets on PolyHaven"""
        result = self._send_command("search_polyhaven_assets", {
            "asset_type": asset_type,
            "categories": categories
        })
        return result.get("assets", {})

    def download_polyhaven_asset(self, asset_id: str, asset_type: str,
                                 resolution: str = "1k", file_format: str = None) -> str:
        """Download and import a PolyHaven asset"""
        result = self._send_command("download_polyhaven_asset", {
            "asset_id": asset_id,
            "asset_type": asset_type,
            "resolution": resolution,
            "file_format": file_format
        })

        if result.get("success"):
            return result.get("message", "Asset downloaded successfully")
        else:
            raise Exception(result.get("message", "Download failed"))

    def apply_texture_to_object(self, object_name: str, texture_id: str) -> str:
        """Apply a PolyHaven texture to an object"""
        result = self._send_command("set_texture", {
            "object_name": object_name,
            "texture_id": texture_id
        })

        if result.get("success"):
            return result.get("message", "Texture applied successfully")
        else:
            raise Exception(result.get("message", "Failed to apply texture"))

    # Asset Management - Sketchfab
    def get_sketchfab_status(self) -> Dict[str, Any]:
        """Check if Sketchfab integration is enabled"""
        return self._send_command("get_sketchfab_status")

    def search_sketchfab_models(self, query: str, categories: str = None,
                                count: int = 20, downloadable: bool = True) -> List[Dict]:
        """Search for models on Sketchfab"""
        result = self._send_command("search_sketchfab_models", {
            "query": query,
            "categories": categories,
            "count": count,
            "downloadable": downloadable
        })
        return result.get("results", [])

    def download_sketchfab_model(self, uid: str) -> str:
        """Download and import a Sketchfab model"""
        result = self._send_command("download_sketchfab_model", {"uid": uid})

        if result.get("success"):
            objects = result.get("imported_objects", [])
            return f"Successfully imported: {', '.join(objects)}"
        else:
            raise Exception(result.get("message", "Download failed"))

    # AI Model Generation - Hyper3D
    def get_hyper3d_status(self) -> Dict[str, Any]:
        """Check if Hyper3D integration is enabled"""
        return self._send_command("get_hyper3d_status")

    def generate_3d_model_from_text(self, prompt: str, bbox_condition: List[float] = None) -> Dict[str, Any]:
        """Generate a 3D model from text description using Hyper3D"""
        result = self._send_command("generate_hyper3d_model_via_text", {
            "text_prompt": prompt,
            "bbox_condition": bbox_condition
        })
        return json.loads(result) if isinstance(result, str) else result

    def check_generation_status(self, subscription_key: str = None, request_id: str = None) -> Dict[str, Any]:
        """Check the status of a Hyper3D generation task"""
        params = {}
        if subscription_key:
            params["subscription_key"] = subscription_key
        if request_id:
            params["request_id"] = request_id

        return self._send_command("poll_rodin_job_status", params)

    def import_generated_model(self, name: str, task_uuid: str = None, request_id: str = None) -> Dict[str, Any]:
        """Import a generated 3D model into Blender"""
        params = {"name": name}
        if task_uuid:
            params["task_uuid"] = task_uuid
        if request_id:
            params["request_id"] = request_id

        return self._send_command("import_generated_asset", params)

    # =========================================================================
    # Geometry Node Development Tools (Added 2025-12-07)
    # =========================================================================

    def inspect_node_sockets(self, node_type: str) -> Dict[str, Any]:
        """
        Inspect a geometry node type's sockets and properties BEFORE using it.
        Prevents 'socket not found' errors from Blender API changes.
        
        Args:
            node_type: The node type identifier (e.g., 'GeometryNodeDistributePointsOnFaces')
        
        Returns:
            Dict with 'inputs', 'outputs', 'properties' lists
        """
        code = f'''
import bpy
import json

# Create temp node group to inspect the node
temp = bpy.data.node_groups.new(name="TempInspect", type="GeometryNodeTree")
try:
    node = temp.nodes.new("{node_type}")
    
    inputs = []
    for i, inp in enumerate(node.inputs):
        input_info = {{"index": i, "name": inp.name, "type": inp.bl_idname}}
        if hasattr(inp, "default_value"):
            try:
                val = inp.default_value
                if hasattr(val, "__iter__") and not isinstance(val, str):
                    val = list(val)
                input_info["default"] = val
            except:
                pass
        inputs.append(input_info)
    
    outputs = []
    for i, out in enumerate(node.outputs):
        outputs.append({{"index": i, "name": out.name, "type": out.bl_idname}})
    
    # Get settable properties
    props = []
    skip_props = ["bl_", "rna_", "name", "label", "location", "width", "height", 
                  "parent", "inputs", "outputs", "internal_links", "dimensions",
                  "select", "show_", "use_", "is_", "type", "color", "mute", "hide"]
    for prop in dir(node):
        if not any(prop.startswith(s) for s in skip_props) and not prop.startswith("_"):
            try:
                val = getattr(node, prop)
                if not callable(val):
                    props.append({{"name": prop, "value": str(val)}})
            except:
                pass
    
    result = {{"node_type": "{node_type}", "label": node.bl_label, 
               "inputs": inputs, "outputs": outputs, "properties": props}}
    print(json.dumps(result))
except Exception as e:
    print(json.dumps({{"error": str(e)}}))
finally:
    bpy.data.node_groups.remove(temp)
'''
        result_str = self.execute_blender_code(code)
        try:
            return json.loads(result_str)
        except:
            return {"error": result_str, "node_type": node_type}

    def create_inverse_parameter_pair(self, node_group_name: str, 
                                       param_name: str,
                                       normal_min: float, normal_max: float,
                                       inverse_min: float, inverse_max: float,
                                       location: tuple = (0, 0)) -> Dict[str, Any]:
        """
        Create a parameter with two Map Range nodes - one normal, one inverse.
        Useful for conservation-based systems (e.g., count increases, size decreases).
        
        Args:
            node_group_name: Name of the geometry node group
            param_name: Name for the new parameter
            normal_min/max: Output range for the normal mapping
            inverse_min/max: Output range for the inverse mapping (will be swapped)
            location: (x, y) position for the nodes
        
        Returns:
            Dict with parameter socket ID and node names
        """
        code = f'''
import bpy
import json

ng = bpy.data.node_groups.get("{node_group_name}")
if not ng:
    print(json.dumps({{"error": "Node group not found: {node_group_name}"}}))
else:
    # Create the interface parameter
    param = ng.interface.new_socket(name="{param_name}", in_out="INPUT", socket_type="NodeSocketFloat")
    param.default_value = 0.5
    param.min_value = 0.0
    param.max_value = 1.0
    
    # Find the Group Input node
    group_in = None
    for node in ng.nodes:
        if node.bl_idname == "NodeGroupInput":
            group_in = node
            break
    
    if not group_in:
        group_in = ng.nodes.new("NodeGroupInput")
        group_in.location = ({location[0]} - 400, {location[1]})
    
    # Create normal Map Range
    normal_map = ng.nodes.new("ShaderNodeMapRange")
    normal_map.name = "{param_name}_Normal"
    normal_map.label = "{param_name} (Normal)"
    normal_map.location = ({location[0]}, {location[1]})
    normal_map.inputs["From Min"].default_value = 0.0
    normal_map.inputs["From Max"].default_value = 1.0
    normal_map.inputs["To Min"].default_value = {normal_min}
    normal_map.inputs["To Max"].default_value = {normal_max}
    
    # Create inverse Map Range
    inverse_map = ng.nodes.new("ShaderNodeMapRange")
    inverse_map.name = "{param_name}_Inverse"
    inverse_map.label = "{param_name} (Inverse)"
    inverse_map.location = ({location[0]}, {location[1]} - 150)
    inverse_map.inputs["From Min"].default_value = 0.0
    inverse_map.inputs["From Max"].default_value = 1.0
    inverse_map.inputs["To Min"].default_value = {inverse_min}
    inverse_map.inputs["To Max"].default_value = {inverse_max}
    
    # Connect parameter to both
    ng.links.new(group_in.outputs["{param_name}"], normal_map.inputs["Value"])
    ng.links.new(group_in.outputs["{param_name}"], inverse_map.inputs["Value"])
    
    result = {{
        "parameter_name": "{param_name}",
        "parameter_socket": param.identifier,
        "normal_node": normal_map.name,
        "inverse_node": inverse_map.name,
        "normal_output": "{param_name}_Normal.Result",
        "inverse_output": "{param_name}_Inverse.Result"
    }}
    print(json.dumps(result))
'''
        result_str = self.execute_blender_code(code)
        try:
            return json.loads(result_str)
        except:
            return {"error": result_str}

    def test_parameter_bounds(self, object_name: str, socket_id: str, 
                               test_values: List[float] = None) -> Dict[str, Any]:
        """
        Sweep a parameter across its range and report geometry bounds at each value.
        Useful for testing that geometry stays within expected bounds.
        
        Args:
            object_name: Name of the object with geometry nodes modifier
            socket_id: The socket identifier (e.g., 'Socket_2')
            test_values: List of values to test (default: [0.0, 0.25, 0.5, 0.75, 1.0])
        
        Returns:
            Dict with bounds at each test value and variance analysis
        """
        if test_values is None:
            test_values = [0.0, 0.25, 0.5, 0.75, 1.0]
        
        values_str = str(test_values)
        
        code = f'''
import bpy
import json

obj = bpy.data.objects.get("{object_name}")
if not obj:
    print(json.dumps({{"error": "Object not found: {object_name}"}}))
else:
    mod = None
    for m in obj.modifiers:
        if m.type == "NODES":
            mod = m
            break
    
    if not mod:
        print(json.dumps({{"error": "No geometry nodes modifier found"}}))
    else:
        results = []
        test_values = {values_str}
        
        for val in test_values:
            mod["{socket_id}"] = val
            mod.show_viewport = False
            mod.show_viewport = True
            bpy.context.view_layer.update()
            
            dg = bpy.context.evaluated_depsgraph_get()
            obj_eval = obj.evaluated_get(dg)
            mesh = obj_eval.to_mesh()
            
            if mesh.vertices:
                xs = [v.co.x for v in mesh.vertices]
                ys = [v.co.y for v in mesh.vertices]
                zs = [v.co.z for v in mesh.vertices]
                
                bounds = {{
                    "value": val,
                    "x_min": round(min(xs), 3),
                    "x_max": round(max(xs), 3),
                    "y_min": round(min(ys), 3),
                    "y_max": round(max(ys), 3),
                    "z_min": round(min(zs), 3),
                    "z_max": round(max(zs), 3),
                    "x_range": round(max(xs) - min(xs), 3),
                    "y_range": round(max(ys) - min(ys), 3),
                    "z_range": round(max(zs) - min(zs), 3),
                    "vertex_count": len(mesh.vertices)
                }}
                results.append(bounds)
            
            obj_eval.to_mesh_clear()
        
        # Reset to middle value
        mod["{socket_id}"] = 0.5
        mod.show_viewport = False
        mod.show_viewport = True
        
        # Calculate variance
        if results:
            x_ranges = [r["x_range"] for r in results]
            y_ranges = [r["y_range"] for r in results]
            z_ranges = [r["z_range"] for r in results]
            
            variance = {{
                "x_variance": round(max(x_ranges) - min(x_ranges), 3),
                "y_variance": round(max(y_ranges) - min(y_ranges), 3),
                "z_variance": round(max(z_ranges) - min(z_ranges), 3)
            }}
        else:
            variance = {{"error": "No results"}}
        
        print(json.dumps({{"results": results, "variance": variance}}))
'''
        result_str = self.execute_blender_code(code)
        try:
            return json.loads(result_str)
        except:
            return {"error": result_str}

    def create_volume_blob_system(self, node_group_name: str,
                                   container_size: float = 2.0,
                                   density_range: tuple = (0.5, 15.0),
                                   radius_range: tuple = (0.6, 0.15)) -> Dict[str, Any]:
        """
        Create a complete Points to Volume blob system for organic aggregates.
        
        This creates:
        - Inner distribution cube (80% of container size)
        - Breakdown parameter with inverse density/radius mapping
        - Distribute Points on Faces
        - Points to Volume
        - Volume to Mesh
        - All properly connected
        
        Args:
            node_group_name: Name for the new node group
            container_size: Size of the outer container
            density_range: (min, max) density for point distribution
            radius_range: (min, max) radius for volume spheres (inverse relationship)
        
        Returns:
            Dict with node group name and parameter info
        """
        inner_size = container_size * 0.75
        
        code = f'''
import bpy
import json

# Create the node group
ng = bpy.data.node_groups.new(name="{node_group_name}", type="GeometryNodeTree")

# Interface
ng.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
ng.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
breakdown = ng.interface.new_socket(name="Breakdown", in_out="INPUT", socket_type="NodeSocketFloat")
breakdown.default_value = 0.5
breakdown.min_value = 0.0
breakdown.max_value = 1.0

nodes = ng.nodes
links = ng.links

# Group I/O
group_in = nodes.new("NodeGroupInput")
group_in.location = (-600, 0)
group_out = nodes.new("NodeGroupOutput")
group_out.location = (400, 0)

# Inner cube for distribution
inner_cube = nodes.new("GeometryNodeMeshCube")
inner_cube.name = "InnerCube"
inner_cube.location = (-400, 100)
inner_cube.inputs["Size"].default_value = ({inner_size}, {inner_size}, {inner_size})

# Density mapping (increases with breakdown)
density_map = nodes.new("ShaderNodeMapRange")
density_map.name = "DensityMap"
density_map.location = (-400, -100)
density_map.inputs["From Min"].default_value = 0.0
density_map.inputs["From Max"].default_value = 1.0
density_map.inputs["To Min"].default_value = {density_range[0]}
density_map.inputs["To Max"].default_value = {density_range[1]}
links.new(group_in.outputs["Breakdown"], density_map.inputs["Value"])

# Radius mapping (decreases with breakdown - inverse)
radius_map = nodes.new("ShaderNodeMapRange")
radius_map.name = "RadiusMap"
radius_map.location = (-400, -250)
radius_map.inputs["From Min"].default_value = 0.0
radius_map.inputs["From Max"].default_value = 1.0
radius_map.inputs["To Min"].default_value = {radius_range[0]}
radius_map.inputs["To Max"].default_value = {radius_range[1]}
links.new(group_in.outputs["Breakdown"], radius_map.inputs["Value"])

# Distribute points
distribute = nodes.new("GeometryNodeDistributePointsOnFaces")
distribute.name = "DistributePts"
distribute.location = (-150, 100)
links.new(inner_cube.outputs["Mesh"], distribute.inputs["Mesh"])
links.new(density_map.outputs["Result"], distribute.inputs["Density"])

# Points to Volume
pts_to_vol = nodes.new("GeometryNodePointsToVolume")
pts_to_vol.name = "PointsToVolume"
pts_to_vol.location = (50, 100)
links.new(distribute.outputs["Points"], pts_to_vol.inputs["Points"])
links.new(radius_map.outputs["Result"], pts_to_vol.inputs["Radius"])

# Volume to Mesh
vol_to_mesh = nodes.new("GeometryNodeVolumeToMesh")
vol_to_mesh.name = "VolumeToMesh"
vol_to_mesh.location = (250, 100)
links.new(pts_to_vol.outputs["Volume"], vol_to_mesh.inputs["Volume"])

# Output
links.new(vol_to_mesh.outputs["Mesh"], group_out.inputs["Geometry"])

result = {{
    "node_group": "{node_group_name}",
    "parameter": "Breakdown",
    "parameter_socket": breakdown.identifier,
    "node_count": len(nodes),
    "density_range": [{density_range[0]}, {density_range[1]}],
    "radius_range": [{radius_range[0]}, {radius_range[1]}],
    "container_size": {container_size},
    "inner_size": {inner_size}
}}
print(json.dumps(result))
'''
        result_str = self.execute_blender_code(code)
        try:
            return json.loads(result_str)
        except:
            return {"error": result_str}

    def mothball_scene_objects(self, object_names: List[str], 
                                hide: bool = True) -> Dict[str, Any]:
        """
        Hide and disable modifiers for a list of objects to shelve experiments.
        
        Args:
            object_names: List of object names to mothball
            hide: True to hide/disable, False to unhide/enable
        
        Returns:
            Dict with status for each object
        """
        names_str = str(object_names)
        
        code = f'''
import bpy
import json

object_names = {names_str}
hide = {str(hide)}
results = {{}}

for obj_name in object_names:
    obj = bpy.data.objects.get(obj_name)
    if obj:
        obj.hide_viewport = hide
        obj.hide_render = hide
        
        # Disable/enable modifiers
        mod_count = 0
        for mod in obj.modifiers:
            if mod.type == "NODES":
                mod.show_viewport = not hide
                mod_count += 1
        
        results[obj_name] = {{
            "status": "mothballed" if hide else "restored",
            "modifiers_affected": mod_count
        }}
    else:
        results[obj_name] = {{"status": "not found"}}

print(json.dumps(results))
'''
        result_str = self.execute_blender_code(code)
        try:
            return json.loads(result_str)
        except:
            return {"error": result_str}


# Convenience functions for GitHub Copilot
def create_cube_at_position(x: float, y: float, z: float, size: float = 2.0) -> str:
    """Create a cube at the specified position - GitHub Copilot friendly function"""
    bridge = BlenderCopilotBridge()
    code = f"""
import bpy
bpy.ops.mesh.primitive_cube_add(location=({x}, {y}, {z}), size={size})
"""
    return bridge.execute_blender_code(code)


def create_sphere_at_position(x: float, y: float, z: float, radius: float = 1.0) -> str:
    """Create a sphere at the specified position - GitHub Copilot friendly function"""
    bridge = BlenderCopilotBridge()
    code = f"""
import bpy
bpy.ops.mesh.primitive_uv_sphere_add(location=({x}, {y}, {z}), radius={radius})
"""
    return bridge.execute_blender_code(code)


def clear_scene() -> str:
    """Clear all objects from the Blender scene"""
    bridge = BlenderCopilotBridge()
    code = """
import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
"""
    return bridge.execute_blender_code(code)


def get_scene_summary() -> str:
    """Get a human-readable summary of the current scene"""
    bridge = BlenderCopilotBridge()
    scene_info = bridge.get_scene_info()

    summary = f"Scene: {scene_info.get('name', 'Unknown')}\n"
    summary += f"Total objects: {scene_info.get('object_count', 0)}\n"

    objects = scene_info.get('objects', [])
    if objects:
        summary += "Objects in scene:\n"
        for obj in objects:
            summary += f"  - {obj.get('name', 'Unknown')} ({obj.get('type', 'Unknown')})\n"

    return summary


def download_texture_and_apply(texture_name: str, object_name: str) -> str:
    """Search for a texture on PolyHaven and apply it to an object"""
    bridge = BlenderCopilotBridge()

    # Search for the texture
    assets = bridge.search_polyhaven_assets(asset_type="textures")

    # Find matching texture
    matching_asset = None
    for asset_id, asset_data in assets.items():
        if texture_name.lower() in asset_data.get('name', '').lower():
            matching_asset = asset_id
            break

    if not matching_asset:
        return f"No texture found matching '{texture_name}'"

    # Download the texture
    bridge.download_polyhaven_asset(matching_asset, "textures")

    # Apply to object
    return bridge.apply_texture_to_object(object_name, matching_asset)


def analyze_scene(output_format: str = "text", filepath: str = None) -> str:
    """
    Analyze the current Blender scene including geometry nodes, materials, and objects.
    
    Args:
        output_format: "text" for console output, "markdown" for markdown format
        filepath: Optional path to save the report
    
    Returns:
        The analysis report as a string
    """
    from scene_analyzer import SceneAnalyzer
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


def demo_copilot_integration():
    """Demonstrate how GitHub Copilot can use these functions"""
    print("🚀 GitHub Copilot + BlenderMCP Integration Demo")
    print("=" * 50)

    # Example 1: Scene management
    print("\n📋 Current scene:")
    print(get_scene_summary())

    # Example 2: Create objects
    print("\n🎲 Creating objects...")
    create_cube_at_position(0, 0, 0, 2.0)
    create_sphere_at_position(3, 0, 0, 1.5)

    print("\n📋 Updated scene:")
    print(get_scene_summary())

    # Example 3: Check available integrations
    bridge = BlenderCopilotBridge()
    print("\n🔌 Available integrations:")

    polyhaven_status = bridge.get_polyhaven_status()
    print(
        f"  PolyHaven: {'✅ Enabled' if polyhaven_status.get('enabled') else '❌ Disabled'}")

    sketchfab_status = bridge.get_sketchfab_status()
    print(
        f"  Sketchfab: {'✅ Enabled' if sketchfab_status.get('enabled') else '❌ Disabled'}")

    hyper3d_status = bridge.get_hyper3d_status()
    print(
        f"  Hyper3D: {'✅ Enabled' if hyper3d_status.get('enabled') else '❌ Disabled'}")


# =========================================================================
# Geometry Node Development Convenience Functions (Added 2025-12-07)
# =========================================================================

def inspect_node(node_type: str) -> Dict[str, Any]:
    """
    Inspect a geometry node type's sockets before using it.
    
    Example:
        info = inspect_node("GeometryNodeDistributePointsOnFaces")
        print(info['inputs'])  # Shows all input sockets with names and types
    """
    bridge = BlenderCopilotBridge()
    return bridge.inspect_node_sockets(node_type)


def create_blob_system(name: str = "BlobSystem", size: float = 2.0) -> Dict[str, Any]:
    """
    Create a ready-to-use organic blob/clod system with a single Breakdown slider.
    
    Example:
        result = create_blob_system("SoilClods", size=2.0)
        # Now apply the node group to an object
    """
    bridge = BlenderCopilotBridge()
    return bridge.create_volume_blob_system(name, container_size=size)


def test_bounds(object_name: str, socket_id: str = "Socket_2") -> Dict[str, Any]:
    """
    Test how an object's bounds change across a parameter's range.
    
    Example:
        results = test_bounds("MyClodObject", "Socket_2")
        print(results['variance'])  # Shows how much bounds vary
    """
    bridge = BlenderCopilotBridge()
    return bridge.test_parameter_bounds(object_name, socket_id)


def mothball(object_names: List[str]) -> Dict[str, Any]:
    """
    Hide and disable objects to shelve them without deleting.
    
    Example:
        mothball(["Test1", "Test3", "Test4"])  # Keep Test2 active
    """
    bridge = BlenderCopilotBridge()
    return bridge.mothball_scene_objects(object_names, hide=True)


def unmothball(object_names: List[str]) -> Dict[str, Any]:
    """
    Restore previously mothballed objects.
    
    Example:
        unmothball(["Test1"])  # Bring Test1 back
    """
    bridge = BlenderCopilotBridge()
    return bridge.mothball_scene_objects(object_names, hide=False)


if __name__ == "__main__":
    demo_copilot_integration()
