# LeafBuilder Geometry Nodes - Handoff Document

## Overview

This document covers two leaf generation systems:

1. **LeafBuilder (3D)** - High-detail procedural leaf with veins, thickness, and serration (object: `3DLeaf`)
2. **Leaf2D** - Low-poly leaf optimized for texture mapping (object: `2DLeaf`)

---

## Leaf2D (Low-Poly Texture Leaf)

Created **2025-12-07**. Optimized for low polygon count to be used as a texture container for leaf images.

### Geometry Stats

- **5 vertices, 1 face** (single n-gon)
- **34 nodes, 40 links**

### Parameters (6 parameters)

| Socket | Parameter | Type | Default | Range | Description |
|--------|-----------|------|---------|-------|-------------|
| Socket_2 | Length | Float | 1.0 | 0.1-5.0 | Length from base to tip |
| Socket_3 | Width | Float | 0.4 | 0.05-2.0 | Maximum width at widest point |
| Socket_4 | Tip Angle | Float | 30.0 | 5-90° | Sharpness of tip (lower = sharper) |
| Socket_5 | Base Angle | Float | 45.0 | 5-90° | Width at stem attachment (lower = narrower) |
| Socket_6 | Curve | Float | 0.0 | -1 to 1 | Bow/arch shape along length |
| Socket_7 | Side Angle | Float | 0.0 | -45 to 45° | Tilt of leaf sides relative to spine |

### Material: Leaf2DMaterial

Simple texture-ready material:

- **LeafTexture** - Image Texture node (drop your leaf image here)
- **UVMap** - UV coordinate input
- **FallbackColor** - Green color when no texture loaded
- Alpha clip enabled for transparency

### Data Flow

```
MeshCircle (5 vertices, NGON fill)
    ↓
ScaleLeaf (Transform)
    ├── Scale X: Width
    └── Scale Y: Length
    ↓
Position Analysis
    ├── Y normalized to 0-1
    └── X position for angle calculations
    ↓
Angle-Based Shaping
    ├── tan(BaseAngle) at base (Y=0)
    ├── tan(TipAngle) at tip (Y=1)
    └── Interpolated between
    ↓
Curve System
    └── Z = sin(π × Y) × Curve
    ↓
Side Angle System
    └── Z += |X| × tan(SideAngle)
    ↓
SetLeafPos → SetOffset → Output
```

### Usage

```python
import bpy
leaf = bpy.data.objects.get("2DLeaf")
mod = leaf.modifiers.get("Leaf2D")

mod["Socket_2"] = 1.2    # Length
mod["Socket_3"] = 0.5    # Width
mod["Socket_4"] = 20.0   # Tip Angle (sharp)
mod["Socket_5"] = 60.0   # Base Angle (wide base)
mod["Socket_6"] = 0.15   # Curve (slight bow)
mod["Socket_7"] = 15.0   # Side Angle (folded sides)

mod.show_viewport = False
mod.show_viewport = True
```

### Loading a Texture

```python
import bpy
mat = bpy.data.materials.get("Leaf2DMaterial")
tex_node = mat.node_tree.nodes.get("LeafTexture")

# Load your leaf image
img = bpy.data.images.load("/path/to/leaf_texture.png")
tex_node.image = img
```

---

## LeafBuilder (3D High-Detail Leaf)

Created **2025-12-06**. Full procedural leaf with geometry-based details.

### Geometry Stats

- **~200 vertices** (10×20 grid + extrusion)
- **42 nodes, 52 links**

### Geometry Node Parameters (9 parameters)

