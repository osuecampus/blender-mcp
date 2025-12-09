#!/usr/bin/env python3
"""
Demo of Natural Language Blender Commands
Run this to test the natural language interface
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from examples.natural_language_blender import BlenderCommandGenerator


def demo_commands():
    """Demonstrate various natural language commands"""

    generator = BlenderCommandGenerator()

    # Test commands
    test_commands = [
        "create a red cube at position 2,0,0",
        "add a blue sphere",
        "create a green cylinder with radius 1.5",
        "add a yellow plane",
        "make it bigger",
        "clear the scene"
    ]

    print("🎨 Demonstrating Natural Language to Blender Commands\n")

    for cmd in test_commands:
        print(f"📝 Command: '{cmd}'")
        print("🐍 Generated Python:")

        # Just generate the code without executing
        blender_code = generator.parse_natural_language(cmd)
        print(blender_code)
        print("-" * 60)
        print()


if __name__ == "__main__":
    demo_commands()
