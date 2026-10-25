# Backends and invariants

Prefer software found by `check_environment.py`. This machine has SOLIDWORKS 2025 SP5 and cadgen 0.7.10/build123d 0.11.1; FreeCAD/Blender were not found in PATH or standard installed-program directories. No large software installation is required for v1.

SOLIDWORKS is the delivered native feature/assembly backend. `_native_helpers.py` contains exercised typed COM helpers; `solidworks_backend.py` supplies project-specific dimensions and positions. Set `MECHANISM_SW_INSTALL` if the install directory changes. Importing helpers alone does not start SOLIDWORKS; backend invocation does. User documents remain open and unchanged; only the newly created assembly is closed/reopened for verification. Separate project prefixes avoid conflicting filenames across open SW projects. No auto-delete/rebuild of existing native parts is performed.

Important API behaviors observed on 2025 SP5:

- Read type libraries and use their generated wrappers; generic EnsureDispatch may fail GetTypeInfo.
- Load parts before AddComponent5. Fix the frame; unfix new links before assigning transforms.
- `swAddMateError_NoError` is 1, not 0. Check the actual feature tree's mate error codes too.
- Create the motor while the study is Animation, switch to Motion Analysis and actually calculate; load cmotionsw.dll. Require type4 on saved/reopened studies.
- This installed motor API accepts angular speed in rad/s. Convert RPM to 2πRPM/60 and verify native poses; do not infer success from setter return values.
- Cylinder entity direction is −Z; motor ReverseDirection is selected according to requested world motion.
- Default native result grid is 25 FPS. SetTime between output frames can display the preceding frame; verify on .04-second boundaries. The last serialized frame of a 30-second study is29.96. Warm the timebar off zero then return to zero after reopening.
- SaveAs native returns success/errors/warnings. Null export data is Python None. Clear selections before neutral export. Restore the dimension-prompt preference in finally blocks.
- Fully defined native sketches have solver status3. Equation-driven dimensions are exposed through their original features; exported STEP is not editable sketch history.

The text-to-CAD adapter uses the installed `cadgen` decorators and rendering CLI. On Windows decorator output paths use POSIX separators. A model must be a module-level decorated entrypoint; do not put a decorated nested function inside a generic CLI or read geometry before asking for its build. `cad_adapter.py` writes a minimal project model that imports the reusable shape function and lets cadgen save metadata.

FreeCAD: not implemented or tested in v1, so no FCStd output is promised. If installed later, implement/test real joints in its available assembly API before declaring native constraint preservation. Geometry-only STEP can be offered explicitly as a partial alternative, not a successful native assembly.

Product rendering and Blender are not implemented. Engineering rendering defaults to1920×1080/30FPS, light background, distinct link colors, FFmpeg MP4. New renderers must consume the solved pose data.