| Socket | Parameter | Type | Default | Range | Description |
|--------|-----------|------|---------|-------|-------------|
| Socket_2 | Width | Float | 0.4 | 0.05-2.0 | Maximum width of the leaf |
| Socket_3 | Length | Float | 1.0 | 0.1-5.0 | Length of the leaf from base to tip |
| Socket_4 | Tip Angle | Float | 30.0 | 5-90° | Sharpness of leaf tip (lower = sharper) |
| Socket_5 | Serration | Float | 0.0 | 0-1 | Edge smoothness (0=smooth, 1=jagged) |
| Socket_6 | Serration Count | Int | 8 | 3-30 | Number of serrations along edge |
| Socket_7 | Thickness | Float | 0.02 | 0.001-0.1 | Physical thickness of leaf |
| Socket_8 | Curvature | Float | 0.1 | -0.5-0.5 | Bowl/curl shape (+ = cupped, - = arched) |
| Socket_9 | Seed | Int | 0 | - | Random seed for variation |
| Socket_10 | Base Shape | Float | 0.3 | 0-1 | Sharpness of base where stem attaches (lower = sharper) |

### Material Parameters (Shader Nodes)

The **LeafMaterial** shader provides these adjustable color nodes:

| Node Name | Type | Default | Description |
|-----------|------|---------|-------------|
| DarkColor | RGB | (0.02, 0.08, 0.01) | Shadow/underside color |
| LightColor | RGB | (0.15, 0.4, 0.08) | Highlight/top color |
| VeinColor | RGB | (0.2, 0.35, 0.1) | Central rib and vein color |
| TopBottomRamp | ColorRamp | 0.3-0.7 | Controls top/bottom color blend |
| VeinRamp | ColorRamp | 0.4-0.6 | Sharpness of vein lines |
| RibPower | Math | 8.0 | Central rib thickness (higher = thinner) |
| RibStrength | Math | 0.3 | Central rib visibility |
| VeinStrength | Math | 0.15 | Secondary vein visibility |
| VeinWave Scale | Wave | 15.0 | Density of secondary veins |

---

## Architecture Overview

### Geometry Nodes: 42 nodes, 52 links

#### Leaf Shape Generation

```
LeafGrid (Mesh Grid)
    ├── Size Y: Length parameter
    ├── Vertices: 10 x 20
    ↓
GridOffset (Set Position)
    └── Shifts Y so leaf starts at origin (0 to Length)
    ↓
Position → SeparateXYZ → NormalizeY (Y / Length)
    ↓
Width Profile Calculation:
    ├── sin(π × t) for natural bulge
    ├── (1-t)^(90/TipAngle) for tip shape
    └── clamp(t/BaseShape)^0.5 for base cutoff
    ↓
Serration System:
    ├── sin(Index × frequency) for wave pattern
    └── Scale by Serration parameter
    ↓
SetLeafPosition
    ├── X: original X × width profile
    ├── Y: unchanged
    └── Z: X² × Curvature
    ↓
LeafSolidify (Extrude Mesh)
    └── Offset Z: Thickness parameter
    ↓
ShadeSmooth → SetLeafMaterial → Output
```

#### Key Width Formula

```
width_factor = sin(π × t) × (1 - t)^(90 / tip_angle)
```

Where `t` is normalized position along leaf (0 = base, 1 = tip).

- `sin(π × t)` creates natural widening then tapering
- `(1-t)^power` creates the pointed tip
- Lower tip angle = higher power = sharper tip

### Material Shader: 23 nodes

```
Geometry.Normal → SeparateZ → MapRange(-1,1 → 0,1)
    ↓
TopBottomRamp (ColorRamp)
    ↓
BaseColorMix
    ├── A: DarkColor (underside)
    └── B: LightColor (topside)
    ↓
ColorWithVeins
    ├── Factor: RibStrength + VeinStrength
    └── B: VeinColor
    ↓
LeafBSDF (Principled BSDF)
    ├── Base Color: ColorWithVeins output
    ├── Roughness: 0.4
    ├── Subsurface: 0.3 (translucency)
    └── Normal: VeinBump
    ↓
Material Output
```

#### Rib System

Central midvein using X distance from center:

```
|X - 0.5| → Invert → Power(8) → × RibStrength
```

