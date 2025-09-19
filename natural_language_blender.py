#!/usr/bin/env python3
"""
Natural Language to Blender Python API Converter
Converts natural language descriptions into Blender Python commands
"""

import socket
import json
import re
from typing import Dict, List, Tuple, Any


class BlenderCommandGenerator:
    """Generates Blender Python commands from natural language descriptions"""

    def __init__(self, host='127.0.0.1', port=9876):
        self.host = host
        self.port = port

    def parse_natural_language(self, description: str) -> str:
        """
        Convert natural language description to Blender Python code

        Examples:
        - "create a red cube" -> creates cube with red material
        - "add a sphere at position 2,0,0" -> creates sphere at specified location
        - "delete all cubes" -> deletes all cube objects
        - "make the cube bigger" -> scales the active cube
        """

        description = description.lower().strip()
        commands = []

        # Initialize Blender context
        commands.append("import bpy")

        # CREATE/ADD OBJECTS
        if "create" in description or "add" in description:

            # CUBE
            if "cube" in description:
                location = self._extract_position(description)
                size = self._extract_size(description)

                cmd = f"bpy.ops.mesh.primitive_cube_add("
                if location:
                    cmd += f"location={location}, "
                if size:
                    cmd += f"size={size}, "
                cmd += "enter_editmode=False, align='WORLD')"
                commands.append(cmd)

                # Add material if color specified
                color = self._extract_color(description)
                if color:
                    commands.extend(self._create_material_commands(color))

            # SPHERE
            elif "sphere" in description or "ball" in description:
                location = self._extract_position(description)
                radius = self._extract_radius(description)

                cmd = f"bpy.ops.mesh.primitive_uv_sphere_add("
                if location:
                    cmd += f"location={location}, "
                if radius:
                    cmd += f"radius={radius}, "
                cmd += "enter_editmode=False, align='WORLD')"
                commands.append(cmd)

                color = self._extract_color(description)
                if color:
                    commands.extend(self._create_material_commands(color))

            # CYLINDER
            elif "cylinder" in description:
                location = self._extract_position(description)
                radius = self._extract_radius(description)
                depth = self._extract_depth(description)

                cmd = f"bpy.ops.mesh.primitive_cylinder_add("
                if location:
                    cmd += f"location={location}, "
                if radius:
                    cmd += f"radius={radius}, "
                if depth:
                    cmd += f"depth={depth}, "
                cmd += "enter_editmode=False, align='WORLD')"
                commands.append(cmd)

                color = self._extract_color(description)
                if color:
                    commands.extend(self._create_material_commands(color))

            # PLANE
            elif "plane" in description or "floor" in description:
                location = self._extract_position(description)
                size = self._extract_size(description)

                cmd = f"bpy.ops.mesh.primitive_plane_add("
                if location:
                    cmd += f"location={location}, "
                if size:
                    cmd += f"size={size}, "
                cmd += "enter_editmode=False, align='WORLD')"
                commands.append(cmd)

                color = self._extract_color(description)
                if color:
                    commands.extend(self._create_material_commands(color))

        # DELETE OBJECTS
        elif "delete" in description or "remove" in description:
            if "all" in description:
                if "cube" in description:
                    commands.append(
                        "bpy.ops.object.select_all(action='DESELECT')")
                    commands.append("for obj in bpy.context.scene.objects:")
                    commands.append(
                        "    if obj.type == 'MESH' and 'Cube' in obj.name:")
                    commands.append("        obj.select_set(True)")
                    commands.append("bpy.ops.object.delete()")
                elif "sphere" in description:
                    commands.append(
                        "bpy.ops.object.select_all(action='DESELECT')")
                    commands.append("for obj in bpy.context.scene.objects:")
                    commands.append(
                        "    if obj.type == 'MESH' and 'Sphere' in obj.name:")
                    commands.append("        obj.select_set(True)")
                    commands.append("bpy.ops.object.delete()")
                else:
                    commands.append(
                        "bpy.ops.object.select_all(action='SELECT')")
                    commands.append("bpy.ops.object.delete()")
            else:
                commands.append("bpy.ops.object.delete()")

        # SCALE/RESIZE
        elif "bigger" in description or "larger" in description or "scale up" in description:
            scale_factor = self._extract_scale_factor(description) or 1.5
            commands.append(
                f"bpy.context.object.scale = ({scale_factor}, {scale_factor}, {scale_factor})")

        elif "smaller" in description or "scale down" in description:
            scale_factor = self._extract_scale_factor(description) or 0.7
            commands.append(
                f"bpy.context.object.scale = ({scale_factor}, {scale_factor}, {scale_factor})")

        # MOVE/TRANSLATE
        elif "move" in description:
            location = self._extract_position(description)
            if location:
                commands.append(f"bpy.context.object.location = {location}")

        # ROTATE
        elif "rotate" in description:
            rotation = self._extract_rotation(description)
            if rotation:
                commands.append(
                    f"bpy.context.object.rotation_euler = {rotation}")

        # MATERIAL/COLOR
        elif "color" in description or "material" in description:
            color = self._extract_color(description)
            if color:
                commands.extend(self._create_material_commands(color))

        # Clear scene
        elif "clear" in description or "reset" in description:
            commands.append("bpy.ops.object.select_all(action='SELECT')")
            commands.append("bpy.ops.object.delete()")

        # Join commands with newlines
        return "\n".join(commands)

    def _extract_position(self, text: str) -> Tuple[float, float, float] | None:
        """Extract position coordinates from text"""
        # Look for patterns like "at (1,2,3)" or "position 1,2,3"
        patterns = [
            r"(?:at|position)\s*\(?(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\)?",
            r"(?:at|position)\s*\(?(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\)?",
            r"\((-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\)"
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return (float(match.group(1)), float(match.group(2)), float(match.group(3)))
        return None

    def _extract_size(self, text: str) -> float | None:
        """Extract size from text"""
        patterns = [
            r"size\s*(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)\s*units?\s*big",
            r"(\d+(?:\.\d+)?)\s*units?\s*wide"
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return float(match.group(1))
        return None

    def _extract_radius(self, text: str) -> float | None:
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

    def _extract_depth(self, text: str) -> float | None:
        """Extract depth/height from text"""
        patterns = [
            r"depth\s*(\d+(?:\.\d+)?)",
            r"height\s*(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)\s*(?:tall|high|deep)"
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return float(match.group(1))
        return None

    def _extract_scale_factor(self, text: str) -> float | None:
        """Extract scale factor from text"""
        patterns = [
            r"(\d+(?:\.\d+)?)\s*times",
            r"scale\s*(?:by\s*)?(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)\s*x"
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return float(match.group(1))
        return None

    def _extract_rotation(self, text: str) -> Tuple[float, float, float] | None:
        """Extract rotation from text"""
        # Convert degrees to radians for Blender
        import math

        # Look for specific rotations
        if "90 degrees" in text or "90°" in text:
            if "x" in text:
                return (math.radians(90), 0, 0)
            elif "y" in text:
                return (0, math.radians(90), 0)
            elif "z" in text:
                return (0, 0, math.radians(90))

        # Look for general rotation pattern
        pattern = r"rotate\s*(?:by\s*)?(\d+(?:\.\d+)?)\s*degrees?"
        match = re.search(pattern, text)
        if match:
            angle = math.radians(float(match.group(1)))
            return (0, 0, angle)  # Default to Z rotation

        return None

    def _extract_color(self, text: str) -> Tuple[float, float, float, float] | None:
        """Extract color from text and return RGBA values"""
        color_map = {
            "red": (1.0, 0.0, 0.0, 1.0),
            "green": (0.0, 1.0, 0.0, 1.0),
            "blue": (0.0, 0.0, 1.0, 1.0),
            "yellow": (1.0, 1.0, 0.0, 1.0),
            "orange": (1.0, 0.5, 0.0, 1.0),
            "purple": (1.0, 0.0, 1.0, 1.0),
            "cyan": (0.0, 1.0, 1.0, 1.0),
            "white": (1.0, 1.0, 1.0, 1.0),
            "black": (0.0, 0.0, 0.0, 1.0),
            "gray": (0.5, 0.5, 0.5, 1.0),
            "grey": (0.5, 0.5, 0.5, 1.0),
            "pink": (1.0, 0.5, 0.8, 1.0),
            "brown": (0.6, 0.3, 0.1, 1.0)
        }

        for color_name, rgba in color_map.items():
            if color_name in text:
                return rgba

        return None

    def _create_material_commands(self, color: Tuple[float, float, float, float]) -> List[str]:
        """Create commands to apply a material with the specified color"""
        commands = [
            "# Create and assign material",
            "mat = bpy.data.materials.new(name='Generated_Material')",
            "mat.use_nodes = True",
            "bsdf = mat.node_tree.nodes['Principled BSDF']",
            f"bsdf.inputs['Base Color'].default_value = {color}",
            "bpy.context.object.data.materials.append(mat)"
        ]
        return commands

    def execute_command(self, description: str) -> Dict[str, Any]:
        """Execute a natural language command in Blender"""
        try:
            # Generate Blender Python code
            blender_code = self.parse_natural_language(description)

            print(f"Generated Blender code for '{description}':")
            print("-" * 50)
            print(blender_code)
            print("-" * 50)

            # Send to Blender via MCP
            command = {
                "type": "execute_code",
                "params": {
                    "code": blender_code
                }
            }

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                s.sendall(json.dumps(command).encode('utf-8'))
                response = s.recv(4096)
                result = json.loads(response.decode('utf-8'))

                return {
                    "success": True,
                    "description": description,
                    "generated_code": blender_code,
                    "blender_response": result
                }

        except Exception as e:
            return {
                "success": False,
                "description": description,
                "error": str(e)
            }


def main():
    """Interactive natural language Blender interface"""
    generator = BlenderCommandGenerator()

    print("🎨 Natural Language Blender Interface")
    print("Type your commands in natural language!")
    print("Examples:")
    print("  - 'create a red cube at position 2,0,0'")
    print("  - 'add a blue sphere'")
    print("  - 'make it bigger'")
    print("  - 'delete all cubes'")
    print("  - 'clear the scene'")
    print("\nType 'quit' to exit\n")

    while True:
        try:
            description = input("🗣️  Describe what you want: ").strip()

            if description.lower() in ['quit', 'exit', 'q']:
                print("Goodbye! 👋")
                break

            if not description:
                continue

            result = generator.execute_command(description)

            if result["success"]:
                print("✅ Command executed successfully!")
                if "result" in result["blender_response"]:
                    print(
                        f"📝 Blender says: {result['blender_response']['result']}")
            else:
                print(f"❌ Error: {result['error']}")

            print()

        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
