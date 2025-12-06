# Blender API Lessons Learned

This document tracks mistakes made when working with Blender via MCP and how to prevent them.

---

## Session: 2024-12-05 - Plant Stalks Geometry Nodes

### Mistake 1: Assuming socket names without verification

**What happened:** Tried to access `resample.mode` and `distribute.inputs["Density Max"]` without first checking if they exist in Blender 5.0.

**Error:** `'GeometryNodeResampleCurve' object has no attribute 'mode'` and `key "Density Max" not found`

**Prevention:**

- Always inspect node sockets FIRST before building complex networks
- Use a small test script to enumerate `node.inputs` and `dir(node)` for available attributes
- Blender versions change API - never assume socket names from memory

### Mistake 2: Over-engineering the first attempt

**What happened:** User asked for "a single stalk growing up out of a plane" with basic controls. I built a 25-node network with distribution, instancing, random rotation, and organic bending.

**What user wanted:** A simple, single stalk at center with height, taper, orientation, and bend controls.

**Prevention:**

- Start with the MINIMUM viable implementation
- Ask clarifying questions if scope is unclear
- Build incrementally - add complexity only when requested

### Mistake 3: Not verifying results visually before declaring success

**What happened:** Declared "SUCCESS" based on code execution without confirming the visual result matched expectations.

**Prevention:**

- Always capture and review screenshots after geometry nodes work
- Use `get_node_details` to verify the network structure
- Check for orphaned/unconnected nodes

### Mistake 4: Multiple failed iterations polluting the scene

**What happened:** Failed code executions left partial objects and node groups that needed manual cleanup.

**Prevention:**

- Clear scene state explicitly before major operations
- Use try/except to clean up on failure
- Check scene state after errors before retrying

### Mistake 5: Using name-based socket access when indexes are more reliable

**What happened:** Socket names can vary between Blender versions or node configurations. Index-based access worked when name-based failed.

**Prevention:**

- Prefer index-based socket access for reliability: `node.inputs[0]` vs `node.inputs["Name"]`
- When using names, wrap in try/except with fallback to index

---

## Quick Reference: Geometry Nodes Inspection Pattern

```python
# Before building, always inspect the nodes you'll use:
temp = bpy.data.node_groups.new(name="Inspect", type="GeometryNodeTree")
node = temp.nodes.new("GeometryNodeSomeType")

print("Inputs:")
for i, inp in enumerate(node.inputs):
    print(f"  [{i}] {inp.name} ({inp.bl_idname})")

print("Outputs:")
for i, out in enumerate(node.outputs):
    print(f"  [{i}] {out.name} ({out.bl_idname})")

print("Attributes:", [a for a in dir(node) if not a.startswith('_')])

bpy.data.node_groups.remove(temp)
```

---

## Blender 5.0 Specific Notes

- `GeometryNodeResampleCurve` uses `inputs["Mode"]` menu socket, not a `.mode` attribute
- Distribute Points node socket order: Mesh, Selection, Distance Min, Density Max, Density, Density Factor, Seed
- Always check socket types match when linking (Int vs Float can cause silent failures)

---

## Session: 2024-12-05 - Plant Stalks v2 (Simplified)

### Code Execution Log

**Attempt 1: Clear scene**

- Status: ✅ SUCCESS
- Result: Scene cleared (0 objects, 0 node groups, 0 materials)

**Attempt 2: Inspect nodes before building**

- Status: ✅ SUCCESS  
- Result: Got exact socket indices for all nodes I need
- Lesson: This prevented socket name errors that plagued v1

**Attempt 3: Build minimal geometry nodes**

- Status: ⚠️ INTERRUPTED (Ctrl+C in terminal)
- Result: Partial execution - Soil object created, node group partially built
- Recovery: Checked scene state, found 16 nodes/22 links created successfully

**Attempt 4: Check for orphans (first try)**

- Status: ❌ FAILED
- Error: `unterminated string literal (detected at line 23)`
- Cause: Used `\\n` in f-string which doesn't work in triple-quoted strings passed through JSON
- Fix: Use string concatenation instead of f-strings with newlines

**Attempt 5: Check for orphans (fixed)**

- Status: ✅ SUCCESS
- Result: All 16 nodes connected, no orphans, modifier values correct

### String Escaping Rules for execute_blender_code

When passing Python code through the bridge:

1. Use `\"` for strings inside the code block (escaped for JSON)
2. Avoid `\\n` in strings - use print() calls or string concatenation
3. Avoid f-strings with complex expressions - use `str()` concatenation
4. Test simple code first, then add complexity

### Mistake 6: Map Range direction confusion

**What happened:** Wired Base Radius to `To Max` and Tip Radius to `To Min`, but Spline Factor goes 0→1 from base to tip.

**The math:**

- Spline Factor = 0 at base, 1 at tip
- Map Range: when Value=0, output=To Min; when Value=1, output=To Max
- Therefore: To Min = Base Radius, To Max = Tip Radius

**Fix:** Swapped the links so Base Radius → To Min, Tip Radius → To Max

**Prevention:**

- Draw out the data flow on paper first
- Test with extreme values to verify direction (e.g., Base=1.0, Tip=0.001)

---

## Session: 2024-12-05 - PlantSystem Full Build

### Build Log

| Step | Status | Nodes | Links | Notes |
|------|--------|-------|-------|-------|
| Create PlantSystem interface | ✅ | 2 | 0 | 10 input parameters |
| Trunk distribution | ✅ | 17 | 22 | Points + chaos offset |
| Add Repeat Zone (aborted) | ⚠️ | - | - | Too complex for MVP |
| Add branch generation | ✅ | 39 | 49 | Single generation of branches |
| Clean orphan nodes | ✅ | 35 | 49 | Removed 4 orphans |
| Add gravity droop | ✅ | 40 | 56 | Quadratic Z offset |
| Add chaos noise | ✅ | 48 | 66 | Noise-based XY wobble |
| Final cleanup | ✅ | 47 | 66 | Removed 1 orphan |

### Current PlantSystem Parameters

| Socket | Parameter | Type | Description |
|--------|-----------|------|-------------|
| 1 | Trunk Count | Int | Number of main stems |
| 2 | Trunk Height | Float | Height in meters |
| 3 | Trunk Radius | Float | Base thickness |
| 4 | Branches Per Level | Int | (Not yet implemented) |
| 5 | Branch Generations | Int | (Not yet implemented) |
| 6 | Branch Length Ratio | Float | Child length vs parent |
| 7 | Branch Angle | Float | (Not yet fully implemented) |
| 8 | Chaos | Float | Noise-based variation |
| 9 | Gravity | Float | Downward droop |
| 10 | Seed | Int | Random seed |

### Still TODO

- Multiple branches per trunk (Branches Per Level)
- Multiple generations (Repeat Zone or explicit unrolling)
- Mesh instancing per generation (leaves, flowers)
- Proper branch angle from parent direction

---

## Session: 2024-12-06 - Debugging PlantSystem Parameters

### Mistake 7: Set Curve Radius doesn't automatically affect Curve to Mesh

**What happened:** Built a chain of Spline Parameter → Map Range → Set Curve Radius → Curve to Mesh, but Trunk Radius changes had no visible effect.

**Root cause:** Set Curve Radius stores the radius as a per-point attribute on the curve, but Curve to Mesh's Scale input defaults to 1.0 and doesn't automatically read this attribute.

**Initial failed fix:** Added a `Radius` input node (`GeometryNodeInputRadius`) connected to Curve to Mesh Scale. This reads the radius attribute, but didn't work because the radius attribute was being evaluated in the wrong context (profile curve context vs main curve context).

**Working fix:** Removed the Set Curve Radius/Map Range chain entirely. Connected Trunk Radius directly to Curve Circle Radius for uniform width OR use a Math passthrough node to Curve to Mesh Scale.

**Key insight:** Curve to Mesh Scale needs a scalar value, not a field. Group Input values are technically "fields" (could vary per element). A Math node with `ADD 0` acts as a passthrough that converts the field to a scalar.

### Mistake 8: Linking Group Input directly to Curve Circle radius doesn't work

**What happened:** Connected Group Input[Trunk Radius] directly to Curve Circle[Radius], but changes to the parameter had no effect.

**Root cause:** Curve primitive nodes (Curve Line, Curve Circle) may not properly evaluate linked parameter inputs in all contexts.

**Working solution:** Use a Math node passthrough:

```python
passthrough = ng.nodes.new("ShaderNodeMath")
passthrough.operation = "ADD"
passthrough.inputs[1].default_value = 0.0
ng.links.new(group_input.outputs["Trunk Radius"], passthrough.inputs[0])
ng.links.new(passthrough.outputs[0], curve_to_mesh.inputs[2])  # Scale
```

