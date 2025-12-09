# Quick Actions Panel

A customizable Blender sidebar panel that provides quick access to frequently used operators with custom labels.

## Features

- **Customizable Labels**: Rename any action to something meaningful for your workflow
- **Operator Arguments**: Full support for operator parameters (e.g., specific origin types)
- **Category Grouping**: Organize actions into collapsible categories
- **Edit Mode**: Add, remove, and reorder actions directly in Blender
- **Presets**: Quick-add common action sets (Modeling, Object, View, Nodes, Materials)
- **Persistent**: Actions are saved with the .blend file

## Installation

### Method 1: Install as Addon (Recommended)

1. In Blender, go to **Edit > Preferences > Add-ons**
2. Click **Install...**
3. Navigate to `addons/quick_actions_panel.py` and select it
4. Enable the addon by checking the box next to "Quick Actions Panel"

### Method 2: Copy to Blender Scripts Folder

Copy `quick_actions_panel.py` to your Blender scripts folder:
- **Linux**: `~/.config/blender/<version>/scripts/addons/`
- **macOS**: `/Users/<user>/Library/Application Support/Blender/<version>/scripts/addons/`
- **Windows**: `%APPDATA%\Blender Foundation\Blender\<version>\scripts\addons\`

Then enable in Preferences > Add-ons.

### Method 3: Load via BlenderMCP Bridge

```python
from tools import BlenderCopilotBridge

bridge = BlenderCopilotBridge()
bridge.execute_blender_code('''
import bpy
import sys
import importlib.util

addon_path = "/path/to/addons/quick_actions_panel.py"
spec = importlib.util.spec_from_file_location("quick_actions_panel", addon_path)
module = importlib.util.module_from_spec(spec)
sys.modules["quick_actions_panel"] = module
spec.loader.exec_module(module)
module.register()
''')
```

## Usage

1. Open the 3D Viewport sidebar by pressing **N**
2. Click the **Quick Actions** tab
3. Actions are displayed grouped by category - click any button to run the action

### Edit Mode

Toggle **Edit** to customize your panel:

- **Add/Remove Actions**: Use + and - buttons
- **Reorder**: Use ▲ and ▼ arrows
- **Edit Properties**: Select an action to modify:
  - **Label**: Custom display name
  - **Operator**: Blender operator ID (e.g., `object.origin_set`)
  - **Args**: Operator arguments (e.g., `type='ORIGIN_GEOMETRY'`)
  - **Icon**: Blender icon name (e.g., `OBJECT_ORIGIN`)
  - **Category**: Grouping category name

### Adding Custom Actions

To add a custom action:

1. Enable Edit mode
2. Click the **+** button
3. Fill in:
   - **Operator**: The Blender operator ID
   - **Args**: Any arguments the operator needs
   - **Label**: Your custom name
   - **Category**: Group it belongs to

#### Finding Operator IDs

- Hover over any Blender menu item to see its operator ID in the tooltip
- Or enable **Developer Extras** in Preferences > Interface to see Python info

#### Common Argument Formats

```
type='ORIGIN_GEOMETRY'                    # Enum string
location=True, rotation=False             # Boolean flags  
mode='ALL'                                # Mode enum
type='OBJECT', keep_transform=True        # Multiple args
```

## Default Actions

When first loaded via BlenderMCP, these actions are pre-configured:

### Apply
| Action | Operator Args |
|--------|---------------|
| Apply All Transforms | `location=True, rotation=True, scale=True` |
| Apply Location | `location=True` |
| Apply Rotation | `rotation=True` |
| Apply Scale | `scale=True` |
| Apply Rotation & Scale | `rotation=True, scale=True` |
| Apply Visual Transform | - |
| Apply to Deltas (All) | `mode='ALL'` |
| Make Instances Real | - |

### Set Origin
| Action | Operator Args |
|--------|---------------|
| Origin to Geometry | `type='ORIGIN_GEOMETRY', center='MEDIAN'` |
| Origin to Geometry (Bounds) | `type='ORIGIN_GEOMETRY', center='BOUNDS'` |
| Origin to Center of Mass (Surface) | `type='ORIGIN_CENTER_OF_MASS'` |
| Origin to Center of Mass (Volume) | `type='ORIGIN_CENTER_OF_VOLUME'` |
| Origin to 3D Cursor | `type='ORIGIN_CURSOR'` |
| Geometry to Origin | `type='GEOMETRY_ORIGIN'` |

### Relations
| Action | Operator Args |
|--------|---------------|
| Make Local (All) | `type='ALL'` |
| Make Local (Object) | `type='SELECT_OBJECT'` |
| Make Local (Object Data) | `type='SELECT_OBDATA'` |
| Make Local (Data + Materials) | `type='SELECT_OBDATA_MATERIAL'` |
| Make Single User (All) | `type='ALL'` |
| Make Single User (Object) | `type='SELECTED_OBJECTS'` |
| Make Single User (Object + Data) | `object=True, obdata=True` |
| Make Library Override | - |

### Parent
| Action | Operator Args |
|--------|---------------|
| Parent to Object | `type='OBJECT'` |
| Parent (Keep Transform) | `type='OBJECT', keep_transform=True` |
| Parent to Bone | `type='BONE'` |
| Parent to Armature | `type='ARMATURE'` |
| Parent to Vertex | `type='VERTEX'` |
| Parent to 3 Vertices | `type='VERTEX_TRI'` |
| Parent (No Inverse) | - |
| Clear Parent | `type='CLEAR'` |
| Clear Parent (Keep Transform) | `type='CLEAR_KEEP_TRANSFORM'` |

## Blender Icon Reference

Common icons for actions:

| Icon | Name |
|------|------|
| ✓ | `CHECKMARK` |
| 🔗 | `LINKED` / `UNLINKED` |
| 📍 | `OBJECT_ORIGIN` |
| 🎯 | `PIVOT_CURSOR` |
| 📦 | `OBJECT_DATA` |
| ⚙️ | `PREFERENCES` |
| ➕ | `ADD` |
| ➖ | `REMOVE` |

For a full list, search "Blender Icon Viewer" addon or use:
```python
import bpy
icons = bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items.keys()
```

## API Reference

### Properties

- `bpy.context.scene.quick_actions.items` - Collection of QuickActionItem
- `bpy.context.scene.quick_actions.active_index` - Currently selected item index
- `bpy.context.scene.quick_actions.show_edit_mode` - Edit mode toggle
- `bpy.context.scene.quick_actions.group_by_category` - Category grouping toggle

### QuickActionItem Properties

- `enabled`: bool - Whether to show this action
- `label`: str - Display name
- `operator`: str - Operator ID
- `operator_args`: str - Operator arguments string
- `icon`: str - Icon name
- `category`: str - Category for grouping

### Operators

- `quickactions.add_action` - Add a new action
- `quickactions.remove_action` - Remove selected action
- `quickactions.move_action` - Move action up/down
- `quickactions.run_action` - Execute an action
- `quickactions.add_preset` - Add preset action set
- `quickactions.clear_all` - Clear all actions

## Compatibility

- **Blender**: 4.0.0+
- **Python**: 3.10+

## License

MIT License - See project LICENSE file.
