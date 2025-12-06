# PlantSystem Geometry Nodes - Handoff Document

## Current State Summary

The PlantSystem is a Blender geometry nodes network for procedural plant generation. It was **rebuilt on 2024-12-05**, **extended on 2024-12-06** with taper, lean, and height variation features, **extended on 2025-12-05** with crook (trunk bending) system, and **extended on 2025-12-05** with branching system and procedural bark material.

### What Works ✓ (13 of 15 parameters)

**Trunk Parameters:**

- **Trunk Count** - Exact number of trunks to generate (density normalized by grid area)
- **Trunk Height** - Controls Z height of trunks  
- **Height Variation** - Random per-trunk height scaling (0=uniform, 1=huge range)
- **Trunk Radius** - Controls trunk tube thickness (base radius)
- **Trunk Taper** - Controls radius reduction from base to tip (0=cylinder, 1=cone)
- **Chaos** - Per-point random XY offset (uses Index+Seed for variation)
- **Lean** - Random trunk tilt in radians (0.3 ≈ 8°, 0.6 ≈ 22°)
- **Crook** - Noise-based trunk bending strength (0=straight, 1+=curved)
- **Crook Scale** - Noise frequency for bends (low=gentle curves, high=wiggly)
- **Seed** - Controls distribution pattern and all randomization

**Branch Parameters:**

- **Branches Per Level** - Number of branches per trunk (sampled along trunk height)
- **Branch Length Ratio** - Branch length as ratio of trunk height (0.5 = half trunk height)
- **Branch Angle** - Angle in degrees branches spread from trunk (45° typical)

### What Does NOT Work ✗ (2 parameters)

- **Branch Generations** - NOT CONNECTED (would need Repeat Zone for recursive branching)
- **Gravity** - NOT CONNECTED (needs additional curve deformation)

### Warnings

None - the Point Cloud warning was fixed by switching to mesh-based distribution.

---

## Architecture Overview

### Node Count

- **74 nodes**, **91 links** (after branching system and bark material)

### Interface Parameters (16 sockets total)

| Socket ID | Parameter | Type | Default | Status |
|-----------|-----------|------|---------|--------|
| Socket_0 | Geometry | Geometry | - | Input (not used) |
| Socket_1 | Trunk Count | Int | 5 | ✓ Working → DensityCalc (exact count) |
| Socket_2 | Trunk Height | Float | 2.0 | ✓ Working → TrunkCurve.Length + CrookHeightDivide |
| Socket_14 | Height Variation | Float | 0.3 | ✓ Working → HeightScale.Scale Z |
| Socket_3 | Trunk Radius | Float | 0.1 | ✓ Working → TaperMultiply (base radius) |
| Socket_12 | Trunk Taper | Float | 0.8 | ✓ Working → Taper system (0=cylinder, 1=cone) |
| Socket_4 | Branches Per Level | Int | 3 | ✓ Working → BranchPoints.Count |
| Socket_5 | Branch Generations | Int | 2 | NOT CONNECTED (needs Repeat Zone) |
| Socket_6 | Branch Length Ratio | Float | 0.5 | ✓ Working → BranchLengthMult |
| Socket_7 | Branch Angle | Float | 45.0 | ✓ Working → BranchAngleToRad |
| Socket_10 | Seed | Int | 42 | ✓ Working → Distribute + all random nodes |
| Socket_8 | Chaos | Float | 0.3 | ✓ Working → ChaosScale.Scale |
| Socket_9 | Gravity | Float | 0.2 | NOT CONNECTED |
| Socket_13 | Lean | Float | 0.2 | ✓ Working → LeanRotate (random tilt) |
| Socket_15 | Crook | Float | 0.2 | ✓ Working → CrookScale (bend strength) |
| Socket_16 | Crook Scale | Float | 2.0 | ✓ Working → CrookNoise.Scale (frequency) |

---

## Data Flow Analysis