### Mistake 9: Modifier parameter changes not updating geometry

**What happened:** Changed modifier socket values (e.g., `mod["Socket_1"] = 1`), but `view_layer.update()` didn't cause the geometry nodes to re-evaluate.

**Root cause:** Blender's depsgraph caches geometry nodes results and doesn't always invalidate when only modifier properties change via Python.

**Working solution:** Toggle the modifier visibility to force re-evaluation:

```python
mod["Socket_1"] = new_value
mod.show_viewport = False
mod.show_viewport = True
bpy.context.view_layer.update()
```

### Mistake 10: Including base geometry in output

**What happened:** The PlantSystem was joining Group Input geometry (the Soil plane) with the generated trunks, causing the bounding box to always include the original plane dimensions.

**Root cause:** Original design linked `Group Input[Geometry] → Join Geometry` to preserve the base mesh.

**Fix:** Removed the link from Group Input Geometry to Join Geometry since we want only the generated plant geometry.

### Current Working Node Structure

For a controllable trunk radius:

```
Group Input[Trunk Radius]
        ↓
  Math (ADD +0) [passthrough]
        ↓
Curve to Mesh[Scale]
        ↓
   (plus)
        ↓
Curve Circle[Radius=1.0] → Curve to Mesh[Profile Curve]
```

### Validated Parameters (after fixes)

| Parameter | Test Values | Result |
|-----------|-------------|--------|
| Trunk Count | 1, 3, 5 | 64, 192, 320 verts ✓ |
| Trunk Height | 2.0, 4.0, 6.0 | Z-max: 2.0, 4.0, 6.0 ✓ |
| Trunk Radius | 0.1, 0.2, 0.4 | X-range: 0.2, 0.4, 0.8 ✓ |

### Force Update Pattern

Always use this pattern when testing parameter changes:

```python
mod[socket_name] = value
mod.show_viewport = False
mod.show_viewport = True
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
obj_eval = obj.evaluated_get(dg)
mesh = obj_eval.to_mesh()
# ... use mesh ...
obj_eval.to_mesh_clear()
```

---

## New MCP Tools for Geometry Nodes Debugging (2024-12-06)

Based on pain points discovered during PlantSystem development, five new MCP tools were added:

### Tool 1: `get_node_connections`

**Purpose:** Get all connections to/from a specific node.

**When to use:**

- Debugging why a node isn't receiving expected input
- Understanding what depends on a specific node's output
- Finding unconnected sockets on a node

**Example response:**

```json
{
  "node_name": "Map Range",
  "incoming": [
    {"from_node": "Group Input", "from_socket": "Trunk Radius", "to_socket": "From Max"}
  ],
  "outgoing": [
    {"to_node": "Curve to Mesh", "from_socket": "Result", "to_socket": "Scale"}
  ],
  "unconnected_inputs": [
    {"index": 0, "name": "Value", "default_value": 0.5}
  ]
}
```

### Tool 2: `get_geometry_stats`

**Purpose:** Get vertex/face counts and bounding box AFTER modifiers are applied.

**When to use:**

- Verifying geometry nodes output changed as expected
- Checking dimensions after parameter changes
- Debugging "nothing visible" issues (0 vertices = no geometry output)

**Key feature:** Uses `evaluated_get(depsgraph)` to get post-modifier geometry.

**Example response:**

```json
{
  "vertex_count": 320,
  "face_count": 318,
  "bounding_box": {"min": [-0.2, -0.2, 0], "max": [0.2, 0.2, 3.0]},
  "dimensions": {"x": 0.4, "y": 0.4, "z": 3.0}
}
```

### Tool 3: `trace_node_dataflow`

**Purpose:** Find the path(s) data takes from one socket to another.

**When to use:**

- Debugging "value isn't reaching destination" issues
- Understanding complex node networks
- Verifying expected data flow paths exist

**Example response:**

```json
{
  "from": {"node": "Group Input", "socket": "Trunk Radius"},
  "to": {"node": "Curve to Mesh", "socket": "Scale"},
  "direct_connection": false,
  "paths": [
    [
      {"node": "Group Input", "socket": "Trunk Radius"},
      {"node": "Math.001", "socket": "Value"},
      {"node": "Curve to Mesh", "socket": "Scale"}
    ]
  ]
}
```

### Tool 4: `set_geonode_parameter`

