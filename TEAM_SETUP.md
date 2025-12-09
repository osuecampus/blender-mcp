# BlenderMCP Team Development Environment

A shared development environment for Blender automation using the Model Context Protocol (MCP). This repo enables AI-assisted 3D modeling with GitHub Copilot/Claude integration.

## Quick Start for Team Members

### Prerequisites

- **Blender 3.0+** (or 5.0+ recommended)
- **Python 3.10+**
- **VS Code** with GitHub Copilot
- **uv** package manager

### 1. Install uv (if not already installed)

```bash
# macOS
brew install uv

# Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Clone and Setup

```bash
git clone https://github.com/nickHarperOSU/blender-mcp.git
cd blender-mcp

# Create virtual environment
uv venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
uv pip install -e .
```

### 3. Install Blender Addon

1. Open Blender
2. Go to **Edit > Preferences > Add-ons**
3. Click **Install...** and select `addon.py` from this repo
4. Enable the addon by checking **"Interface: Blender MCP"**

### 4. Connect Blender to MCP

1. In Blender, press `N` to open the sidebar
2. Find the **"BlenderMCP"** tab
3. Click **"Connect to Claude"**
4. The addon listens on `localhost:9876`

### 5. Start Working in VS Code

Open the repo in VS Code. The MCP server is already configured in `.vscode/mcp.json`.

**Run the build task** (Ctrl+Shift+B) to start the MCP server, or:

```bash
uvx blender-mcp
```

## Development Workflow

### Tool Development Cycle

```
1. Encounter a repetitive task in Blender
2. Build a Python tool to automate it
3. Test via copilot_bridge.py
4. Document lessons learned
5. Update copilot-instructions.md
6. Commit and share with team
```

### Key Files

| File | Purpose |
|------|---------|
| `copilot_bridge.py` | Python API to communicate with Blender |
| `copilot-instructions.md` | AI instructions for Copilot (auto-loaded) |
| `docs/BLENDER_API_LESSONS.md` | Lessons learned, patterns, gotchas |
| `addon.py` | Blender addon (socket server) |

### Available Tools

| Tool | Usage |
|------|-------|
| `tools/texture_baker_v2.py` | Bake procedural materials to textures |
| `tools/geonode_helper.py` | Analyze and organize geometry nodes |
| `tools/scene_analyzer.py` | Document scene structure |
| `tools/node_addon_helper.py` | Leverage Node Wrangler and other addons |

## Using the Bridge

```python
from tools.copilot_bridge import BlenderCopilotBridge

bridge = BlenderCopilotBridge()

# Execute any Blender Python code
result = bridge.execute_blender_code("""
import bpy
print(f"Scene has {len(bpy.data.objects)} objects")
""")
print(result)

# Take a viewport screenshot
screenshot = bridge.capture_viewport_screenshot()
```

## Adding to Lessons Learned

When you discover something important about Blender's API:

1. Open `docs/BLENDER_API_LESSONS.md`
2. Add a new section with:
   - **What happened** (the problem)
   - **Cause** (why it happened)
   - **The fix** (code example)
   - **Prevention** (how to avoid in future)

Example:

```markdown
### Lesson: Object Must Be Render-Enabled for Baking

**What happened:** Bake operation failed with "Object not enabled for rendering"

**Cause:** Object had `hide_render = True`

**The fix:**
\`\`\`python
obj.hide_render = False
\`\`\`

**Prevention:** Always check render visibility before baking operations.
```

## Creating New Tools

1. Create a new `.py` file in the repo root
2. Use this template:

```python
#!/usr/bin/env python3
"""
Tool Name - Brief description

Usage:
    from tools.tool_name import main_function
    result = main_function(args)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.copilot_bridge import BlenderCopilotBridge

def main_function():
    bridge = BlenderCopilotBridge()
    
    code = """
import bpy
# Your Blender code here
"""
    
    return bridge.execute_blender_code(code)

if __name__ == "__main__":
    main_function()
```

3. Add documentation to `copilot-instructions.md`
4. Test thoroughly before committing

## VS Code Tasks

| Task | Shortcut | Description |
|------|----------|-------------|
| Full Setup | Ctrl+Shift+B | Open Blender + Start MCP |
| Start MCP Server | - | Run `uvx blender-mcp` |
| Check Connection | - | Test Blender socket |

## Troubleshooting

### "Connection refused" error

- Ensure Blender is open

- Click "Connect to Claude" in Blender's sidebar
- Check that port 9876 is not in use

### "Material not found" when baking

- Run `list_all_materials()` first
- Use EXACT material name (case-sensitive)

- Verify object has UV coordinates

### Geometry nodes not updating

- Check if using shader nodes (may freeze after first evaluation)
- Consider using drivers instead
- Test incrementally after each change

## Team Conventions

### Branch Strategy

- `main` - Stable, tested tools

- `local-copilot-development` - Active development
- Feature branches for major new tools

### Commit Messages

```

feat: Add texture_baker_v2 with bake-and-replace workflow
fix: Correct normal map node connection in bake replacement
docs: Add baking lessons to BLENDER_API_LESSONS.md
```

### Code Style

- Use docstrings for all public functions
- Include usage examples in module docstrings
- Type hints for function parameters

## Resources

- [Blender Python API](https://docs.blender.org/api/current/)
- [MCP Specification](https://modelcontextprotocol.io/)
- [Project Discord](https://discord.gg/z5apgR8TFU)
