#!/usr/bin/env python3
"""
Enhanced Natural Language Blender Interface
Combines simple regex parsing with sophisticated MCP tools
Perfect for GitHub Copilot integration
"""

import re
import json
from typing import Dict, List, Tuple, Any, Optional
from copilot_bridge import BlenderCopilotBridge


class EnhancedBlenderNL:
    """Enhanced natural language interface using MCP tools"""

    def __init__(self):
        self.bridge = BlenderCopilotBridge()

    def process_request(self, description: str) -> str:
        """Process a natural language request and execute appropriate actions"""
        description = description.lower().strip()

        # Check integrations first
        if "status" in description or "what" in description and "available" in description:
            return self._get_status_info()

        # Scene information
        if any(word in description for word in ["scene", "what's in", "current", "show me"]):
            return self._get_scene_info()

        # Screenshot
        if any(word in description for word in ["screenshot", "capture", "image", "picture"]):
            return self._capture_screenshot()

        # Asset downloading (PolyHaven)
        if "download" in description and any(word in description for word in ["texture", "material", "hdri", "model"]):
            return self._handle_asset_download(description)

        # 3D model generation (Hyper3D)
        if any(phrase in description for phrase in ["generate", "create ai", "ai model", "hyper3d"]):
            return self._handle_3d_generation(description)

        # Object creation (enhanced with MCP)
        if any(word in description for word in ["create", "add", "make"]):
            return self._create_objects(description)

        # Object manipulation
        if any(word in description for word in ["move", "scale", "rotate", "transform"]):
            return self._manipulate_objects(description)

        # Material application
        if any(word in description for word in ["material", "texture", "color", "apply"]):
            return self._handle_materials(description)

        # Clear/delete
        if any(word in description for word in ["clear", "delete", "remove", "reset"]):
            return self._handle_deletion(description)

        # Fallback to direct code execution
        return self._generate_and_execute_code(description)

    def _get_status_info(self) -> str:
        """Get status of all integrations"""
        result = "🔌 BlenderMCP Integration Status:\n\n"

        # Check PolyHaven
        polyhaven = self.bridge.get_polyhaven_status()
        status = "✅ Enabled" if polyhaven.get('enabled') else "❌ Disabled"
        result += f"PolyHaven (textures, HDRIs, models): {status}\n"

        # Check Sketchfab
        sketchfab = self.bridge.get_sketchfab_status()
        status = "✅ Enabled" if sketchfab.get('enabled') else "❌ Disabled"
        result += f"Sketchfab (3D models): {status}\n"

        # Check Hyper3D
        hyper3d = self.bridge.get_hyper3d_status()
        status = "✅ Enabled" if hyper3d.get('enabled') else "❌ Disabled"
        result += f"Hyper3D (AI model generation): {status}\n"

        result += "\n💡 To enable integrations, check the BlenderMCP panel in Blender's sidebar"
        return result

    def _get_scene_info(self) -> str:
        """Get comprehensive scene information"""
        scene_info = self.bridge.get_scene_info()

        result = f"📋 Scene: {scene_info.get('name', 'Unknown')}\n"
        result += f"📊 Total objects: {scene_info.get('object_count', 0)}\n\n"

        objects = scene_info.get('objects', [])
        if objects:
            result += "🎯 Objects in scene:\n"
            for obj in objects:
                name = obj.get('name', 'Unknown')
                obj_type = obj.get('type', 'Unknown')
                location = obj.get('location', [0, 0, 0])
                result += f"  • {name} ({obj_type}) at ({location[0]:.1f}, {location[1]:.1f}, {location[2]:.1f})\n"
        else:
            result += "🔍 No objects in scene"

        return result

    def _capture_screenshot(self) -> str:
        """Capture a viewport screenshot"""
        try:
            filepath = self.bridge.capture_viewport_screenshot()
            return f"📸 Screenshot saved to: {filepath}"
        except Exception as e:
            return f"❌ Failed to capture screenshot: {str(e)}"

    def _handle_asset_download(self, description: str) -> str:
        """Handle asset downloading from PolyHaven/Sketchfab"""
        # Check if PolyHaven is enabled
        polyhaven_status = self.bridge.get_polyhaven_status()
        sketchfab_status = self.bridge.get_sketchfab_status()

        if not polyhaven_status.get('enabled') and not sketchfab_status.get('enabled'):
            return "❌ No asset integrations are enabled. Please enable PolyHaven or Sketchfab in Blender."

        # Extract asset type and search terms
        if "texture" in description or "material" in description:
            return self._search_and_download_texture(description)
        elif "hdri" in description or "environment" in description:
            return self._search_and_download_hdri(description)
        elif "model" in description:
            return self._search_and_download_model(description)
        else:
            return "🤔 Please specify what type of asset you want: texture, HDRI, or model"

    def _search_and_download_texture(self, description: str) -> str:
        """Search and download textures"""
        # Extract search terms (simple approach)
        search_terms = self._extract_search_terms(description)

        try:
            # Search PolyHaven for textures
            assets = self.bridge.search_polyhaven_assets(asset_type="textures")

            # Find matching assets
            matches = []
            for asset_id, asset_data in assets.items():
                asset_name = asset_data.get('name', '').lower()
                if any(term in asset_name for term in search_terms):
                    matches.append(
                        (asset_id, asset_data.get('name', asset_id)))

            if not matches:
                return f"❌ No textures found matching: {', '.join(search_terms)}"

            # Download the first match
            asset_id, asset_name = matches[0]
            self.bridge.download_polyhaven_asset(asset_id, "textures")

            result = f"✅ Downloaded texture: {asset_name}\n"
            if len(matches) > 1:
                result += f"💡 Found {len(matches)} matches, downloaded the first one"

            return result

        except Exception as e:
            return f"❌ Error downloading texture: {str(e)}"

    def _search_and_download_hdri(self, description: str) -> str:
        """Search and download HDRIs"""
        search_terms = self._extract_search_terms(description)

        try:
            assets = self.bridge.search_polyhaven_assets(asset_type="hdris")

            matches = []
            for asset_id, asset_data in assets.items():
                asset_name = asset_data.get('name', '').lower()
                if any(term in asset_name for term in search_terms):
                    matches.append(
                        (asset_id, asset_data.get('name', asset_id)))

            if not matches:
                return f"❌ No HDRIs found matching: {', '.join(search_terms)}"

            asset_id, asset_name = matches[0]
            self.bridge.download_polyhaven_asset(asset_id, "hdris")

            return f"✅ Downloaded and applied HDRI: {asset_name}\n🌍 World environment updated"

        except Exception as e:
            return f"❌ Error downloading HDRI: {str(e)}"

    def _search_and_download_model(self, description: str) -> str:
        """Search and download 3D models"""
        search_terms = self._extract_search_terms(description)

        # Try Sketchfab first if enabled
        sketchfab_status = self.bridge.get_sketchfab_status()
        if sketchfab_status.get('enabled'):
            try:
                query = " ".join(search_terms)
                models = self.bridge.search_sketchfab_models(query, count=5)

                if models:
                    # Download the first model
                    model = models[0]
                    uid = model.get('uid')
                    name = model.get('name', 'Unknown')

                    result = self.bridge.download_sketchfab_model(uid)
                    return f"✅ Downloaded model from Sketchfab: {name}\n{result}"

            except Exception as e:
                pass  # Fall back to PolyHaven

        # Try PolyHaven
        polyhaven_status = self.bridge.get_polyhaven_status()
        if polyhaven_status.get('enabled'):
            try:
                assets = self.bridge.search_polyhaven_assets(
                    asset_type="models")

                matches = []
                for asset_id, asset_data in assets.items():
                    asset_name = asset_data.get('name', '').lower()
                    if any(term in asset_name for term in search_terms):
                        matches.append(
                            (asset_id, asset_data.get('name', asset_id)))

                if matches:
                    asset_id, asset_name = matches[0]
                    self.bridge.download_polyhaven_asset(asset_id, "models")
                    return f"✅ Downloaded model from PolyHaven: {asset_name}"

            except Exception as e:
                return f"❌ Error downloading model: {str(e)}"

        return f"❌ No models found matching: {', '.join(search_terms)}"

    def _handle_3d_generation(self, description: str) -> str:
        """Handle AI 3D model generation"""
        hyper3d_status = self.bridge.get_hyper3d_status()

        if not hyper3d_status.get('enabled'):
            return "❌ Hyper3D integration is not enabled. Please enable it in Blender."

        # Extract the generation prompt
        prompt = self._extract_generation_prompt(description)

        try:
            # Start generation
            result = self.bridge.generate_3d_model_from_text(prompt)

            if "task_uuid" in result:
                return f"🚀 Started AI model generation: '{prompt}'\n💡 This will take a few minutes. Check status with 'check generation status'"
            else:
                return f"❌ Failed to start generation: {result}"

        except Exception as e:
            return f"❌ Error starting generation: {str(e)}"

    def _create_objects(self, description: str) -> str:
        """Create objects with enhanced capabilities"""
        # Check for specific objects
        if "cube" in description:
            position = self._extract_position(description)
            size = self._extract_size(description) or 2.0

            code = f"import bpy\nbpy.ops.mesh.primitive_cube_add(location={position or (0, 0, 0)}, size={size})"
            self.bridge.execute_blender_code(code)

            return f"✅ Created cube at {position or (0, 0, 0)} with size {size}"

        elif "sphere" in description or "ball" in description:
            position = self._extract_position(description)
            radius = self._extract_radius(description) or 1.0

            code = f"import bpy\nbpy.ops.mesh.primitive_uv_sphere_add(location={position or (0, 0, 0)}, radius={radius})"
            self.bridge.execute_blender_code(code)

            return f"✅ Created sphere at {position or (0, 0, 0)} with radius {radius}"

        else:
            return self._generate_and_execute_code(description)

    def _manipulate_objects(self, description: str) -> str:
        """Handle object transformations"""
        return self._generate_and_execute_code(description)

    def _handle_materials(self, description: str) -> str:
        """Handle material and texture application"""
        # Check if trying to apply a specific texture
        if "apply" in description and any(word in description for word in ["texture", "material"]):
            # Extract object and texture names
            words = description.split()
            # This is a simplified approach - in practice you'd want more sophisticated parsing
            return "💡 To apply textures, first download them, then specify: 'apply [texture_name] to [object_name]'"

        return self._generate_and_execute_code(description)

    def _handle_deletion(self, description: str) -> str:
        """Handle object deletion"""
        if "all" in description or "everything" in description or "scene" in description:
            code = "import bpy\nbpy.ops.object.select_all(action='SELECT')\nbpy.ops.object.delete()"
            self.bridge.execute_blender_code(code)
            return "✅ Cleared all objects from scene"

        return self._generate_and_execute_code(description)

    def _generate_and_execute_code(self, description: str) -> str:
        """Fallback: generate and execute Blender Python code"""
        # This is where you could integrate with OpenAI API to generate more sophisticated code
        # For now, return a helpful message
        return f"🤖 Complex request detected: '{description}'\n💡 Consider using the execute_blender_code() function directly for custom operations"

    # Helper methods
    def _extract_search_terms(self, description: str) -> List[str]:
        """Extract search terms from description"""
        # Remove common words
        stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
                      'download', 'get', 'find', 'search', 'texture', 'material', 'hdri', 'model'}

        words = re.findall(r'\b\w+\b', description.lower())
        return [word for word in words if word not in stop_words and len(word) > 2]

    def _extract_generation_prompt(self, description: str) -> str:
        """Extract the generation prompt from description"""
        # Remove trigger words and clean up
        triggers = ['generate', 'create ai', 'ai model', 'hyper3d', 'make']

        for trigger in triggers:
            description = description.replace(trigger, '').strip()

        # Clean up and return
        return description.strip() or "a simple 3D object"

    def _extract_position(self, text: str) -> Optional[Tuple[float, float, float]]:
        """Extract position coordinates from text"""
        patterns = [
            r"(?:at|position)\s*\(?(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\)?",
            r"\((-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\)"
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return (float(match.group(1)), float(match.group(2)), float(match.group(3)))
        return None

    def _extract_size(self, text: str) -> Optional[float]:
        """Extract size from text"""
        patterns = [
            r"size\s*(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)\s*units?\s*big"
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return float(match.group(1))
        return None

    def _extract_radius(self, text: str) -> Optional[float]:
        """Extract radius from text"""
        patterns = [
            r"radius\s*(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)\s*radius"
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return float(match.group(1))
        return None


def main():
    """Interactive enhanced natural language interface"""
    nl_interface = EnhancedBlenderNL()

    print("🎨 Enhanced Blender Natural Language Interface")
    print("Powered by BlenderMCP + GitHub Copilot")
    print("=" * 50)
    print()
    print("💡 Try commands like:")
    print("  - 'show me the scene'")
    print("  - 'create a red cube at position 2,0,0'")
    print("  - 'download a wood texture'")
    print("  - 'what integrations are available?'")
    print("  - 'generate a dragon model'")
    print("  - 'capture a screenshot'")
    print()
    print("Type 'quit' to exit")
    print()

    while True:
        try:
            command = input("🗣️  What would you like to do? ").strip()

            if command.lower() in ['quit', 'exit', 'q']:
                print("Goodbye! 👋")
                break

            if not command:
                continue

            result = nl_interface.process_request(command)
            print(f"\n📋 Result:\n{result}\n")

        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"❌ Error: {e}\n")


if __name__ == "__main__":
    main()
