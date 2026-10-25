---
name: mechanism-to-cad
description: 从机械图片、结构草图、原理图或零件描述分析机构，建立参数化三维零件、真实装配运动副、运动学仿真与动画。优先支持平面四杆；输入不足以确定机构时请求必要尺寸和约束，不凭图片比例制造确定尺寸。
---

# 机械结构智能建模与运动仿真系统

Use this skill to coordinate evidence-based mechanical interpretation, CAD and closed-loop motion. V1 fully exercises planar four-bar geometry and SOLIDWORKS native features/mates/Motion Analysis on Windows. Other mechanisms and FreeCAD/Blender adapters are extension points, not delivered capabilities. Read [architecture](references/architecture.md) for supported scope and project contracts.

## Start with evidence and the available environment

For a freshly cloned repository without local settings, follow README.md and run `scripts/configure_environment.py` with a verified installed interpreter. `local_environment.example.json` is a template; it is not a usable configuration until its paths are replaced.

1. Run `scripts/check_environment.py --out <report.json>` using the interpreter from `local_environment.json`, or `MECHANISM_PYTHON`. Reuse installed software. If that interpreter was moved, identify another interpreter with cadgen, numpy, matplotlib, Pillow and pywin32 before proceeding. Do not uninstall/update other skills or silently install large CAD applications.
2. Read the existing **text-to-cad:cad** SKILL.md from the detected installed path. It owns cadgen geometry/export/snapshot contracts. The adapter here composes that package; it does not replace the plugin or its text-to-CAD workflow. Consult [CAD backends](references/cad_backends.md) for native SOLIDWORKS/API behavior and fallback boundaries.
3. If an image is supplied, view it with the host image tool. Record visible parts, IDs, geometry, fixed/driver parts, joint hypotheses, evidence, uncertainties and confidence in a JSON observations file. Use `assets/templates/image_observations.json` as the data contract. Check that the proposed topology matches the image. Python does not perform autonomous vision; no observations means no claim that an image was analyzed.
4. Ask for missing **critical** dimensions or constraints that determine topology, motion or solution choice. Progress on independent work while waiting. Mark optional defaults and conceptual assumptions explicitly. Do not infer exact dimensions from perspective/photo scale. Do not label guessed hidden joints as confirmed.

## Resolve the mechanism before making parts

Use millimeters and the explicit schema in [kinematics](references/kinematics.md). The four-bar family uses `ground, crank, coupler, rocker` center distances, `branch=+1/-1`, one fixed ground, four revolute joints, one input drive. `+1` selects the upper circular-intersection branch for A=(0,0), D=(ground,0).

`core.synthesize(ground, rocker, swing, K)` returns all distinct nondegenerate crank-rocker length candidates found by the analytic construction, with verification. Show all candidates and ask the user to select when there is more than one. Do not choose candidate zero automatically. A mirror choice does not select which named stroke is faster; record direction, mounting and timing convention separately.

The supplied acceptance case has **two** length solutions, not a unique design. The included acceptance template records the user's explicit short-coupler selection; do not reuse that choice as a universal default. Rounded prior lengths must pass the current input tolerances before being accepted.

`scripts/analyze_mechanism.py` builds the topology and resolved parameters; `scripts/solve_kinematics.py` solves circle intersections with a fixed branch, reports full-turn feasibility, singularities, transmission angle and geometric closure, and exports trajectories and numerical angular derivatives. For restricted input motion, explicitly set `require_full_turn=false` and limit the requested input angle/time; native constant-speed full-turn acceptance is still separate. The current native workflow is intended for nonsingular full-turn input.

## Execute the project

Use a **new project directory**; existing parts/assemblies are never overwritten by generation. Keep original supplied CAD files intact. For a resolved four-bar:

```powershell
$skillDir = Join-Path $env:USERPROFILE '.agents\skills\mechanism-to-cad'
& "$skillDir\run.ps1" 'D:\Projects\MyMechanism' --parameters 'D:\Projects\parameters.json'
```

Add `--reference <image>` and `--observations <json>` after visually analyzing an image. Defaults are engineering video, 1920×1080, 30 FPS. `--fps`, `--width`, `--height` override video settings. The `generate_animation.py --camera-json` CLI accepts cadgen camera JSON for a specific view.

Stages are `analyze,solve,parts,assembly,animation,validate`. Resume only unfinished stages with `--stages animation,validate`, for example. A failed stage writes a failed record and stops; do not claim downstream outputs exist. See [troubleshooting](references/troubleshooting.md).

Native part generation retains fully defined sketches, equation-driven lengths/widths/thicknesses/holes, bosses/extrudes and through-hole cuts. Native assembly fixes the frame and establishes four concentric and three axial-distance mates. Each link has local pivots at (0,0,0), (L,0,0), shaft axis +Z. Axial offsets leave 4 mm clearance between adjacent link layers. These offsets require appropriate shafts/spacers in a physical build; four main links exclude those fasteners.

The SOLIDWORKS study must actually calculate, be sampled against the independent solver and survive close/reopen with cached results. Read the exact assembly filename from `reports/native_validation.json`: native filenames include a project prefix so projects can coexist in SOLIDWORKS. STEP saves geometry, not native mates; retain SLDPRT and SLDASM together. Only claim a native simulation if that report records success and reopened samples pass. The installed API's speed units and output grid are handled by the exercised adapter; do not copy RPM directly into an unverified API call.

Animation uses a solved frame table, not independent rotations. V1 engineering preview uses cadgen and FFmpeg; product/Blender mode explicitly raises unsupported. MP4 is a geometric kinematic preview; SOLIDWORKS Motion Analysis is separately saved in SLDASM. No force/stress/print-strength claim follows from motion success.

## Validate, inspect and deliver

- Run `scripts/validate_project.py <project>` after all requested stages. It reopens STEP, measures hole axes/widths/thicknesses, checks solid validity, binary STL manifoldness, native mate states and replay, recomputes CSV poses, checks branch continuity, and decodes the moving MP4. It proves continuous interference exclusion for the delivered flat-link family through disjoint invariant Z intervals; do not apply this proof to extended pedals/bases or arbitrary imported parts without fresh geometry checks.
- Read the generated part snapshots and animation preview with the image tool. Use the installed text-to-CAD snapshot/viewer workflow for visible geometry. Review additional views if interfaces remain hidden. Show `assembly/Viewer_Assembly.step` with `cad_show`; use `cad_open` only if no viewer is open.
- Deliver the native assembly, all referenced native parts, STEP/STL, motion CSV, MP4 and reports. Report design selection, unconfirmed assumptions and checks actually executed. For loads, gears, cams, sliders or arms outside v1, identify the unsupported step and develop a separately tested adapter before claiming support.

For local regression use `python -m unittest discover -s <skill>/tests -v`. `README.md` gives user-facing calls and the Windows installation/runtime contract.