### Trunk Count Normalization (Added 2025-12-05)

The `Distribute Points on Faces` node uses density (points per unit area), not an exact count. To make Trunk Count an **exact number**, we normalize by grid area:

```
Group Input[Trunk Count]
    ↓
DensityCalc (Math DIVIDE)
    ├── Value: Trunk Count
    └── Value: GridArea (4 × 4 = 16)
    ↓
Distribute Points on Faces[Density]
```

**Result:** Setting Trunk Count=10 produces exactly 10 trunks.

| Node | Purpose |
|------|--------|
| GridSizeX | Value node (4.0) - grid X dimension |
| GridSizeY | Value node (4.0) - grid Y dimension |
| GridArea | Math MULTIPLY - calculates area |
| DensityCalc | Math DIVIDE - Trunk Count / Area |

### Trunk Generation Path (Rebuilt)

```
Grid (4x4 planting area)
    ↓
Distribute Points on Faces
    ├── Density: Trunk Count
    └── Seed: Seed parameter
    ↓
PointIndex + Seed → SeedCombine (Math ADD)
    ↓
ChaosRandom (Random Value VECTOR)
    ↓
ChaosScale (Vector Math SCALE) ← Chaos parameter
    ↓
ApplyChaos (Set Position with Offset)
    ↓
PlaceTrunks (Instance on Points)
    ├── Points: ApplyChaos output
    ├── Instance: TaperSetRadius output (CURVE, not mesh)
    ├── Rotation: ApplyLean output (tilted rotation)
    └── Scale: HeightScaleCombine output (Z-axis variation)
    ↓
RealizeTrunks (Realize Instances) → individual curves per trunk
    ↓
CrookSetPosition (Set Position with Offset)
    ├── Geometry: RealizeTrunks output (curves)
    └── Offset: CrookScale output (noise-based XY displacement)
    ↓
FinalCurveToMesh (Curve to Mesh)
    ├── Curve: CrookSetPosition output
    ├── Profile: TrunkProfile
    └── Scale: FinalRadiusRead (taper)
    ↓
Group Output
```

### Trunk Curve Generation (with Taper)

```
TrunkCurve.001 (Curve Line, Direction Z)
    ├── Length: Trunk Height
    ↓
TrunkResample.001 (8 segments)
    ↓
TaperSetRadius (Set Curve Radius)
    ├── Radius: TaperMultiply output
    │       └── Trunk Radius × TaperMapRange
    │               └── TaperMapRange: (1-Taper) to 1.0
    │                       └── TaperInvert: 1 - SplineParameter.Factor
    ↓
PlaceTrunks (Instance on Points) → curves instanced, not converted to mesh yet
```

**Note:** Mesh conversion happens AFTER crook deformation via `FinalCurveToMesh`.

### Height Variation System

```
Group Input[Height Variation]
    ↓
HeightVarRandom (Random Value, 0 to 1)
    ├── Seed: PointIndex + Seed
    ↓
Math SUBTRACT (1 - random)
    ↓
Math MULTIPLY × Height Variation parameter
    ↓
Math SUBTRACT (1 - result) → gives 1-var to 1 range
    ↓
HeightScale (Combine XYZ)
    ├── X: 1.0 (fixed)
    ├── Y: 1.0 (fixed)
    └── Z: height scale factor
    ↓
Instance on Points[Scale]
```

### Lean (Random Tilt) System

```
LeanRandom (Random Value VECTOR)
    ├── Min: (-Lean, -Lean, 0)
    └── Max: (Lean, Lean, 0)
    ├── Seed: PointIndex + Seed
    ↓
LeanEuler (Euler to Rotation) - converts vector to rotation
    ↓
LeanRotate (Rotate Rotation)
    ├── Rotation: Distribute Points.Rotation (base orientation)
    └── Rotate By: LeanEuler output
    ↓
Instance on Points[Rotation]
```

### Taper System Nodes

