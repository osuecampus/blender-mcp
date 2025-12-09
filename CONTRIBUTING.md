# Contributing to BlenderMCP

Thank you for contributing to our Blender development environment!

## Our Development Philosophy

This repo follows a **cyclical tool and lesson development** approach:

```
Problem → Tool → Test → Document → Share → Repeat
```

Every time we encounter friction in Blender workflows, we:

1. Build a tool to solve it
2. Document what we learned
3. Share with the team

## How to Contribute

### 1. Adding a New Tool

**Before creating a tool**, check if something similar exists:

- `texture_baker_v2.py` - Material baking
- `geonode_helper.py` - Geometry nodes
- `scene_analyzer.py` - Scene documentation
- `copilot_bridge.py` - Blender communication

**To add a new tool:**

1. Create `your_tool.py` in the repo root
2. Use `copilot_bridge.py` for Blender communication
3. Include a docstring with usage examples
4. Add CLI support if appropriate
5. Update `copilot-instructions.md` with documentation

**Template:**

```python
#!/usr/bin/env python3
"""
Tool Name - What it does

Usage:
    from tools.your_tool import YourClass
    tool = YourClass()
    tool.do_thing()

CLI:
    python tools/your_tool.py --help
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.copilot_bridge import BlenderCopilotBridge

class YourClass:
    def __init__(self):
        self.bridge = BlenderCopilotBridge()
    
    def do_thing(self):
        code = '''
import bpy
# Blender operations
'''
        return self.bridge.execute_blender_code(code)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Tool description")
    # Add arguments
    args = parser.parse_args()
    # Run tool
```

### 2. Documenting Lessons Learned

**Location:** `docs/BLENDER_API_LESSONS.md`

**Format:**

```markdown
## Session: YYYY-MM-DD - Topic

### Lesson: Brief Title

**What happened:** Describe the problem you encountered

**Cause:** Why it happened (root cause)

**The fix:**
\`\`\`python
# Working code example
\`\`\`

**Prevention:** How to avoid this in the future
```

**Good lesson topics:**

- API gotchas (socket names changed in Blender 5.0)
- Performance issues (why X is slow)
- Workarounds for Blender limitations
- Successful patterns worth reusing

### 3. Updating AI Instructions

**Location:** `copilot-instructions.md`

This file is automatically loaded by GitHub Copilot. Update it when:

- Adding a new tool (document usage)
- Discovering important patterns
- Finding things the AI should/shouldn't do

**Structure:**

- Keep it concise - AI has context limits
- Use code examples
- Include "when to use" / "when NOT to use"

### 4. Improving Setup/Documentation

**Files:**

- `TEAM_SETUP.md` - Getting started guide
- `setup-team.sh` - Automated setup script
- `README.md` - Public-facing documentation

## Code Standards

### Python Style

- Use type hints for function parameters
- Docstrings for all public functions
- Follow PEP 8 (mostly)

### Blender Code

- Always verify object/material names exist
- Clean up temporary nodes after operations
- Restore original state when modifying settings

### Commits

```
feat: Add new capability
fix: Correct a bug
docs: Update documentation
refactor: Code restructure without behavior change
test: Add or update tests
```

## Pull Request Process

1. Create a feature branch from `local-copilot-development`
2. Make your changes
3. Test with actual Blender workflows
4. Update documentation
5. Submit PR with clear description

## Testing Your Changes

### Manual Testing

1. Start Blender and connect the addon
2. Run `uvx blender-mcp` to start MCP server
3. Test your tool via VS Code Copilot or Python directly

### Quick Connection Test

```bash
python check_blender.py
```

### Test Script Template

```python
#!/usr/bin/env python3
"""Test script for your_tool"""

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from your_tool import YourClass

def test_basic():
    tool = YourClass()
    result = tool.do_thing()
    assert result is not None
    print("✓ Basic test passed")

if __name__ == "__main__":
    test_basic()
```

## Questions?

- Check existing documentation first
- Ask in team chat
- Open an issue for larger discussions
