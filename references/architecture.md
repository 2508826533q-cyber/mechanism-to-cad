# Scope and data flow

V1: Codex visual observations → explicit JSON parameters → analytic four-bar synthesis/topology → circle-intersection solver → native SOLIDWORKS feature trees + actual mates + Motion Analysis → cadgen exchange/viewer adapter → solved-pose animation + FFmpeg → file/geometry/motion verification.

Implemented: arbitrary positive four-link lengths, positive/negative input rotation, two circle-intersection branches; crank-rocker dimension synthesis; full-input-turn check; general pose solver also covers feasible double-crank and portions of double-rocker motion. A fixed input, not arbitrary multiple drivers, is supported. The native acceptance flow is full-turn nonsingular planar revolute four-bar.

Not implemented: independent neural image segmentation, autonomous hidden-part inference, arbitrary imported-parts remating, slider-crank/prismatic joints, rigid subassembly joints, gears/contacts, cams, multi-loop or spatial arms, FreeCAD native joints, Blender product rendering, FEM. Keep topology extensible by adding a solver/backend, not by returning a four-bar for these requests.

Project contract:

```
input/        supplied parameters + copied image if present
analysis/     observations/topology, resolved parameters, candidate designs, native part facts
parts/        individually editable native parts (+ native neutral exports)
assembly/     project-prefixed *_Assembly.SLDASM and Viewer_Assembly.py/.step/.step.json
simulation/   configuration, full motion CSV, curves, solver validation
animation/    solved frame CSV/JS, animation.mp4, preview.png, render settings
export/STEP/  four parts + native assembly exchange geometry
export/STL/   binary closed-mesh part outputs
reports/      stage status, real native/replay/geometry/video validation, part snapshots, opening instructions
```

Only present artifacts count as output. The stage runner writes failed status on errors; a full validation report must pass before delivery as a complete project. Individual scripts remain usable for diagnosis/resuming.

Vision: view the user's actual image in the host, record evidence in observations JSON, obtain confirmations on topology and dimensions. `analyze_mechanism.py` imports observations and builds the confirmed topology. A text-only acceptance test does not establish photo interpretation accuracy. The included 32×32 image unit fixture only tests file ingestion.

Each project is independent of the previous sewing-machine projects. No source code imports those earlier models. The local runtime configuration reuses their existing Python environment on this computer; the installed skill scripts themselves are self-contained.
