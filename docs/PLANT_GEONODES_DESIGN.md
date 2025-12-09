# Plant Geometry Nodes System Design

## Overview

A modular geometry nodes system for generating plants with multiple trunks, branching generations, and attachable meshes (leaves, flowers, buds, thorns).

## Design Principles

1. **Modular** - Separate node groups for each concern
2. **Generation-aware** - Track branch generation (0=trunk, 1=primary branch, etc.)
3. **Mesh-agnostic** - Accept any mesh for leaves/flowers via object inputs
4. **Predictable** - Same seed = same result

## Node Group Hierarchy

```
PlantGenerator (main)
├── TrunkDistributor
│   └── Stalk (reusable)
├── BranchGenerator (recursive-ish)
│   └── Stalk (reusable)  
└── MeshInstancer
    └── Per-generation mesh placement
```

## Interface Design

### PlantGenerator (Main Group)

**Inputs:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| Geometry | Geometry | - | Base mesh (soil/pot) |
| Trunk Count | Int | 1 | Number of main trunks |
| Trunk Height | Float | 0.5 | Height of trunks |
| Trunk Radius | Float | 0.02 | Base thickness |
| Branches Per Level | Int | 3 | Branches spawned per parent |
| Branch Generations | Int | 2 | Recursion depth (0-3) |
| Branch Length Ratio | Float | 0.6 | Child length vs parent |
| Branch Angle | Float | 45° | Angle from parent |
| Chaos | Float | 0.2 | Randomness (0=uniform, 1=wild) |
| Gravity | Float | 0.1 | Droop factor |
| Seed | Int | 0 | Random seed |
| Gen 0 Mesh | Object | None | Mesh for trunk tips |
| Gen 1 Mesh | Object | None | Mesh for primary branches |
| Gen 2 Mesh | Object | None | Mesh for secondary branches |
| Gen 3 Mesh | Object | None | Mesh for tertiary branches |

**Outputs:**

| Name | Type | Description |
|------|------|-------------|
| Geometry | Geometry | Complete plant + base |

## Implementation Strategy

### Challenge: No True Recursion in Geometry Nodes

Geometry Nodes doesn't support recursive node groups. We have two options:

**Option A: Repeat Zone (Blender 4.0+)**

- Use a Repeat Zone with generation counter
- Store branch endpoints as points with attributes
- Each iteration: spawn new branches from previous endpoints
- Pros: True iteration, clean
- Cons: Complex attribute management

**Option B: Nested Node Groups (Manual Unrolling)**

- Create separate groups: Gen0Branches, Gen1Branches, Gen2Branches, Gen3Branches
- Each calls the next explicitly
- Pros: Easier to debug, explicit control
- Cons: Max 4 generations hardcoded

### Chosen Approach: Hybrid

Use **Repeat Zone** for the branch generation loop, with a max of 4 iterations.
Store branch data as point cloud with attributes:

- `generation` (int): Which generation this branch belongs to
- `parent_direction` (vector): Direction of parent branch for angle calculation
- `length` (float): This branch's length
- `radius` (float): This branch's radius

## Data Flow

```
1. Input Geometry (soil plane)
   ↓
2. TrunkDistributor
   - Distributes N points at origin (or on surface)
   - Each point = trunk base
   - Output: Points with trunk attributes
   ↓
3. Repeat Zone (Branch Generations)
   Iteration 0: Grow trunks from distributed points
   Iteration 1: Grow branches from trunk endpoints  
   Iteration 2: Grow sub-branches from branch endpoints
   Iteration 3: Grow twigs from sub-branch endpoints
   
   Each iteration:
   a. Read current endpoints (points with generation=N-1)
   b. For each endpoint, spawn K new points (branches)
   c. Apply angle, length ratio, chaos, gravity
   d. Create curve geometry for new branches
   e. Store new endpoints with generation=N
   ↓
4. Curve to Mesh (all branches)
   ↓
5. MeshInstancer
   - Read endpoint points
   - Filter by generation attribute
   - Instance appropriate mesh per generation
   ↓
6. Join: Soil + Branches + Leaves/Flowers
   ↓
7. Output
```

## Key Nodes to Investigate

Before building, need to verify these work as expected in Blender 5.0:

- [ ] `GeometryNodeRepeatZone` - for generation loop
- [ ] `GeometryNodeStoreNamedAttribute` - for generation tracking
- [ ] `GeometryNodeCaptureAttribute` - for storing endpoint data
- [ ] `GeometryNodeInstanceOnPoints` - for mesh placement
- [ ] `GeometryNodeObjectInfo` - for reading external mesh objects
- [ ] `GeometryNodeInputIndex` - for per-branch variation

## Phase 1: Minimal Viable Plant

Start simple:

1. Single trunk (no distribution yet)
2. One generation of branches (3-5 branches)
3. No mesh instancing yet
4. Basic gravity/droop

This validates the branch spawning approach before adding complexity.
