#!/usr/bin/env python3
"""
Quick test of the natural language Blender interface
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from examples.natural_language_blender import BlenderCommandGenerator


def quick_test():
    generator = BlenderCommandGenerator()

    # Test a simple command
    test_description = "create a red cube at position 1,0,0"

    print(f"🧪 Testing: '{test_description}'")

    try:
        result = generator.execute_command(test_description)
        if result["success"]:
            print("✅ Successfully connected to Blender and executed command!")
            print(f"📊 Blender response: {result['blender_response']}")
        else:
            print(f"❌ Error: {result['error']}")
            print("Make sure Blender is running with the MCP addon enabled")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("Make sure Blender is running with the MCP server addon")


if __name__ == "__main__":
    quick_test()