**Purpose:** Set modifier parameter with automatic depsgraph refresh.

**Why it exists:** Blender often doesn't re-evaluate geometry nodes when parameters change via Python. This tool uses the viewport toggle workaround automatically.

**Workaround applied:**

```python
mod[socket_id] = value
mod.show_viewport = False
mod.show_viewport = True
bpy.context.view_layer.update()
```

**Example response:**

```json
{
  "success": true,
  "parameter": {"name": "Trunk Count", "identifier": "Socket_1"},
  "old_value": 3,
  "new_value": 5,
  "geometry_updated": true
}
```

### Tool 5: `find_orphan_nodes`

**Purpose:** Find disconnected or partially-connected nodes.

**When to use:**

- Cleaning up after failed node creation attempts
- Finding accidentally disconnected nodes
- Identifying required inputs that aren't connected

**Example response:**

```json
{
  "orphan_nodes": [
    {"name": "Math.002", "type": "ShaderNodeMath"}
  ],
  "partial_nodes": [
    {"name": "Set Position", "unconnected_inputs": [{"name": "Position"}]}
  ],
  "unconnected_required": [
    {"node": "Curve to Mesh", "socket": "Curve"}
  ]
}
```

### Recommended Workflow

1. **Before building:** Use `inspect_node_type` to see sockets/properties BEFORE creating
2. **Creating nodes:** Use `create_geonode_node` for safe node creation with validation
3. **Creating links:** Use `create_geonode_link` for validated link creation
4. **After building:** Use `find_orphan_nodes` to verify all connections made
5. **When testing:** Use `set_geonode_parameter` instead of `execute_blender_code`
6. **To verify output:** Use `get_geometry_stats` to check mesh changed as expected
7. **When debugging:** Use `get_node_connections` on problem nodes
8. **For complex issues:** Use `trace_node_dataflow` to verify data paths
9. **Inserting nodes:** Use `insert_node_between` to add nodes in existing chains

---

## Geometry Node Building Tools (Implemented)

These tools provide a complete workflow for building geometry node networks:

### `inspect_node_type`

Inspect a node type's sockets and properties BEFORE creating it. Prevents "wrong socket name" errors.

```python
result = inspect_node_type("GeometryNodeDistributePointsOnFaces")
# Returns: inputs, outputs, properties, bl_label
```

### `create_geonode_node`

Create a node in a geometry node tree with validation and optional configuration.

```python
result = create_geonode_node(
    node_tree_name="PlantSystem",
    node_type="ShaderNodeMath",
    name="AddHeight",
    location=[200, 100],
    properties={"operation": "ADD"},
    defaults={1: 0.0}  # Set second input to 0
)
# Returns: name, type, location, inputs, outputs
```

### `create_geonode_link`

Create a link between nodes with proper validation.

```python
result = create_geonode_link(
    node_tree_name="PlantSystem",
    from_node="Grid",
    from_socket="Mesh",  # or index: 0
    to_node="Distribute Points",
    to_socket=0  # or name: "Mesh"
)
# Returns: success, actual socket names used
```

### `insert_node_between`

Insert a node between two already-connected nodes.

```python
result = insert_node_between(
    node_tree_name="PlantSystem",
    from_node="Group Input",
    from_socket="Trunk Radius",
    to_node="TrunkMesh",
    to_socket="Scale",
    new_node_type="ShaderNodeMath",
    properties={"operation": "MULTIPLY"}
)
# Returns: new_node name, links_created, link_removed
```

### `validate_geonode_network`

Comprehensive validation of a node network.

```python
result = validate_geonode_network("PlantSystem")
# Returns: is_valid, issue_count, statistics, issues list
```

### Complete Tool List (14 geometry node tools)

| Tool | Purpose |
|------|---------|
| `get_node_tree_interface` | List all input/output sockets of a node tree |
| `get_node_details` | Get node sockets and properties |
| `get_node_links` | Get all links in node tree |
| `get_node_connections` | All connections to/from a specific node |
| `trace_node_dataflow` | Find paths between sockets |
| `set_geonode_parameter` | Set modifier parameter with auto-refresh |
| `find_orphan_nodes` | Find disconnected nodes |
| `validate_geonode_network` | Comprehensive network validation |
| `delete_geonode_node` | Remove a node cleanly |
| `delete_geonode_link` | Remove a link between nodes |
| `insert_node_between` | Insert node in existing chain |
| `inspect_node_type` | Inspect node sockets BEFORE creating |
| `create_geonode_node` | Create node with validation |
| `create_geonode_link` | Create link with validation |