| Node | Purpose |
|------|--------|
| TaperSplineParam | Gets Factor (0→1) along curve |
| TaperInvert | 1 - Factor (1 at base, 0 at tip) |
| TaperMapRange | Maps to (1-taper)→1 range |
| TaperMin | Calculates 1-taper for min radius |
| TaperMultiply | Trunk Radius × taper factor |
| TaperSetRadius | Sets radius attribute on curve points |
| TaperRadiusRead | Reads radius for Curve to Mesh Scale |

### Height Variation Nodes

| Node | Purpose |
|------|--------|
| HeightVarRandom | Random 0-1 per instance (seeded by Index+Seed) |
| HeightVar1MinusRand | 1 - random (so high random = low scale) |
| HeightVarScale | Multiply by Height Variation parameter |
| HeightVar1MinusResult | 1 - result (gives 1-var to 1 range) |
| HeightScale | Combine XYZ with Z = scale factor |

### Lean System Nodes

| Node | Purpose |
|------|--------|
| LeanRandom | Random vector (-lean to +lean) on X,Y |
| LeanEuler | Euler to Rotation conversion |
| LeanRotate | Rotate Rotation to combine with base |

### Crook (Trunk Bending) System

Added **2025-12-05**. Applies noise-based deformation to realized trunk curves, giving each trunk unique bends while preserving cylindrical cross-section.

**Key Design Decisions:**

1. Crook is applied to CURVES after `RealizeTrunks` but BEFORE `Curve to Mesh` - this ensures the cylindrical profile is built around the bent centerline
2. Only XY offset is applied (Z is forced to 0) to preserve trunk heights
3. Offset increases with height (more bend at trunk top)

```
CrookPosition (Input Position)
    ↓
CrookNoise (Noise Texture 3D)
    ├── Vector: CrookPosition
    └── Scale: Crook Scale parameter
    ↓
CrookCenter (Vector Math SUBTRACT)
    └── Subtracts (0.5, 0.5, 0) to center noise around 0
    ↓
CrookSeparateXY (Separate XYZ)
    ↓
CrookCombineXY (Combine XYZ)
    └── Z forced to 0 (XY only offset)
    ↓
CrookSeparateZ (Separate XYZ - from Position)
    └── Gets Z from Position
    ↓
CrookHeightDivide (Math DIVIDE)
    └── Z ÷ Trunk Height = normalized height (0 at ground, 1 at top)
    ↓
CrookHeightClamp (Clamp 0-1)
    ↓
CrookHeightMult (Vector Math SCALE)
    ├── Vector: CrookCombineXY output
    └── Scale: CrookHeightClamp (height factor)
    ↓
CrookScale (Vector Math SCALE)
    ├── Vector: CrookHeightMult output
    └── Scale: Crook parameter
    ↓
CrookSetPosition (Set Position)
    ├── Geometry: RealizeTrunks output (curves)
    └── Offset: CrookScale output
    ↓
FinalCurveToMesh (Curve to Mesh)
    ├── Curve: CrookSetPosition output
    ├── Profile: TrunkProfile
    └── Scale: FinalRadiusRead (for taper)
    ↓
Group Output
```

### Crook System Nodes

| Node | Purpose |
|------|--------|
| CrookPosition | Gets world position of each curve point |
| CrookNoise | 3D Noise Texture for organic variation |
| CrookCenter | Centers noise output around 0 (-0.5 to 0.5) |
| CrookSeparateXY | Separates X, Y, Z from centered noise |
| CrookCombineXY | Recombines with Z=0 (XY only offset) |
| CrookSeparateZ | Extracts Z component from position |
| CrookHeightDivide | Normalizes Z by trunk height |
| CrookHeightClamp | Clamps to 0-1 range |
| CrookHeightMult | Scales offset by height (more bend at top) |
| CrookScale | Scales final offset by Crook parameter |
| CrookSetPosition | Applies offset to realized curves |
| FinalCurveToMesh | Converts bent curves to cylindrical mesh |
| FinalRadiusRead | Reads curve radius for mesh scale |

