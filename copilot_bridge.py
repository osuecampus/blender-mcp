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
                s.connect((self.host, self.port))
                s.sendall(json.dumps(command).encode('utf-8'))
                response = s.recv(8192)  # Larger buffer for complex responses
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


if __name__ == "__main__":
    demo_copilot_integration()