---

## Session: 2024-12-05 - PlantSystem Rebuild

### Key Insight: Curve to Mesh Does NOT Auto-Use Curve Radius

**Critical discovery:** The `Curve to Mesh` node has a `Scale` input that **defaults to 1.0** and does NOT automatically read the curve's radius attribute set by `Set Curve Radius`.

**Symptom:** Built a taper system with Spline Parameter → Map Range → Set Curve Radius → Curve to Mesh, but radius changes had no visible effect.

**Root cause:** Set Curve Radius stores the radius as a per-point attribute on the curve. However, Curve to Mesh needs you to explicitly READ this attribute and connect it to the Scale input.

**Solution:** Add a `Radius` input node (GeometryNodeInputRadius) and connect it to `Curve to Mesh.Scale`:

```python
# Add Radius input node - reads the radius attribute from curve points
radius_input = node_tree.nodes.new("GeometryNodeInputRadius")
radius_input.name = "TaperRadiusRead"

# Connect to Curve to Mesh Scale input
links.new(radius_input.outputs["Radius"], curve_to_mesh.inputs["Scale"])
```

**Complete Taper Pipeline:**

```
Spline Parameter (Factor: 0→1 along curve)
    ↓
Math SUBTRACT (1 - Factor, so 1 at base, 0 at tip)
    ↓
Map Range (maps to 1-taper → 1 range)
    ↓
Math MULTIPLY × Trunk Radius
    ↓
Set Curve Radius (stores per-point radius attribute)
    ↓ (curve with radius attribute)
Curve to Mesh
    ├── Scale ← GeometryNodeInputRadius (reads the radius!)
    └── Profile ← Circle (Radius=1.0, unit circle)
```

**Key nodes for taper:**

| Node | Type | Purpose |
|------|------|---------|
| GeometryNodeSplineParameter | Input | Factor (0→1 along spline) |
| GeometryNodeSetCurveRadius | Curve | Stores radius per control point |
| GeometryNodeInputRadius | Input | Reads radius attribute back |

---

### Key Insight: Density vs Density Max

The `Distribute Points on Faces` node has TWO density controls:

- **Density Max** - The MAXIMUM allowed density (cap)
- **Density** - The ACTUAL density value

Connecting to `Density Max` alone does nothing if `Density` is at a fixed low value.

**Fix:** Connect the count parameter to `Density` and set `Density Max` to a high value (1000).

### Key Insight: Per-Point Random Variation

For random values to vary PER POINT (not uniformly):

- Connect `Index` node to the Random Value's `ID` input
- Optionally combine with Seed: `Index + Seed → Random.ID`

```python
# Wrong: Same random value for all points
ng.links.new(seed_socket, random_value.inputs["ID"])

# Right: Different random value per point
index_node = ng.nodes.new("GeometryNodeInputIndex")
math_add = ng.nodes.new("ShaderNodeMath")
math_add.operation = "ADD"
ng.links.new(index_node.outputs["Index"], math_add.inputs[0])
ng.links.new(seed_socket, math_add.inputs[1])
ng.links.new(math_add.outputs["Value"], random_value.inputs["ID"])
```

---

## Session: 2024-12-06 - Per-Instance Variation and Rotation

### Key Insight: Per-Instance Scale vs Shared Geometry Modification

**Problem:** Wanted random height variation per trunk, but modifying curve length affects ALL instances uniformly (they share the same curve geometry).

**Wrong approach:** Try to vary `TrunkCurve.Length` per instance

```python
# This doesn't work - curve is shared, all instances same height
ng.links.new(height_factor, trunk_curve.inputs["Length"])
```

**Correct approach:** Use `Instance on Points` Scale input for per-instance variation

```python
# Create a Combine XYZ with X=1, Y=1, Z=height_factor
height_scale = ng.nodes.new("ShaderNodeCombineXYZ")
height_scale.inputs[0].default_value = 1.0  # X fixed
height_scale.inputs[1].default_value = 1.0  # Y fixed
ng.links.new(height_factor.outputs[0], height_scale.inputs[2])  # Z varies

# Connect to Instance on Points Scale
ng.links.new(height_scale.outputs[0], instance_on_points.inputs["Scale"])
```

**Pattern:** Whenever you need per-instance variation, check if Instance on Points has an input for it (Scale, Rotation, Pick Instance) rather than trying to modify the shared source geometry.