### Branch Generation Path

**Not yet implemented.** The branch system will need:

- Repeat Zone for generations
- Branch Angle for orientation
- Gravity for downward bend

---

## Root Cause of Original Warning (FIXED)

The warning `Input geometry has unsupported type: Point Cloud` was caused by:

```
GeometryNodePoints → Set Position → Instance on Points[Points input]
```

The `GeometryNodePoints` node outputs a **Point Cloud**, but `Instance on Points` expects **Mesh vertices** or **Curve points**.

### The Fix (Implemented)

Used **Mesh Grid + Distribute Points on Faces**:

```
Grid → Distribute Points on Faces → Set Position → Instance on Points
```

This produces mesh-based points that Instance on Points handles correctly.

---

## Next Steps

### Priority 1: Add Branching System

1. Sample points along trunk curves using `Sample Curve` or `Curve to Points`
2. Use `Repeat Zone` for recursive branch generations
3. Connect **Branches Per Level** to control spawn count per trunk point
4. Connect **Branch Angle** to rotation input
5. Connect **Branch Length Ratio** to scale branches relative to parent

### Priority 2: Add Gravity Effect

Use `Set Curve Tilt` or `Set Position` with Z-offset based on curve parameter:

- Connect **Gravity** parameter
- Apply downward offset that increases along curve length

### Priority 3: Connect to Input Geometry

Currently uses built-in 4x4 Grid. To support custom shapes:

2. Make Grid size parameters (or remove Grid entirely)

---

## MCP Tools for Geometry Nodes

### Available Tools (14 total for geometry nodes)

| Tool | Purpose |
|------|---------|
| `get_node_tree_interface` | List all input/output sockets |
| `get_node_details` | Get node sockets and properties |
| `get_node_links` | Get all links in node tree |
| `get_node_connections` | All connections to/from a node |
| `trace_node_dataflow` | Find paths between sockets |
| `set_geonode_parameter` | Set modifier parameter with refresh |
| `find_orphan_nodes` | Find disconnected nodes |
| `validate_geonode_network` | Check for issues |
| `delete_geonode_node` | Remove a node cleanly |
| `delete_geonode_link` | Remove a link between nodes |
| `insert_node_between` | Insert node between existing link |
| `inspect_node_type` | Inspect node sockets BEFORE creating |
| `create_geonode_node` | Create node with validation |
| `create_geonode_link` | Create link with validation |

### Key Tool: `insert_node_between`

**Purpose:** Insert a node between two already-connected nodes without manually rewiring.

**Parameters:**

- `node_tree_name`: Name of the geometry node tree
- `node_type`: Type of node to insert (e.g., "ShaderNodeMath")
- `from_node`: Source node name
- `from_socket`: Source socket name or index
- `to_node`: Target node name
- `to_socket`: Target socket name or index
- `input_socket`: Socket on new node to receive input (default: 0)
- `output_socket`: Socket on new node to send output (default: 0)

**Example use case:** Adding a Math MULTIPLY between Trunk Radius and Curve to Mesh.

---

## Key Files

| File | Purpose |
|------|---------|
| `src/blender_mcp/server.py` | MCP server tools (40 total) |
| `addon.py` | Blender addon handlers |
| `docs/BLENDER_API_LESSONS.md` | API quirks and workarounds discovered |
| `docs/PLANTSYSTEM_HANDOFF.md` | This document |
| `blender/testing01.blend` | Saved scene with current PlantSystem |

---

## Important Patterns Discovered

### Force Modifier Update

```python
mod["Socket_X"] = value
mod.show_viewport = False
mod.show_viewport = True
bpy.context.view_layer.update()
```

### Math Passthrough for Field→Scalar

```python
passthrough = ng.nodes.new("ShaderNodeMath")
passthrough.operation = "ADD"
passthrough.inputs[1].default_value = 0.0
# Connect Group Input → passthrough → target
```

