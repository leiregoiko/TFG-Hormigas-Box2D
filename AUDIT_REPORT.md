# AUDIT REPORT — AntsLeire_v0 Simulation Project

> Incremental report. Each section is timestamped. New findings are appended as the project evolves.

---

## Report 1: Initial Audit of `box2d.qmd` — 2026-03-02

### 1. THE THREAD — What This File Is

This is Leire Goikoetxea's **TFG (Bachelor's Thesis) simulation notebook** — a progressive, exploratory journal where she learns Box2D physics from scratch and builds toward a 2D simulation of **ant cooperative transport through constrained environments** (mazes with narrow slits).

The file is a **Quarto notebook** (.qmd) with 17 executable Python code blocks, written in a mix of Spanish and Basque (Euskara), evolving from "hello world" gravity tests to a working swarm simulation.

---

### 2. THE ARGUMENT LINE — The Story in Sequence

#### Act I: Learning the Physics Engine (blocks 1–3, lines 1–236)

- **Block 1**: Pure Box2D + matplotlib. A box falls under gravity (g = -10). First contact with the engine: world creation, static body (ground), dynamic body, time-stepping loop. Plots y-position over time.
- **Block 2**: Introduces Pygame for real-time visualization. Creates a T-shaped composite body (two polygon fixtures on one body) falling with gravity. Learns `b2PolygonShape.SetAsBox` with offsets.
- **Block 3**: Student experimentation — adds triangles, circles (`b2CircleShape`), a second dynamic body. Learning fixture variety.

#### Act II: Building the Arena (blocks 4–5, lines 241–377)