### Key Insight: Combining Rotations with Rotate Rotation

**Problem:** Have base rotation from Distribute Points, need to add random lean on top of it.

**Wrong approach:** Add rotation vectors

```python
# This doesn't work - rotations don't add like vectors
combined = base_rotation + lean_offset
```

**Correct approach:** Use `Rotate Rotation` node (FunctionNodeRotateRotation)

```python
# Step 1: Convert lean angles to rotation type
lean_random = ng.nodes.new("FunctionNodeRandomValue")
lean_random.data_type = "FLOAT_VECTOR"  # X, Y angles

euler_to_rot = ng.nodes.new("FunctionNodeEulerToRotation")
ng.links.new(lean_random.outputs[0], euler_to_rot.inputs["Euler"])

# Step 2: Combine with base rotation
rotate_rot = ng.nodes.new("FunctionNodeRotateRotation")
ng.links.new(distribute.outputs["Rotation"], rotate_rot.inputs["Rotation"])
ng.links.new(euler_to_rot.outputs["Rotation"], rotate_rot.inputs["Rotate By"])

# Step 3: Use combined rotation
ng.links.new(rotate_rot.outputs["Rotation"], instance_on_points.inputs["Rotation"])
```

**Key nodes for rotation:**

| Node | Type | Purpose |
|------|------|---------|
| FunctionNodeEulerToRotation | Math | Convert XYZ angles to Rotation |
| FunctionNodeRotateRotation | Math | Combine two rotations properly |
| FunctionNodeRandomValue (VECTOR) | Random | Generate random XYZ angles |

### Key Insight: Height Variation Range Math

**Goal:** Height Variation of 0.3 should give heights in range 0.7 to 1.0 (relative to base height).

**Math breakdown:**

1. Random value R in [0, 1]
2. (1 - R) flips so R=1 becomes 0
3. × HeightVar scales the effect
4. (1 - result) gives final factor

**Example:** HeightVar=0.3, Random=0.8

- (1 - 0.8) = 0.2
- 0.2 × 0.3 = 0.06
- (1 - 0.06) = 0.94 ← height scale factor

**Result:** Heights range from (1-HeightVar) to 1.0

```python
# Node chain:
# Random[0-1] → (1-R) → ×HeightVar → (1-result) → Scale.Z
var_random = ng.nodes.new("FunctionNodeRandomValue")  # 0 to 1
one_minus_rand = ng.nodes.new("ShaderNodeMath")
one_minus_rand.operation = "SUBTRACT"
one_minus_rand.inputs[0].default_value = 1.0

scale_by_var = ng.nodes.new("ShaderNodeMath")
scale_by_var.operation = "MULTIPLY"

one_minus_result = ng.nodes.new("ShaderNodeMath")
one_minus_result.operation = "SUBTRACT"
one_minus_result.inputs[0].default_value = 1.0
```

---

## MCP Tool Added: insert_node_between (2024-12-06)

### Why This Tool Exists

When building geometry node networks iteratively, you often need to insert a node between two already-connected nodes. Doing this manually requires:

1. Find and remember the existing link
2. Delete the link
3. Create node at appropriate position
4. Create two new links

The `insert_node_between` tool automates all of this.

### Tool Parameters

```python
def insert_node_between(
    node_tree_name: str,      # e.g., "PlantSystem"
    node_type: str,           # e.g., "ShaderNodeMath"
    from_node: str,           # Source node name
    from_socket: str | int,   # Source socket
    to_node: str,             # Target node name
    to_socket: str | int,     # Target socket
    input_socket: int = 0,    # Which input on new node
    output_socket: int = 0    # Which output on new node
) -> dict
```

### Example Usage

Before: `TrunkRadius → Curve to Mesh.Scale`
After: `TrunkRadius → Math.MULTIPLY → Curve to Mesh.Scale`

```python
result = await insert_node_between(
    node_tree_name="PlantSystem",
    node_type="ShaderNodeMath",
    from_node="Group Input",
    from_socket="Trunk Radius",
    to_node="TrunkMesh",
    to_socket="Scale",
    input_socket=0,
    output_socket=0
)
# New node positioned at midpoint between source and target
```

### Implementation Notes

- Auto-calculates midpoint position for the new node
- Returns new node name and connection details
- Works with both socket names and indices
- Validates the link exists before attempting insertion