### Per-Instance Variation via Scale

When you need per-instance variation (e.g., height) but the base geometry (curve) is shared:

```python
# WRONG: Modifying curve length affects all instances uniformly
# RIGHT: Use Instance on Points Scale input for per-instance variation

height_scale = ng.nodes.new("ShaderNodeCombineXYZ")
height_scale.inputs[0].default_value = 1.0  # X
height_scale.inputs[1].default_value = 1.0  # Y
# Connect height factor to Z input
ng.links.new(height_factor.outputs[0], height_scale.inputs[2])
ng.links.new(height_scale.outputs[0], instance_on_points.inputs["Scale"])
```

### Combining Rotations

To add random tilt to existing rotation:

```python
# Convert Euler angles to rotation type
euler_to_rot = ng.nodes.new("FunctionNodeEulerToRotation")

# Combine with existing rotation
rotate_rot = ng.nodes.new("FunctionNodeRotateRotation")
ng.links.new(base_rotation, rotate_rot.inputs["Rotation"])
ng.links.new(euler_to_rot.outputs[0], rotate_rot.inputs["Rotate By"])
```

### Checking Evaluated Geometry

```python
dg = bpy.context.evaluated_depsgraph_get()
obj_eval = obj.evaluated_get(dg)
mesh = obj_eval.to_mesh()
# ... use mesh ...
obj_eval.to_mesh_clear()
```

---

## Test Commands

Set parameters and verify:

```python
import bpy
soil = bpy.data.objects.get("Soil")
mod = soil.modifiers.get("PlantSystem")
mod["Socket_1"] = 5      # Trunk Count
mod["Socket_2"] = 3.0    # Trunk Height
mod["Socket_14"] = 0.4   # Height Variation
mod["Socket_3"] = 0.15   # Trunk Radius
mod["Socket_12"] = 0.8   # Trunk Taper
mod["Socket_13"] = 0.3   # Lean
mod["Socket_8"] = 0.4    # Chaos
mod["Socket_15"] = 0.5   # Crook (bend strength)
mod["Socket_16"] = 2.5   # Crook Scale (noise frequency)
mod["Socket_10"] = 42    # Seed
mod.show_viewport = False
mod.show_viewport = True
```

---

## Summary

**Status as of 2025-12-05:** The PlantSystem is working with 13 of 15 parameters connected:

- ✅ Trunk Count, Trunk Height, Height Variation, Trunk Radius, Trunk Taper, Chaos, Lean, Crook, Crook Scale, Seed
- ✅ Branches Per Level, Branch Length Ratio, Branch Angle
- ⏳ Branch Generations, Gravity

**Network Stats:** 74 nodes, 91 links, validation passed

**Key lessons learned:**

1. Curve to Mesh uses its `Scale` input, not the curve's radius attribute automatically. Add a `Radius` input node connected to Scale.
2. Per-instance variation (like height) requires Instance Scale, not modifying the shared curve.
3. Use `Rotate Rotation` + `Euler to Rotation` to combine random angles with base rotation.
4. **Crook must be applied to CURVES before Curve to Mesh** - applying to mesh vertices flattens the cylindrical cross-section. Apply to curves, then convert to mesh.
5. **Spline Parameter doesn't work on mesh data** - use Position Z / Trunk Height for height-based effects on realized geometry.
6. **Distribute Points density is per unit area** - to get exact count, divide by grid area: `TrunkCount / (SizeX × SizeY)`.
7. **Force Z=0 in XY deformations** - Separate then Combine XYZ with Z=0 to prevent vertical distortion.
8. **Use Generated coordinates for materials on instanced geometry** - Object coordinates follow global axes, Generated follows local mesh bounding box.
9. **Trim Curve to control branch distribution** - Use TrimCurve with factor mode to limit branches to specific trunk height range (30%-85%).
10. **Align branches to trunk tangent** - Use `Align Euler to Vector` with curve tangent output for proper branch orientation.

