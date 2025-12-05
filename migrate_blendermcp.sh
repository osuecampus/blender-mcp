#!/bin/bash

# BlenderMCP Migration Script
# Usage: ./migrate_blendermcp.sh /path/to/new-repository

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if target directory is provided
if [ -z "$1" ]; then
    print_error "Usage: $0 /path/to/new-repository"
    exit 1
fi

TARGET_DIR="$1"
SOURCE_DIR="$(pwd)"

print_status "Starting BlenderMCP migration..."
print_status "Source: $SOURCE_DIR"
print_status "Target: $TARGET_DIR"

# Create target directory if it doesn't exist
if [ ! -d "$TARGET_DIR" ]; then
    print_status "Creating target directory: $TARGET_DIR"
    mkdir -p "$TARGET_DIR"
fi

# Essential files to copy
CORE_FILES=(
    "src/"
    "pyproject.toml"
    "main.py"
    "addon.py"
    "copilot_bridge.py"
    "README.md"
    "uv.lock"
    "HANDOFF_GUIDE.md"
)

# Optional files
OPTIONAL_FILES=(
    "test_connection.py"
    "test_mcp_connection.py"
    "test_enhanced_interface.py"
    "demo_nl_commands.py"
    "enhanced_nl_interface.py"
    "natural_language_blender.py"
    "setup_guide.sh"
    "COPILOT_INTEGRATION.md"
    "copilot-instructions.md"
    "assets/"
)

# Copy core files
print_status "Copying core BlenderMCP files..."
for file in "${CORE_FILES[@]}"; do
    if [ -e "$SOURCE_DIR/$file" ]; then
        print_status "  Copying $file"
        cp -r "$SOURCE_DIR/$file" "$TARGET_DIR/"
    else
        print_warning "  Core file $file not found - skipping"
    fi
done

# Copy optional files
print_status "Copying optional files..."
for file in "${OPTIONAL_FILES[@]}"; do
    if [ -e "$SOURCE_DIR/$file" ]; then
        print_status "  Copying $file"
        cp -r "$SOURCE_DIR/$file" "$TARGET_DIR/"
    else
        print_status "  Optional file $file not found - skipping"
    fi
done

# Change to target directory
cd "$TARGET_DIR"

# Check for UV
if ! command -v uv &> /dev/null; then
    print_warning "UV package manager not found. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# Install dependencies
print_status "Installing dependencies with UV..."
if [ -f "pyproject.toml" ]; then
    uv sync
    print_status "Dependencies installed successfully"
else
    print_error "pyproject.toml not found - cannot install dependencies"
fi

# Test MCP server (don't wait for it to fully start)
print_status "Testing MCP server startup..."
if command -v uv &> /dev/null && [ -f "main.py" ]; then
    timeout 5 uv run python main.py &
    SERVER_PID=$!
    sleep 2
    
    if kill -0 $SERVER_PID 2>/dev/null; then
        print_status "MCP server started successfully (PID: $SERVER_PID)"
        kill $SERVER_PID 2>/dev/null || true
    else
        print_warning "MCP server may have issues starting - check manually"
    fi
else
    print_warning "Cannot test server - missing UV or main.py"
fi

# Create a quick verification script
cat > verify_setup.py << 'EOF'
#!/usr/bin/env python3
"""
Quick verification script for BlenderMCP setup
"""
import sys
import socket
import subprocess
from pathlib import Path

def check_files():
    """Check if essential files exist"""
    essential_files = [
        'main.py',
        'addon.py', 
        'copilot_bridge.py',
        'src/blender_mcp/__init__.py',
        'src/blender_mcp/server.py',
        'pyproject.toml'
    ]
    
    print("🔍 Checking essential files...")
    missing_files = []
    
    for file_path in essential_files:
        if Path(file_path).exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path}")
            missing_files.append(file_path)
    
    return len(missing_files) == 0

def check_python_imports():
    """Test if core modules can be imported"""
    print("\n🐍 Testing Python imports...")
    
    try:
        from copilot_bridge import BlenderCopilotBridge
        print("  ✅ copilot_bridge")
    except ImportError as e:
        print(f"  ❌ copilot_bridge: {e}")
        return False
    
    try:
        import src.blender_mcp.server as server
        print("  ✅ blender_mcp.server")
    except ImportError as e:
        print(f"  ❌ blender_mcp.server: {e}")
        return False
    
    return True

def check_port_availability():
    """Check if port 9876 is available"""
    print("\n🔌 Checking port 9876 availability...")
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 9876))
            print("  ✅ Port 9876 available")
            return True
    except OSError:
        print("  ❌ Port 9876 in use")
        return False

def main():
    print("🚀 BlenderMCP Setup Verification")
    print("=" * 40)
    
    checks = [
        ("File Structure", check_files),
        ("Python Imports", check_python_imports), 
        ("Port Availability", check_port_availability)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"  ❌ {name} failed: {e}")
            results.append((name, False))
    
    print("\n📊 Summary:")
    print("-" * 20)
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All checks passed! BlenderMCP is ready to use.")
        print("\nNext steps:")
        print("  1. Start MCP server: uv run python main.py")
        print("  2. Install addon.py in Blender")
        print("  3. Test with: python -c 'from copilot_bridge import BlenderCopilotBridge; bridge = BlenderCopilotBridge(); print(bridge.get_scene_info())'")
    else:
        print("\n⚠️  Some checks failed. Review the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

chmod +x verify_setup.py

print_status "Migration completed successfully!"
print_status ""
print_status "📋 Next Steps:"
print_status "  1. cd $TARGET_DIR"
print_status "  2. python verify_setup.py"
print_status "  3. uv run python main.py (start MCP server)"
print_status "  4. Install addon.py in Blender"
print_status "  5. Read HANDOFF_GUIDE.md for complete setup"
print_status ""
print_status "🔍 Quick verification:"
print_status "  python verify_setup.py"