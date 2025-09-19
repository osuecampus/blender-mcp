#!/usr/bin/env python3
"""
Simple test of the enhanced interface without interactive loop
"""

from enhanced_nl_interface import EnhancedBlenderNL


def test_commands():
    """Test various commands without interactive input"""

    print("🧪 Testing Enhanced Natural Language Interface")
    print("=" * 50)

    nl_interface = EnhancedBlenderNL()

    test_commands = [
        "show me the scene",
        "what integrations are available?",
        "create a cube at position 1,0,0",
        "what's the status?"
    ]

    for cmd in test_commands:
        print(f"\n🗣️  Command: '{cmd}'")
        print("📋 Result:")
        try:
            result = nl_interface.process_request(cmd)
            print(result)
        except Exception as e:
            print(f"❌ Error: {e}")
        print("-" * 40)


if __name__ == "__main__":
    test_commands()