**Next session:** Implement Branch Generations with Repeat Zone, add Gravity effect.

---

---

## Branching System (Added 2025-12-05)

### Overview

A first-generation branching system has been implemented that creates branches along the trunk height. Branches are distributed from 30% to 85% of trunk height and oriented perpendicular to the trunk with random rotation around the trunk axis.

### Branch Node Structure (21 new nodes)

```
CrookSetPosition (trunk curves)
    ↓
TrimForBranches (Factor: 0.3 to 0.85)
    ↓
BranchPoints (Curve to Points, COUNT mode)
    ├── Count ← Socket_4 (Branches Per Level)
    ├── outputs: Points, Tangent, Normal
    ↓
┌─────────────────────────────────────────────────┐
│ ROTATION CHAIN:                                 │
│                                                 │
│ BranchIndex → BranchSeedCombine (+ Seed)        │
│     ↓                                           │
│ BranchZRandom (0 to 2π)                         │
│     ↓                                           │
│ BranchZCombine → BranchZEuler                   │
│     ↓                                           │
│ BranchAngleToRad ← Socket_7 (degrees)           │
│     ↓                                           │
│ BranchAngleCombine → BranchAngleEuler           │
│     ↓                                           │
│ BranchCombineRotations (Z + Angle)              │
│     ↓                                           │
│ AlignToTrunkTangent ← BranchPoints.Tangent      │
│     ↓                                           │
│ FinalBranchRotation                             │
└─────────────────────────────────────────────────┘
    ↓
InstanceBranches
    ├── Points: BranchPoints output
    ├── Instance: BranchSetRadius output
    └── Rotation: FinalBranchRotation
    ↓
RealizeBranches
    ↓
JoinTrunkBranches (joins trunk + branch curves)
    ↓
FinalCurveToMesh
```

### Branch Curve Generation

```
BranchCurve (Curve Line, DIRECTION mode)
    ├── Direction: (1, 0, 0.3) - outward and slightly up
    ├── Length ← BranchLengthMult output
    │       └── Trunk Height × Branch Length Ratio
    ↓
BranchSetRadius
    ├── Radius ← BranchRadiusScale (40% of trunk radius)
    ↓
InstanceBranches
```

### Key Parameters

| Parameter | Socket | Effect |
|-----------|--------|--------|
| Branches Per Level | Socket_4 | Number of branches per trunk |
| Branch Length Ratio | Socket_6 | Branch length = Trunk Height × Ratio |
| Branch Angle | Socket_7 | Angle (degrees) from vertical |

### Branch Distribution

- **Height Range:** 30% to 85% of trunk height (via TrimForBranches)
- **Radial Distribution:** Random 0-360° around trunk (via BranchZRandom)
- **Orientation:** Aligned to trunk tangent for natural appearance
- **Radius:** 40% of trunk radius (via BranchRadiusScale)

---

## Procedural Bark Material (Added 2025-12-05)

### Overview

A fully procedural bark material (`BarkMaterial`) has been created and applied to the trunks via a `SetBarkMaterial` node in the geometry nodes.

### Material Node Structure (14 nodes)