#### Vasculature System

Secondary veins using Wave Texture:

```
WaveTexture(Diagonal Bands, Scale=15) → VeinRamp → × VeinStrength
```

---

## Usage

### Test Commands

```python
import bpy
leaf = bpy.data.objects.get("Leaf")
mod = leaf.modifiers.get("LeafBuilder")

# Maple-like leaf
mod["Socket_2"] = 0.6    # Width
mod["Socket_3"] = 0.8    # Length
mod["Socket_4"] = 20.0   # Tip Angle (sharp)
mod["Socket_5"] = 0.7    # Serration (jagged)
mod["Socket_6"] = 15     # Serration Count
mod["Socket_8"] = 0.1    # Curvature

# Oak-like leaf
mod["Socket_2"] = 0.4    # Width
mod["Socket_3"] = 1.0    # Length
mod["Socket_4"] = 40.0   # Tip Angle (rounder)
mod["Socket_5"] = 0.3    # Serration (mild)
mod["Socket_6"] = 8      # Serration Count
mod["Socket_8"] = 0.05   # Curvature

# Force update
mod.show_viewport = False
mod.show_viewport = True
```

### Adjusting Colors

```python
import bpy
mat = bpy.data.materials.get("LeafMaterial")
nodes = mat.node_tree.nodes

# Change to autumn colors
nodes["DarkColor"].outputs[0].default_value = (0.3, 0.1, 0.02, 1.0)  # Brown
nodes["LightColor"].outputs[0].default_value = (0.8, 0.4, 0.1, 1.0)  # Orange
nodes["VeinColor"].outputs[0].default_value = (0.5, 0.2, 0.05, 1.0)  # Dark orange
```

---

## Future Enhancements

### Priority 1: Lobed Leaves

- Add lobe count parameter
- Modulate width profile with additional sine waves
- Support maple, oak, fig leaf shapes

### Priority 2: Asymmetry

- Random variation per side
- Damage/insect bite holes

### Priority 3: Petiole (Stem)

- Add stem attachment point
- Stem curve and thickness

### Priority 4: Texture Maps

- Support for photo-based vasculature textures
- Normal map input for realistic surface detail

---

## Key Files

| File | Purpose |
|------|---------|
| 3DLeaf object | High-detail leaf in "Leaves" collection |
| 2DLeaf object | Low-poly texture leaf in "Leaves" collection |
| LeafBuilder | Geometry node group for 3D leaf |
| Leaf2D | Geometry node group for 2D leaf |
| LeafMaterial | Shader for 3D leaf (procedural veins) |
| Leaf2DMaterial | Shader for 2D leaf (texture-based) |
| docs/LEAFBUILDER_HANDOFF.md | This document |

---

## Session History

### 2025-12-07 (Session 2)

- ✅ Created Leaf2D geometry nodes (34 nodes) for low-poly leaves
- ✅ 5 vertices, 1 face - minimal polygon count
- ✅ Added Length, Width, Tip Angle, Base Angle, Curve, Side Angle parameters
- ✅ Created Leaf2DMaterial with Image Texture node for custom textures
- ✅ Alpha clip enabled for transparency support
- ✅ Renamed original leaf object to 3DLeaf
- ✅ Updated documentation to cover both systems

### 2025-12-06 (Session 1)

- ✅ Created LeafBuilder geometry nodes (38 nodes)
- ✅ Implemented width profile with tip angle control
- ✅ Added serration/jagged edge system
- ✅ Added curvature for bowl/curl shape
- ✅ Added thickness via extrusion
- ✅ Created LeafMaterial shader (23 nodes)
- ✅ Implemented top/bottom color gradient
- ✅ Added central rib (midvein)
- ✅ Added secondary vasculature with wave texture
- ✅ Added subsurface scattering for translucency
- ✅ Added bump mapping from veins
- ✅ Added Base Shape parameter for stem attachment area