- **Block 4**: **Critical conceptual leap** — switches to `gravity=(0,0)`. This is now a **top-down view** ("goitik begiratzen ari garela" — we're looking from above). Creates a single-slit arena with a T-shaped cargo ("el Piano"). This is the first real prototype of the experimental setup.
- **Block 5**: Custom maze built to match **article dimensions** (x10, in meters). Two slits at x=16.15 and x=23.95, slit width 4.7m, wall thickness 1.2m. Arena 40m × 24m. The student is replicating a real experiment's geometry.

#### Act III: Forces and Control (blocks 6–7, lines 381–518)

- **Block 6**: Explanatory block. Discovers the difference between:
  - `ApplyForce` (world-frame, like wind)
  - `GetWorldVector` + `ApplyForce` (body-frame, attached to the object — "like an ant pushing")
  - `ApplyForceToCenter` (no torque) vs. `ApplyForce` at a point (generates torque)
- **Block 7**: First test — applies a rotation-causing force at the T's top plus a center-push. The T spins and translates. This is the foundation for ant-driven motion.

#### Act IV: The Swarm (blocks 8–12, lines 521–801)

- **Block 8–9**: Creates 15 ants as small circles (r=0.2m), randomly placed. Adds circle rendering to the draw loop.
- **Block 10**: First complete simulation — ants feel an **attractive force toward the T** (`f_c = pos_t - pos_h`) plus a rightward exit bias (`salida`). This is the "attracted particle model."
- **Block 11**: Random vibration forces for Brownian-like exploration.
- **Block 12**: Adds `linearDamping = 2.0` as a friction proxy. Combines attraction + exit force.

#### Act V: Contact-Based Intelligence (blocks 13–17, lines 803–1416)

- **Block 13–14**: **Key breakthrough** — switches from distance-based to **contact-based** behavior. Uses `h.contacts` list and `contacto.other == carga` to detect when an ant actually touches the cargo. Ants change color (red=searching, green=pushing). Two behavioral states emerge:
  - **Searching**: attracted toward cargo (f_c)
  - **Pushing**: pushes toward exit (f_total)
- **Block 15**: Refines push direction to aim at the **slit center** (x=20, y=17.5), not just rightward. But discovers the force vanishes near the center itself.
- **Block 16**: **Final force model**: decomposes the push into `fuerza_ok = b2Vec2(3*fx, fy)` where fy corrects altitude toward slit center and fx is a constant rightward push. Reports: "MODU HONETAN BETI BETI ATERATZEN DA" — it always passes through.
- **Block 17**: Scales up to the full **two-slit maze** with article dimensions, 20 ants, refined forces. The final working simulation before deciding to continue in a new file.

---

### 3. PACKAGE AUDIT

#### Box2D (pybox2d)

| Feature Used | How | Assessment |
|---|---|---|
| `b2World(gravity=)` | World with g=0 (top-down) | Correct |
| `CreateStaticBody` | Walls, ground | Correct |
| `CreateDynamicBody` | T-cargo, ants | Correct |
| `CreatePolygonFixture(box=)` | Rectangles with offsets | Correct |
| `b2PolygonShape.SetAsBox` | Offset sub-shapes for T | Correct |
| `b2CircleShape(radius=)` | Ant bodies | Correct |
| `CreatePolygonFixture(shape=circulo)` | **BUG** — uses PolygonFixture for circles | Should be `CreateCircleFixture` or `CreateFixture` |
| `ApplyForce / ApplyForceToCenter` | Ant forces | Correct |
| `GetWorldPoint / GetWorldVector` | Local-to-world transforms | Correct, well understood |
| `b2Vec2` | Vector arithmetic | Correct |
| `h.contacts` / `contacto.other` | Contact detection | Correct |
| `linearDamping` | Friction proxy | Correct conceptually |
| `mundo.Step(dt, vel_iters, pos_iters)` | Time stepping | **BUG**: called TWICE per frame in block 17 |

#### Pygame

| Feature Used | Assessment |
|---|---|
| Window, event loop, clock | Standard, correct |
| Polygon/circle drawing | Correct |
| `to_pygame()` coordinate transform | Correct (flips y-axis) |
| No `pygame.quit()` safety | Minor — no try/finally |

#### Matplotlib

- Used only in block 1 for static plotting. Standard and correct.

#### random

- `random.uniform()` for ant positions. Correct but **no seed set** — simulations are not reproducible.

---

### 4. FINDINGS — Gaps and Issues

#### A. Technical Bugs

1. **`CreatePolygonFixture` with `b2CircleShape`**: The code passes a `b2CircleShape` to `CreatePolygonFixture`. This works by accident in pybox2d (it auto-detects the shape type), but it is semantically wrong and confusing. Should use `CreateFixture` with a `fixtureDef` or `CreateCircleFixture`.

2. **Double `mundo.Step()` per frame** (block 17, lines 1376 and 1411): The physics is advanced twice per rendered frame, effectively doubling the simulation speed and altering the physics. This breaks the time-step consistency.

3. **No random seed**: Every run produces different ant positions. Makes results non-comparable. Should use `random.seed(42)` or similar for reproducibility.

4. **Hard-coded magic numbers everywhere**: PPM=20, force magnitudes (3, 7, 10), damping values (2.0, 3.0, 10.0), positions — none parametrized. Makes systematic study impossible.

#### B. Physics Model Gaps

5. **Ants have global knowledge**: Every ant knows the slit position (`salida = b2Vec2(20, 19)`) and pushes toward it when touching cargo. Real ants don't have this information. This is the **biggest conceptual gap** — the simulation proves that if agents know the exit, collective transport works, but doesn't explore *how* they discover it.

6. **No information-sharing mechanism**: There is no pheromone trail, no stigmergy, no chemical signaling, no antenna-contact communication. The swarm intelligence is entirely pre-programmed, not emergent.

7. **No rotational strategy**: Real ants rotate cargo to fit through gaps (this is a key finding in the literature — Feinerman et al.). The T-shape is designed to require rotation, but the force model doesn't explicitly address it. Rotation happens accidentally from asymmetric force application.

8. **No ant-ant interaction**: Ants don't repel, attract, or communicate with each other. They only interact with the cargo and walls. In reality, crowding, obstruction, and recruitment are critical.

9. **No noise/stochasticity in pushing**: Once touching, every ant pushes in the exact same computed direction. Real ants push somewhat randomly, and the collective averaging is what produces the "correct" direction. The **fluctuation-driven exploration** that makes real ant transport work is absent.

10. **`linearDamping` as friction proxy**: This applies viscous drag proportional to velocity, simulating a low-Reynolds-number environment (appropriate for small creatures on a surface). However, the values are arbitrary and change abruptly between states. In a real model, this should be calibrated to actual ant-surface friction data.

#### C. Structural Gaps

11. **No data collection**: No position logging, no time-to-passage measurement, no angle tracking, no force statistics. The simulation runs visually but produces no quantitative output.

12. **No parametric sweeps**: Number of ants, slit width, cargo shape, force magnitudes — nothing is varied systematically. A single configuration is tested.

13. **No termination condition**: Simulations run until the user closes the window. There's no detection of "cargo passed through slit" to stop and measure.

14. **No separation of model and visualization**: Physics and rendering are interleaved in the same loop. This makes it hard to run headless batch simulations for statistics.

---

### 5. THE ACHIEVEMENT

Despite these gaps, the notebook achieves something significant: **a working 2D cooperative transport simulation built from scratch**, progressing from zero knowledge of Box2D to a multi-agent contact-based force model that successfully navigates a T-shaped cargo through a double-slit maze. The learning curve is visible and honestly documented. The student demonstrates:

- Understanding of rigid body physics (forces, torques, fixtures)
- Understanding of body-frame vs. world-frame transformations
- Contact detection for behavioral state switching
- Force decomposition (lateral correction + forward thrust)
- Progressive refinement through experimentation

---

### 6. THREE APPLICATIONS TO PHYSICAL PROBLEMS

#### Application 1: Micro-Drone Swarm for Targeted Drug Delivery

The contact-based force model (search → attach → push) maps directly to **micro-scale robotic drug delivery**. A swarm of micro-drones (10–100 μm) could collectively transport a therapeutic payload through blood vessels or tissue:

- **The slit = biological barrier** (blood-brain barrier, tumor wall, arterial narrowing)
- **The T-cargo = drug payload** too large for any single micro-drone to carry
- **Contact-based switching** = drones only push when physically docked to the payload
- **Lateral correction + forward thrust** = the exact force decomposition needed to navigate through constrained vasculature
- **Key insight from this simulation**: you don't need individual drones to know the full path — local contact sensing + a bias toward flow direction is sufficient. The stochastic attachment/detachment creates a self-correcting swarm that adjusts the payload orientation automatically.
- **What this simulation needs to prove it**: add noise to the pushing direction, remove global exit knowledge, add a chemical gradient (blood flow direction) as the only directional cue.

#### Application 2: Storm-Tracking Drone Swarm with Distributed Sensing

The collective transport metaphor translates to **information transport**: instead of moving a physical object, the "cargo" is a **shared information state** (storm position estimate) and the "slits" are **decision thresholds**:

- Each drone measures local atmospheric conditions (pressure, wind, humidity)
- Drones in "contact" with the storm (inside the phenomenon) contribute measurements weighted by their confidence
- Drones outside "search" — explore to find the storm boundary
- **The force model becomes a consensus protocol**: `f_total = (local_measurement - group_estimate) + bias_toward_storm_center`
- **The dual damping** (high when attached, low when searching) maps perfectly to **exploration-exploitation trade-off** in distributed sensing
- **This simulation's finding that "BETI ATERATZEN DA" (it always passes through)** suggests that a drone swarm using contact-based consensus + directional bias would reliably track a moving storm, even with limited individual sensing range
- **What this needs**: replace physical forces with information-theoretic forces (gradient of uncertainty), the "slit" becomes the decision boundary where the swarm must collectively agree to shift tracking direction

#### Application 3: Collective Manipulation in Zero-G Space Debris Removal

This simulation is literally a **zero-gravity multi-agent manipulation problem** — exactly what space debris removal requires:

- **g = 0 arena = orbital environment**
- **T-shaped cargo = irregularly shaped debris** (spent rocket stages, broken satellite panels)
- **Ants = small service satellites or robotic arms on a mothership**
- **Slits = safe corridors** for deorbiting debris without creating collision cascades
- The contact-based two-state model (approach → dock → push) is the standard architecture for planned multi-spacecraft capture missions (ESA's ClearSpace-1 concept), but this simulation shows it can work with **simpler, swarm-based agents**
- **The force decomposition** (constant deorbit thrust + lateral correction toward safe corridor center) directly translates to orbital maneuver design
- **Critical finding from this simulation**: even with a naive force model, 15–20 agents reliably navigate an awkward shape through a narrow gap. This suggests small satellite swarms could handle debris removal without complex centralized planning
- **What this needs**: add orbital mechanics (not just zero-g but Keplerian dynamics), communication delays, fuel constraints (finite force budget per agent)

---

### 7. SUMMARY TABLE

| Aspect | Status | Priority |
|---|---|---|
| Box2D usage | Functional, 2 bugs | Fix double-step + fixture type |
| Force model | Works but has global knowledge | High — needs local-only information |
| Data collection | Absent | Critical for thesis |
| Reproducibility | No seed | Quick fix |
| Parametric study | Absent | Critical for thesis |
| Biological realism | Low (no communication, no noise) | Medium — depends on thesis scope |
| Code structure | Monolithic, magic numbers | Refactor for batch runs |
| Visualization | Good for debugging | Add trajectory recording |

---

*End of Report 1*

---

## Report 2: v0 Consolidation — 2026-03-02

### Action Taken

The original `box2d.qmd` (1,492 lines, 17 code blocks) was preserved as `box2d_original.qmd` and replaced with a clean, perfected v0 (514 lines, 6 Quarto sections, 1 definitive simulation).

### Files After This Step

| File | Lines | Purpose |
|---|---|---|
| `box2d_original.qmd` | 1,492 | Original exploration journal — preserved untouched as starting point |
| `box2d.qmd` | 514 | Perfected v0 — clean, documented, bug-free, ready for iteration |
| `AUDIT_REPORT.md` | — | This incremental report |

### All Fixes Applied

| # | Original Problem | Fix Applied |
|---|---|---|
| 1 | `CreatePolygonFixture` used for `b2CircleShape` objects | Changed to `CreateFixture(shape=circle_shape, density=..., friction=...)` — semantically correct |
| 2 | `mundo.Step()` called TWICE per frame (block 17, lines 1376 + 1411) | Single `world.Step()` call per frame, placed after force application, before rendering |
| 3 | No random seed — results non-reproducible | `random.seed(42)` added; `RANDOM_SEED` as named constant |
| 4 | 40+ hard-coded magic numbers scattered through code | All extracted to named constants in a single configuration section with physical descriptions |
| 5 | Contact detection logic duplicated (once in physics loop, once in render loop) | Single `is_touching_cargo()` function, called by both `compute_ant_force()` and `draw_world()` |
| 6 | Rendering and physics interleaved in one monolithic loop | Clean separation: `draw_world()` function handles all rendering; main loop is: events → forces → step → draw |
| 7 | Mixed Spanish/Basque/informal comments, no consistency | Consistent bilingual documentation (Euskara + English) in all section headers and notes |
| 8 | 17 code blocks of incremental experiments, many obsolete | 1 definitive simulation across 6 well-named Quarto sections: Config → World → Walls → Cargo → Ants → Simulation |
| 9 | No docstrings on any function | Full docstrings on `is_touching_cargo()`, `compute_ant_force()`, `to_screen()`, `draw_world()` |
| 10 | No output on simulation end | Prints final cargo position, angle, and total frame count on exit |
| 11 | Slit geometry computed inline with raw numbers | Derived values (`SLIT_WALL_HALF_HEIGHT`, `SLIT_WALL_BOTTOM_CENTER_Y`, etc.) computed from parameters |
| 12 | Variable names inconsistent (mix of Spanish/English) | Consistent English variable names throughout (`world`, `cargo`, `ants`, `walls`) |
| 13 | No Quarto metadata beyond title | Added subtitle, author, date, code-tools, toc-depth, number-sections |
| 14 | Known limitations undocumented | Explicit "Known limitations" section listing all 6 major gaps for future work |

### What Was NOT Changed (by design)

These are **model-level gaps** identified in Report 1 that require new features, not fixes. They define the roadmap for future versions:

1. **Global knowledge** — ants still know the slit position. Replacing this with local-only information (pheromones, gradients) is a v1+ feature.
2. **No stochasticity** — push direction remains deterministic. Adding noise to the force model is a v1+ feature.
3. **No data collection** — no position/angle logging. Adding CSV/trajectory export is a v1+ feature.
4. **No parametric sweeps** — single configuration. Adding batch runs over ant count, slit width, etc. is a v1+ feature.
5. **No ant-ant interaction** — no repulsion, crowding, or recruitment. This is a v2+ feature.
6. **No information-sharing mechanism** — no pheromones, no stigmergy. This is a v2+ feature.

### Architecture of the v0

```
box2d.qmd (514 lines)
│
├── Section 1: Configuration (all parameters)
│   └── Single cell: imports, constants, derived values
│
├── Section 2: World Creation
│   └── b2World(gravity=(0,0))
│
├── Section 3: Walls and Slits
│   └── 8 fixtures: 4 outer walls + 4 slit segments
│
├── Section 4: Cargo (T-shape)
│   └── 3 fixtures: stem + top bar + bottom bar
│
├── Section 5: Force Model
│   ├── is_touching_cargo(ant, cargo) → bool
│   └── compute_ant_force(ant, cargo) → (force, is_pushing)
│
└── Section 6: Simulation Loop
    ├── to_screen(point) → (px, py)
    ├── draw_world(world, screen, cargo)
    └── Main loop: events → forces → step → draw
```

---

*End of Report 2*

---

## Report 3: v1 Design — Pheromone-Based Ant Colony with Explorers and Workers — 2026-03-02

### 1. SORTED IDEAS

#### 1.1 Two Ant Castes

| Caste | Role | Behavior |
|---|---|---|
| **Explorers** (Esploratzaileak) | Scout the surroundings, find food, lay pheromone trails | Leave colony, explore randomly, mark paths, detect food, signal back |
| **Workers** (Langileak) | Transport food back to the colony | Stay near colony until signaled, follow pheromone trails to food, carry food back |

#### 1.2 The Arena — Now a Foraging Landscape

The v0 double-slit maze transforms into a **foraging world**:

- **Colony** (Habia): a fixed zone on one side — the nest, origin of all ants
- **Food sources**: one or more deposits placed far from the colony
- **Obstacles**: static bodies that block direct paths — ants must navigate around them. The **gaps between obstacles** are the new "slits"
- **Open terrain**: the rest of the arena, where pheromones are deposited and decay

#### 1.3 Pheromone System — Two Types

| Pheromone | Emitted by | Meaning | When |
|---|---|---|---|
| **Type A: "Exploration"** (Esplorazio-feromona) | Explorers while exploring | "I have been here" — trail maintenance | Continuously while searching, diminishing emission rate over time |
| **Type B: "Food found"** (Janari-feromona) | Explorers returning with food location | "Follow me to food" — recruitment signal | After finding food, on the return trip to colony |

#### 1.4 Pheromone Dynamics — Three Time Parameters

```
EMISSION:
  - Rate diminishes with time since last "refueling" at colony
  - P_emission(t) = P_max * exp(-t / τ_emission)
  - τ_emission = parametrized decay constant for emission capacity
  - When P_emission drops below REFUEL_THRESHOLD, explorer returns to colony to refuel

PERSISTENCE (on the ground):
  - Deposited pheromone decays in place
  - P_ground(t) = P_deposited * exp(-t / τ_persistence)
  - τ_persistence = parametrized lifetime of pheromone on the ground
  - Does NOT propagate (v1 simplification) — stays where deposited

DETECTION:
  - Ants detect pheromone within DETECTION_RADIUS
  - Detection is binary at threshold: sensed if P_ground > DETECTION_THRESHOLD
  - Affects both explorers (avoid retracing) and workers (follow trails)
```

#### 1.5 Behavioral State Machine

**Explorer Ant States:**

```
EXPLORE_OUTBOUND
  │  Leaves colony, moves randomly, deposits Type A pheromone
  │  Emission rate decays with time
  │
  ├── IF emission capacity < REFUEL_THRESHOLD
  │   └── → EXPLORE_RETURN_REFUEL (go back to colony, refuel, restart)
  │
  ├── IF detects food
  │   └── → FOOD_FOUND
  │
  └── IF detects fading Type A from others
      └── Re-deposits (trail maintenance)

FOOD_FOUND
  │  Switches pheromone to Type B
  │  Some explorers stay near food (FOOD_MARKER state)
  │  Others begin return trip
  │
  ├── → FOOD_MARKER (stays at food, emits strong Type B beacon)
  └── → EXPLORE_RETURN_FOOD (returns to colony, deposits Type B trail)

EXPLORE_RETURN_FOOD
  │  Heads back to colony depositing Type B pheromone
  │  This creates the recruitment trail
  │
  └── IF reaches colony
      └── → EXPLORE_OUTBOUND (cycle restarts, or switches role)

EXPLORE_RETURN_REFUEL
  │  Heads back to colony (no special pheromone, just going home)
  │
  └── IF reaches colony
      └── → EXPLORE_OUTBOUND (emission capacity reset)
```

**Worker Ant States:**

```
WORKER_IDLE
  │  Stays near colony / wanders locally
  │
  ├── IF detects Type B pheromone
  │   └── → WORKER_TO_FOOD
  │
  └── IF detects returning explorer (physical contact or strong Type B)
      └── → WORKER_TO_FOOD

WORKER_TO_FOOD
  │  Follows Type B pheromone gradient toward food
  │  Navigates around obstacles using the reinforced trails
  │
  └── IF reaches food
      └── → WORKER_CARRYING

WORKER_CARRYING
  │  Picks up food, heads back to colony
  │  Deposits Type B pheromone (reinforcing the trail for others)
  │  Must navigate obstacles — the "slits" from v0
  │
  └── IF reaches colony
      └── → WORKER_IDLE (food delivered, cycle complete)
```

#### 1.6 The Arena Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   ┌─────┐                                                       │
│   │     │          ┌───┐                                        │
│   │ COL │          │OBS│         ┌───┐                          │
│   │ ONY │          │ 1 │         │OBS│        ┌──────┐          │
│   │     │          └───┘         │ 2 │        │ FOOD │          │
│   │  H  │                        └───┘        │  ★   │          │
│   │     │    ┌──────┐                         └──────┘          │
│   │     │    │ OBS  │       ┌───┐                               │
│   └─────┘    │  3   │       │OBS│                               │
│              └──────┘       │ 4 │                               │
│                             └───┘                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

  Colony (left)  ──→  Obstacles create narrow passages  ──→  Food (right)
                       (the "slits" emerge naturally)
```

#### 1.7 Pheromone Grid — Implementation Approach

The pheromone field lives on a **discrete grid** overlaid on the continuous Box2D world:

```
- Grid resolution: PHEROMONE_CELL_SIZE (e.g., 0.5m per cell)
- Grid dimensions: (ARENA_WIDTH / CELL_SIZE) × (ARENA_HEIGHT / CELL_SIZE)
- Two layers: grid_type_A[x][y] and grid_type_B[x][y]
- Each cell stores: intensity (float), timestamp of last deposit
- Per frame: all cells decay by factor exp(-dt / τ_persistence)
- When ant deposits: cell intensity += emission_amount
- When ant senses: read cells within DETECTION_RADIUS, follow gradient
```

---

### 2. FLOW — Execution Order per Frame

```
FRAME START
│
├── 1. EVENT HANDLING
│   └── Pygame events (quit, keyboard)
│
├── 2. PHEROMONE DECAY
│   └── For all grid cells: intensity *= exp(-dt / τ_persistence)
│   └── (Optimization: skip cells below EPSILON)
│
├── 3. ANT BEHAVIOR (for each ant)
│   │
│   ├── 3a. SENSE environment
│   │   └── Read pheromone grid within DETECTION_RADIUS
│   │   └── Check contacts (food? colony? obstacles? cargo?)
│   │
│   ├── 3b. DECIDE next action (state machine transition)
│   │   └── Based on current state + sensed info → new state
│   │
│   ├── 3c. ACT
│   │   └── Compute force vector based on state
│   │   └── Apply force to ant body
│   │   └── Deposit pheromone at current position
│   │
│   └── 3d. UPDATE internal variables
│       └── Emission capacity decay
│       └── Timer updates
│
├── 4. PHYSICS STEP
│   └── world.Step(dt, vel_iters, pos_iters)
│
├── 5. RENDER
│   ├── Draw pheromone heatmap (Type A = light blue, Type B = yellow)
│   ├── Draw obstacles (green)
│   ├── Draw colony (white/gold)
│   ├── Draw food (bright star)
│   ├── Draw ants (colored by state)
│   └── Draw HUD (frame count, ants by state, food delivered)
│
└── FRAME END
```

---

### 3. PSEUDOCODE — Complete v1

```python
# ================================================================
# CONFIGURATION
# ================================================================

# --- Arena ---
ARENA_WIDTH = 80.0          # Bigger arena for foraging
ARENA_HEIGHT = 50.0
WALL_THICKNESS = 1.0

# --- Colony ---
COLONY_X, COLONY_Y = 8.0, 25.0
COLONY_RADIUS = 3.0          # Circular zone

# --- Food ---
FOOD_X, FOOD_Y = 70.0, 25.0
FOOD_RADIUS = 2.0
FOOD_AMOUNT = 100            # Units of food available

# --- Obstacles (create the "natural slits") ---
OBSTACLES = [
    {"x": 25, "y": 15, "w": 3, "h": 8},
    {"x": 25, "y": 38, "w": 3, "h": 6},
    {"x": 45, "y": 22, "w": 4, "h": 10},
    {"x": 45, "y": 40, "w": 3, "h": 5},
    {"x": 55, "y": 10, "w": 6, "h": 3},
]

# --- Ants ---
NUM_EXPLORERS = 10
NUM_WORKERS = 15
ANT_RADIUS = 0.3
ANT_MAX_SPEED = 5.0

# --- Pheromone emission ---
P_MAX_EMISSION = 1.0
TAU_EMISSION = 30.0
REFUEL_THRESHOLD = 0.1
DEPOSIT_PER_STEP = 0.05

# --- Pheromone persistence ---
TAU_PERSISTENCE_A = 60.0
TAU_PERSISTENCE_B = 120.0
DETECTION_THRESHOLD = 0.01
DETECTION_RADIUS = 2.0

# --- Pheromone grid ---
PHEROMONE_CELL_SIZE = 0.5
GRID_W = int(ARENA_WIDTH / PHEROMONE_CELL_SIZE)
GRID_H = int(ARENA_HEIGHT / PHEROMONE_CELL_SIZE)

# --- Force model ---
EXPLORE_FORCE = 8.0
FOLLOW_GRADIENT_FORCE = 12.0
HOMING_FORCE = 10.0
FOOD_ATTRACTION = 10.0
DAMPING_FREE = 3.0
DAMPING_CARRYING = 8.0

# --- Colors ---
COLOR_EXPLORER_OUTBOUND = (52, 152, 219)    # Blue
COLOR_EXPLORER_FOOD = (241, 196, 15)        # Gold
COLOR_EXPLORER_REFUEL = (149, 165, 166)     # Gray
COLOR_FOOD_MARKER = (230, 126, 34)          # Orange
COLOR_WORKER_IDLE = (189, 195, 199)         # Light gray
COLOR_WORKER_GOING = (155, 89, 182)         # Purple
COLOR_WORKER_CARRYING = (46, 204, 113)      # Green
COLOR_PHEROMONE_A = (100, 180, 255, 80)     # Light blue
COLOR_PHEROMONE_B = (255, 255, 100, 120)    # Yellow
COLOR_COLONY = (255, 255, 255)              # White
COLOR_FOOD = (255, 215, 0)                  # Gold


# ================================================================
# DATA STRUCTURES
# ================================================================

class PheromoneGrid:
    """Discrete grid storing pheromone intensity for two types."""
    def __init__(self, width, height, cell_size): ...
    def deposit(self, world_x, world_y, pheromone_type, amount): ...
    def read(self, world_x, world_y, radius, pheromone_type): ...
    def decay(self, dt): ...
    def render(self, screen, to_screen_fn): ...

class Ant:
    """Individual ant with state machine, pheromone emission, force computation."""
    def __init__(self, body, caste): ...
    def sense(self, pheromone_grid, colony_pos, food_pos): ...
    def decide(self, sensed_data): ...
    def act(self, pheromone_grid): ...


# ================================================================
# INITIALIZATION
# ================================================================

world = b2World(gravity=(0, 0))
create_outer_walls(world)
for obs in OBSTACLES:
    create_obstacle(world, obs)
colony_sensor = create_sensor(world, COLONY_X, COLONY_Y, COLONY_RADIUS)
food_sensor = create_sensor(world, FOOD_X, FOOD_Y, FOOD_RADIUS)
pheromone = PheromoneGrid(ARENA_WIDTH, ARENA_HEIGHT, PHEROMONE_CELL_SIZE)

ants = []
for i in range(NUM_EXPLORERS):
    body = spawn_ant_at(world, COLONY_X, COLONY_Y, ANT_RADIUS)
    ants.append(Ant(body, caste='explorer'))
for i in range(NUM_WORKERS):
    body = spawn_ant_at(world, COLONY_X, COLONY_Y, ANT_RADIUS)
    ants.append(Ant(body, caste='worker'))


# ================================================================
# MAIN LOOP
# ================================================================

food_delivered = 0

while running:
    dt = TIME_STEP
    handle_events()
    pheromone.decay(dt)

    for ant in ants:
        sensed = ant.sense(pheromone, colony_pos, food_pos)
        ant.decide(sensed)
        ant.act(pheromone)
        if ant.state == 'WORKER_IDLE' and ant.just_delivered:
            food_delivered += 1

    world.Step(dt, VEL_ITERATIONS, POS_ITERATIONS)

    screen.fill(COLOR_BACKGROUND)
    pheromone.render(screen, to_screen)
    draw_world(world, screen)
    draw_colony(screen, COLONY_X, COLONY_Y, COLONY_RADIUS)
    draw_food(screen, FOOD_X, FOOD_Y, FOOD_RADIUS, FOOD_AMOUNT)
    draw_ants(screen, ants)
    draw_hud(screen, frame_count, food_delivered, ants)
    pygame.display.flip()
```

---

### 4. IMPLEMENTATION ORDER

| Step | What | Why first |
|---|---|---|
| **S1** | `PheromoneGrid` class (deposit, decay, read, render) | Foundation — everything depends on it |
| **S2** | New arena: bigger, with colony zone, food zone, obstacles | The physical stage must exist before actors |
| **S3** | `Ant` class with state machine (explorer states only) | Explorers are the first actors; workers depend on explorer trails |
| **S4** | Explorer behavior: OUTBOUND + REFUEL cycle | Simplest loop — validates pheromone deposit + decay visually |
| **S5** | Food detection + FOOD_FOUND + RETURN_FOOD states | Completes the explorer lifecycle |
| **S6** | Worker behavior: IDLE + TO_FOOD + CARRYING cycle | Workers follow trails that now exist |
| **S7** | Data collection: CSV export of positions, states, food deliveries | Enables quantitative analysis |
| **S8** | Visualization polish: heatmap, ant colors, HUD | Makes the simulation legible |

### 5. KEY DESIGN DECISIONS

These are the choices made based on the specification. All are parametrized and changeable:

1. **Pheromone grid** (discrete cells) rather than particle-based — simpler, fast decay, easy gradient computation
2. **Exponential decay** for both emission capacity and ground persistence — physically natural, one parameter each
3. **Two pheromone types** (A=exploration, B=food-trail) stored on the same grid with separate layers
4. **Colony and food as sensor zones** (Box2D sensors: detect overlap but don't block movement)
5. **Obstacles as solid Box2D bodies** — ants must physically navigate around them, creating emergent "slits"
6. **Workers start idle at colony** — only activated by Type B pheromone detection or returning explorer contact
7. **Food markers** — some explorers stay at food to maintain a strong Type B beacon
8. **Arena ~4× larger than v0** (80×50 vs 40×24) — foraging needs distance

---

*End of Report 3*

---

## Report 4: v1 Implementation Complete — 2026-03-02

### File Created

`box2d_v1.qmd` — 926 lines, 7 Quarto sections, fully documented.

### Architecture

```
box2d_v1.qmd (926 lines)
│
├── Section 1: Configuration (all 50+ parameters)
│   └── Imports, seeds, arena, colony, food, obstacles, ants, pheromones, forces, colors
│
├── Section 2: PheromoneGrid class
│   ├── __init__: numpy arrays (grid_a, grid_b), precomputed decay factors
│   ├── deposit(wx, wy, ptype, amount)
│   ├── decay(): bulk numpy multiply per frame
│   ├── read_intensity(wx, wy, radius, ptype): sum in circular region
│   ├── read_gradient(wx, wy, radius, ptype): weighted direction toward higher concentration
│   └── render(surface, to_screen_fn): colored dot overlay
│
├── Section 3: World building
│   ├── b2World(gravity=(0,0))
│   ├── 4 outer walls
│   └── 5 obstacles (create natural passages)
│
├── Section 4: Colony + Food zones (Box2D sensors)
│
├── Section 5: Ant class (7 states)
│   ├── Explorer states: OUTBOUND → RETURN_REFUEL or FOOD_FOUND → FOOD_MARKER
│   ├── Worker states: IDLE → TO_FOOD → CARRYING → IDLE
│   ├── sense_decide_act(): unified per-frame method
│   ├── _random_wander_force(): smooth random walk (drifting angle)
│   ├── _clamp_speed(): velocity limiter
│   └── get_color(): state-dependent RGB
│
├── Section 6: Spawn ants at colony
│   ├── 10 explorers (3 designated as food markers)
│   └── 15 workers (start idle)
│
└── Section 7: Simulation loop
    ├── to_screen(), draw_static_world(), draw_zones(), draw_ants(), draw_hud()
    └── Main loop: events → decay → sense/decide/act → physics → render
```

### What v1 Implements vs Design (Report 3)

| Design Element | Status | Notes |
| --- | --- | --- |
| Two ant castes (explorer/worker) | Done | 10+15 default |
| 7-state state machine | Done | All transitions implemented |
| Pheromone Type A (exploration) | Done | Exponential emission decay + ground persistence |
| Pheromone Type B (food trail) | Done | Emitted on return, stronger, longer-lasting |
| Pheromone grid (numpy) | Done | 80×50 cells, two layers, bulk decay |
| Gradient sensing | Done | Weighted direction toward higher concentration |
| Trail maintenance | Done | Explorers re-deposit when local Type A is fading |
| Emission capacity decay | Done | exp(-dt/τ), refuels at colony |
| Food markers | Done | 30% of explorers stay at food as Type B beacons |
| Obstacles as natural slits | Done | 5 static bodies create narrow passages |
| Colony/food as sensors | Done | Box2D isSensor=True, distance-based detection |
| Smooth random walk | Done | Drifting wander_angle, not erratic |
| Speed clamping | Done | ANT_MAX_SPEED enforced per frame |
| HUD with stats | Done | Time, food count, state distribution |
| Data collection (CSV) | Not yet | Deferred to v1.1 |
| Parametric sweeps | Not yet | Deferred to v1.1 |

### Files After This Step

| File | Lines | Purpose |
| --- | --- | --- |
| `box2d_original.qmd` | 1,492 | Original exploration journal |
| `box2d.qmd` | 514 | Perfected v0 (cooperative transport) |
| `box2d_v1.qmd` | 926 | v1 (pheromone-based foraging colony) |
| `AUDIT_REPORT.md` | — | This incremental report |

---

*End of Report 4*

---

## Report 5: v1.1 — Behavioral Fixes & Interactive UI — 2026-03-02

### Context

After running v1, the following problems were observed (screenshot + user feedback):

1. **Explorer stuck on obstacle**: A returning explorer hit an obstacle and "died there" — no avoidance mechanism existed.
2. **Ants going left**: Many explorers wandered leftward from the colony and never found food. The `away-from-colony` bias was radial, not directional.
3. **HUD unreadable**: Small text rendered directly over the simulation area, overlapping with ants and pheromones.
4. **No controls**: No way to pause, resume, or stop the simulation cleanly.
5. **No per-ant inspection**: No way to see individual ant data (distance, state, trips).
6. **Individual departure**: Ants left one by one instead of in realistic groups.

### All Changes Applied (v1 → v1.1)

| # | Problem | Solution |
|---|---|---|
| 1 | Ants stuck on obstacles | `compute_wall_avoidance()`: AABB proximity check for each obstacle + arena wall distance checks. Returns repulsive force. Applied to ALL ant states. |
| 2 | Leftward exploration | Replaced `away-from-colony` radial bias with rightward cone: `wander_angle` initialized in `±EXPLORE_BIAS_ANGLE_SPREAD` (±45°) around `EXPLORE_BIAS_ANGLE_CENTER` (0 = right). Plus constant `fx += 2.5` rightward force. |
| 3 | HUD unreadable | Dedicated 260px right-side panel (`PANEL_WIDTH`). Simulation area = 800px, total window = 1060px. All text in panel only. |
| 4 | No controls | SPACE = pause/resume, S = screenshot (PNG), ESC = quit. Displayed in panel under "CONTROLS" section. |
| 5 | No ant inspection | `get_info_lines()` method returns 12 data fields per ant. Shown in panel when ant is clicked during pause. |
| 6 | Individual departure | Cluster spawning: `CLUSTER_SIZE=4`, ants spawn in adjacent positions with shared `cluster_id`. Wander angles within each cluster start in same rightward cone. |

### New Functions & Methods

| Function | Lines | Purpose |
|---|---|---|
| `compute_wall_avoidance(body)` | 347–386 | Arena walls (4 proximity checks) + obstacle AABBs (closest-point distance). Returns (fx, fy) repulsive force. |
| `screen_to_world(sx, sy)` | 671–673 | Inverse coordinate transform for mouse click → world position. |
| `find_ant_at_screen(mx, my)` | 708–720 | Finds closest ant to click point within 2m threshold. |
| `draw_panel(...)` | 723–785 | Right-side info panel: header, stats, state counts, controls, ant info card. |
| `Ant.get_info_lines(frame)` | 579–596 | Returns 12 (label, value) pairs: ID, caste, cluster, state, position, speed, distance, pheromone spent, emission cap, departure time, food trips, carrying status. |
| `Ant._update_tracking()` | 439–445 | Cumulative distance via frame-to-frame position delta. |
| `Ant._deposit(grid, ptype, amt)` | 447–451 | Deposit + track `pheromone_spent`. |

### New Tracking Fields per Ant

| Field | Type | Purpose |
|---|---|---|
| `cluster_id` | int | Which departure cluster this ant belongs to |
| `departure_frame` | int | Frame number when ant last left colony |
| `total_distance` | float | Cumulative meters traveled over lifetime |
| `pheromone_spent` | float | Total pheromone units deposited |
| `food_trips` | int | Completed food delivery cycles |
| `prev_pos` | tuple | Previous frame position for distance calculation |

### New Parameters (v1.1)

| Parameter | Value | Purpose |
|---|---|---|
| `PANEL_WIDTH` | 260 | Right info panel width (pixels) |
| `SIM_WIDTH` | 800 | Simulation area width (pixels) |
| `CLUSTER_SIZE` | 4 | Ants per departure group |
| `CLUSTER_SPREAD` | 1.0 | Meters between cluster members at spawn |
| `EXPLORE_BIAS_ANGLE_CENTER` | 0.0 | Rightward (radians) |
| `EXPLORE_BIAS_ANGLE_SPREAD` | 0.8 | ±45° cone half-width (radians) |
| `WALL_AVOID_RADIUS` | 2.5 | Distance at which avoidance activates (meters) |
| `WALL_AVOID_FORCE` | 12.0 | Strength of repulsive obstacle force |

### Architecture After v1.1

```
box2d_v1.qmd (853 lines, v1.1)
│
├── Section 1: Configuration (166 lines)
│   └── 60+ parameters: display, physics, arena, colony, food, obstacles,
│       ants, clusters, pheromones, forces, wall avoidance, colors
│
├── Section 2: PheromoneGrid class (unchanged from v1)
│   └── deposit, decay, read_intensity, read_gradient, render
│
├── Section 3: World building (unchanged from v1)
│   └── b2World + 4 walls + 5 obstacles + colony sensor + food sensor
│
├── Section 4: Ant class (v1.1)
│   ├── compute_wall_avoidance() — NEW
│   ├── Ant.__init__: cluster_id, tracking fields, biased wander_angle
│   ├── sense_decide_act(): wall avoidance in ALL states
│   ├── get_info_lines(): 12-field data card — NEW
│   └── _update_tracking(), _deposit(): stat accumulation — NEW
│
├── Section 5: Spawn ants in clusters (v1.1)
│   └── CLUSTER_SIZE groups, shared proximity, sequential cluster_ids
│
├── Section 6: Simulation loop (v1.1)
│   ├── to_screen(), screen_to_world() — NEW
│   ├── draw_static_world(), draw_zones()
│   ├── draw_ants_sim(highlighted) — NEW highlight ring
│   ├── find_ant_at_screen() — NEW
│   ├── draw_panel() — NEW (replaces draw_hud)
│   └── Main loop: events → decay → behavior → physics → render + panel
│
└── Section 7: Notes on v1.1 changes
```

### Files After This Step

| File | Lines | Purpose |
|---|---|---|
| `box2d_original.qmd` | 1,492 | Original exploration journal |
| `box2d.qmd` | 514 | Perfected v0 (cooperative transport) |
| `box2d_v1.qmd` | 853 | v1.1 (pheromone foraging + interactive UI) |
| `AUDIT_REPORT.md` | — | This incremental report |
| `.ants/` | — | Python 3.10 venv (pygame, Box2D, numpy, matplotlib) |

### Status: Awaiting Test

v1.1 has been written but not yet tested. Expected improvements:

- Explorers should move rightward toward food instead of scattering in all directions
- Ants should navigate around obstacles instead of getting stuck
- The info panel should be legible and separate from the simulation
- Pause + click should show per-ant data for debugging

---

*End of Report 5*

---

## Report 6: v1.2 — Tangential Wall Avoidance + Distinct Ant Colors — 2026-03-02

### Problem Observed (v1.1 screenshot, frame 3260)

The explorer that found food (state `FOOD_FOUND`) got stuck against an obstacle while returning to colony. The same class of bug as v1: **force deadlock**.

**Root cause**: `HOMING_FORCE * 1.2 = 12.0` toward colony and `WALL_AVOID_FORCE = 12.0` away from obstacle were equal and opposite. The ant sat at the equilibrium point indefinitely. The repulsion-only wall avoidance had no way to *route around* the obstacle — it only pushed straight back.

**Secondary issue**: Ants were the same color and size as pheromone dots (both blue/small), making them nearly indistinguishable in the simulation view.

### Solution: Tangential Sliding

Instead of only pushing away from obstacles, `compute_wall_avoidance()` now adds a **tangential force perpendicular to the obstacle surface**:

```
         obstacle
     ┌───────────────┐
     │               │
 ant ●─ repulsion ──→│   (old v1.1: ant stops here, deadlocked)
     │               │
     └───────────────┘

         obstacle
     ┌───────────────┐
     │               │  tangent (toward target)
 ant ●─ repulsion ──→│  ↑↑↑↑↑↑↑↑↑↑
     │               │  (new v1.2: ant slides along surface)
     └───────────────┘
```

The tangent direction is chosen by projecting the desired-to-target vector onto both possible perpendiculars and picking the one that aligns better. This means the ant always slides in the direction that moves it closer to its goal.

### All Changes (v1.1 → v1.2)

| # | Change | Detail |
|---|---|---|
| 1 | Tangential wall avoidance | `compute_wall_avoidance(body, target_x, target_y)` — adds sliding force perpendicular to obstacle normal, oriented toward target |
| 2 | Per-state target passing | Each of 7 states calls wall avoidance with its actual target (colony or food) |
| 3 | Stronger avoidance params | `WALL_AVOID_RADIUS` 2.5→3.0, `WALL_AVOID_FORCE` 12→15, new `WALL_TANGENT_GAIN=0.8` |
| 4 | Distinct ant colors | Explorers=red, refueling=orange, food-found=yellow, markers=magenta, workers idle=white, going=purple, carrying=green |
| 5 | Black ant outlines | 1px `COLOR_ANT_OUTLINE=(0,0,0)` ring around every ant |
| 6 | Larger ant rendering | 150% of physics radius for visibility |

### Technology Decision

After this version, the project will migrate from Pygame to a **Python backend + Web frontend** architecture:

- `engine.py`: Box2D physics, Ant class, PheromoneGrid — pure Python, no rendering
- `server.py`: FastAPI + WebSocket — sends state JSON at 30fps
- `web/index.html + simulation.js + style.css`: HTML5 Canvas + rich HTML panels

This enables: parameter sliders, real-time charts, clickable ant cards, zoom/pan, headless batch runs, and a browser-based TFG demo.

---

*End of Report 6*

---

## Report 7: v1.3 — Stuck Escape + True Cluster Cohesion — 2026-03-02

### Problems Observed (v1.2 screenshots f2505 + f2910)

Two screenshots taken 7 seconds apart (41.8s → 48.5s) show **3 yellow "Found food" ants in identical positions** — stuck against obstacles. The tangential sliding from v1.2 was insufficient because:

1. **Oscillation trap**: Tangent force only applies within `WALL_AVOID_RADIUS` (3m) of the obstacle surface. The ant gets pushed away → homing pulls it back → pushed away again. It oscillates at the boundary without clearing the obstacle edge. A 16m-tall obstacle requires 8+ meters of lateral travel, but the tangent zone is only 3m deep.

2. **Cluster behavior wrong**: User's concept was ants traveling *together as a pack*, sharing discoveries, protecting resources. The v1.2 "clusters" only spawned ants nearby — they diverged immediately and explored independently.

### Fix 1: Stuck Detection + Escape Kick

```
STUCK BEHAVIOR:

Frame 0-89:  Ant heading toward colony, blocked by obstacle
             stuck_counter increments each frame without distance progress
             Tangential force slides but oscillation prevents clearing

Frame 90:    stuck_counter >= STUCK_THRESHOLD
             → Strong lateral kick (20N) perpendicular to target direction
             → Random left or right
             → stuck_counter resets
             → Ant launched sideways, clears obstacle edge

Frame 91+:   Homing resumes, obstacle no longer blocking
             Ant proceeds to colony
```

### Fix 2: True Cluster Cohesion

| Feature | What it does |
| --- | --- |
| `_compute_cluster_cohesion()` | Each ant feels a force toward its cluster centroid. Ants in the same cluster travel together. |
| `cluster_lookup` dict | Maps `cluster_id → [ant list]`. O(1) lookup per ant per frame. |
| Shared discovery | When one explorer finds food, all cluster mates within 6m also transition to `FOOD_FOUND`. The group turns around together. |
| Cohesion in all moving states | Cluster cohesion force added to EXPLORE_OUT, REFUEL, FOOD_FOUND, WORKER_GOING, WORKER_CARRY. |

### New Parameters (v1.3)

| Parameter | Value | Purpose |
| --- | --- | --- |
| `STUCK_THRESHOLD` | 90 | Frames without progress before escape (~1.5s) |
| `STUCK_KICK_FORCE` | 20.0 | Lateral escape force (Newtons) |
| `STUCK_MIN_PROGRESS` | 0.05 | Minimum distance gain per frame to count as progress (m) |
| `CLUSTER_COHESION_FORCE` | 4.0 | Pull toward cluster centroid |
| `CLUSTER_COHESION_RADIUS` | 12.0 | Max distance for cohesion to apply (m) |
| `CLUSTER_DISCOVERY_RADIUS` | 6.0 | Shared discovery range (m) |

### New Ant Fields

| Field | Purpose |
| --- | --- |
| `stuck_counter` | Frames without target distance progress |
| `prev_target_dist` | Last measured distance to current target |

### Expected Behavior

- Ants stuck against obstacles for >1.5s get kicked sideways and find a way around
- Explorer clusters travel together toward food as a pack
- When one ant in a cluster finds food, nearby cluster mates all "feel" it and return together
- Workers with clusters also cohere while going to food and returning

---

*End of Report 7*

---

## Report 8: v1.4 — Sustained Escape Mode + Flock-Model Clusters

**Date**: 2026-03-02
**File modified**: `box2d_v1.qmd` (v1.3 → v1.4)

### Root Cause Analysis — Why v1.1–v1.3 Stuck Fixes Failed

All three prior approaches shared the same fundamental flaw: **transient forces overpowered
by sustained homing**. The homing force toward the target is applied every frame at 10–12N.
Prior "fixes" were:

| Version | Approach | Problem |
|---------|----------|---------|
| v1.1 | Repulsive force only | Equal to homing → deadlock |
| v1.2 | + Tangential sliding | Only applies within 3m of obstacle → oscillation at boundary |
| v1.3 | + One-time kick (20N) | Moves ant ~0.11m, then homing pulls back; 90-frame reset → oscillation |

**Key insight**: The obstacle at (48, 20, 2w, 8h) spans y=12–28. An ant at y=25 heading
left toward colony at (8,25) needs to clear 3m vertically. A one-time kick at 20N moves
the ant 0.11m before homing reasserts. The ant needs **sustained lateral movement** with
homing completely suppressed.

### Fix 1: Sustained Escape Mode

**Design**: When `stuck_counter >= STUCK_THRESHOLD` (60 frames, ~1s of no progress):

1. Compute perpendicular escape direction (to the line from ant to target)
2. **Obstacle clearance heuristic**: Check 3m ahead on both perpendicular sides, pick the
   side with more open space (further from obstacles and arena walls)
3. Set `escape_remaining = ESCAPE_DURATION` (120 frames = 2s)
4. While escaping: apply `ESCAPE_FORCE` (15N) in committed direction + wall avoidance
5. **Homing is completely suppressed** — the escape check short-circuits at the top of
   `sense_decide_act` before any state logic runs

**Parameters changed/added:**
- `STUCK_THRESHOLD`: 90 → 60 (detect faster)
- `STUCK_KICK_FORCE`: removed entirely
- `ESCAPE_DURATION`: 120 frames (new)
- `ESCAPE_FORCE`: 15N (new)

**New Ant fields**: `escape_fx`, `escape_fy`, `escape_remaining`

**Math**: At 15N force on a 0.5-density ant with damping 3.0, terminal velocity ≈ 5 m/s.
Over 2 seconds: ~10m lateral travel. The largest obstacle needs only ~3m vertical clearance.
The ant will easily clear it, then resume homing on the other side.

### Fix 2: Flock-Model Clusters

**User's vision** (verbatim): "they should move more or less in a kind of invisible circle,
moving together, some random star-like spread, but the 'mass center' of the group moves
as a whole...they as a group can save pheromones, as the pheromone track is so to say on
the movement of the mass center, in that way, so to say they can in turn leave the pheromone"

**Implementation — `_compute_flock_forces()` returns `(fx, fy, shared_angle)`:**

1. **Cohesion** (force=10.0, radius=15m): Strong pull toward cluster centroid.
   Increased from 4.0 to 10.0. This is the "invisible circle" — ants stay tightly grouped.

2. **Separation** (force=3.0, dist=1.5m): Push apart ants closer than 1.5m.
   This creates the "star-like spread" around the centroid — ants don't pile up on top
   of each other but maintain individual spacing.

3. **Shared heading** (weight=0.7): Average velocity direction of all cluster members.
   Explorer wander angles are blended: `wander_angle = shared_heading + gauss(0, 0.15)`.
   This makes the "mass center move as a whole" — all ants in the cluster go roughly
   the same direction, with small individual perturbations.

4. **Pheromone round-robin** — `_should_deposit()`: Each ant has a `cluster_index`
   (0, 1, 2, ...). Deposit only when `frame % cluster_size == cluster_index`. The trail
   follows the cluster's average path. One deposit every N frames instead of N overlapping
   deposits every frame. Group resource efficiency as the user described.

**Parameters changed/added:**
- `CLUSTER_COHESION_FORCE`: 4.0 → 10.0
- `CLUSTER_COHESION_RADIUS`: 12.0 → 15.0
- `CLUSTER_SEPARATION_FORCE`: 3.0 (new)
- `CLUSTER_SEPARATION_DIST`: 1.5 (new)
- `FLOCK_HEADING_WEIGHT`: 0.7 (new)
- `CLUSTER_DISCOVERY_RADIUS`: 6.0 → 8.0

### Code Changes Summary

| Component | Change |
|-----------|--------|
| Config | +4 new params, 3 updated, 1 removed (STUCK_KICK_FORCE) |
| `_check_stuck()` | Replaced by `_check_enter_escape()` — sets sustained escape |
| `_compute_cluster_cohesion()` | Replaced by `_compute_flock_forces()` — 3-component flock |
| `_should_deposit()` | New — pheromone round-robin gating |
| `sense_decide_act()` | Escape short-circuit at top; flock forces replace cohesion; deposits gated |
| `Ant.__init__` | +4 new fields (escape_fx/fy/remaining, cluster_index) |
| Spawn section | Sets `cluster_index` during cluster_lookup construction |
| Info card | Shows escape mode status ("120f left" / "No") |

### Expected Behavior

- Ants stuck against obstacles enter sustained escape after ~1s, clear the obstacle in 2s
- No more oscillation: homing is **completely suppressed** during escape
- Escape direction is intelligent: heuristic picks the open side
- Clusters move as cohesive flocks with star-like spread around centroid
- Mass center has shared heading — cluster moves as a unit
- Pheromone trail follows mass center path via round-robin deposits
- When one ant finds food, cluster mates within 8m also transition (and escape is cancelled)

---

*End of Report 8*

---

## Report 9: [Next entry will be appended here]