```
BarkTexCoord (Texture Coordinate)
    ↓ Object output
BarkMapping (Mapping, Scale: 12, 2, 1)  ← vertical streaks
    ↓
    ├─→ NoiseColorLarge (Noise Texture, Scale: 3, Detail: 6)
    │       ↓ Fac
    │   RampColorLarge (Color Ramp: 0.35-0.65, dark→medium brown)
    │       ↓
    ├─→ NoiseColorFine (Noise Texture, Scale: 20, Detail: 8)
    │       ↓ Fac
    │   RampColorFine (Color Ramp: 0.4-0.6, subtle variation)
    │       ↓
    └─→ MixBarkColors (Mix RGBA, Factor: 0.4)
            ↓ → BarkBSDF.Base Color

    ├─→ BarkVoronoi (Voronoi, Distance to Edge, Scale: 25)
    │       ↓ Distance
    ├─→ NoiseBump (Noise Texture, Scale: 40, Detail: 12)
    │       ↓ Fac
    └─→ MixBump (Mix Float, Factor: 0.5)
            ↓
        RampBump (Color Ramp, contrast control)
            ↓
        BarkBump (Bump, Strength: 0.4, Distance: 0.02)
            ↓ Normal → BarkBSDF.Normal

BarkBSDF (Principled BSDF)
    ├── Base Color: MixBarkColors output
    ├── Roughness: 0.85 (matte bark surface)
    └── Normal: BarkBump output
    ↓ BSDF
Material Output
```

### Color Palette

| Element | RGB Values | Description |
|---------|-----------|-------------|
| Very Dark Brown | (0.04, 0.025, 0.015) | Shadows, crevices |
| Medium Brown | (0.12, 0.07, 0.04) | Main bark color |
| Fine Dark | (0.06, 0.04, 0.025) | Detail shadows |
| Fine Light | (0.1, 0.06, 0.035) | Detail highlights |

### Key Parameters

- **Mapping Scale (8, 1, 8):** Creates vertical bark streaks using Generated coordinates
- **Texture Coordinates:** Uses Generated (not Object) so bark follows trunk direction even when tilted
- **Voronoi Scale: 25** - Controls crack/ridge density
- **Bump Strength: 0.4** - Subtle but visible surface detail
- **Roughness: 0.85** - Matte, non-reflective bark surface

### Geometry Nodes Integration

The material is applied via `SetBarkMaterial` node (node 53):

```
FinalCurveToMesh
    ↓ Geometry
SetBarkMaterial (Material: BarkMaterial)
    ↓ Geometry
Group Output
```

**Network Stats after bark material:** 53 nodes in PlantSystem

---

## Test Commands

Set all parameters and verify:

```python
import bpy
soil = bpy.data.objects.get("Soil")
mod = soil.modifiers.get("PlantSystem")

# Trunk parameters
mod["Socket_1"] = 5       # Trunk Count
mod["Socket_2"] = 4.0     # Trunk Height
mod["Socket_14"] = 0.3    # Height Variation
mod["Socket_3"] = 0.1     # Trunk Radius
mod["Socket_12"] = 0.7    # Trunk Taper
mod["Socket_13"] = 0.15   # Lean
mod["Socket_8"] = 0.3     # Chaos
mod["Socket_15"] = 0.25   # Crook
mod["Socket_16"] = 2.5    # Crook Scale
mod["Socket_10"] = 42     # Seed

# Branch parameters
mod["Socket_4"] = 5       # Branches Per Level
mod["Socket_6"] = 0.5     # Branch Length Ratio
mod["Socket_7"] = 45.0    # Branch Angle (degrees)

# Force update
mod.show_viewport = False
mod.show_viewport = True
bpy.context.view_layer.update()
```

---

## Session History

### 2025-12-05 (Session 3)

- ✅ Implemented procedural bark material (14 shader nodes)
- ✅ Fixed bark texture to use Generated coordinates (follows trunk direction)
- ✅ Implemented branching system (21 new geometry nodes)
- ✅ Connected Branches Per Level, Branch Length Ratio, Branch Angle parameters
- ✅ Added TrimForBranches for height-based branch distribution
- ✅ Added AlignToTrunkTangent for proper branch orientation
- **Network grew from 53 to 74 nodes**

### 2025-12-05 (Session 2)

- ✅ Implemented crook system for trunk bending
- ✅ Fixed trunk count accuracy (density normalization)
- ✅ Restructured to apply crook to curves before mesh conversion

### 2024-12-06 (Session 1)

- ✅ Added taper, lean, and height variation
- ✅ Initial PlantSystem rebuild
