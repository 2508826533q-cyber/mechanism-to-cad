# Failure handling

- Missing critical lengths / multiple candidates: run synthesis, present candidates, request the needed dimension/branch choice. Continue environment/code work that does not depend on the answer. Never choose a design by timing out a question.
- Contradictory swing/K: show calculated values and requested tolerances. The rounded65.6/390.6 pair gives39.974279° and K1.19984686 for d300/c250, so it does not meet exact40°/1.2.
- Invalid circle intersection / toggle / angular jump: report the input angle, closure range and branch; refine time step only for discretization ambiguity, not to hide infeasibility. Do not animate independent links to bypass the solver.
- Source CAD newer than local SOLIDWORKS: source bodies may be readable with warning128 but sketches unavailable. Preserve originals and disclose rebuilding limits. Do not silently claim to have preserved an unavailable source feature tree.
- Missing Python path: edit local_environment.json or set MECHANISM_PYTHON after checking installed packages; do not move/delete the shared existing environment. `run.ps1` checks that it exists and otherwise stops with an explicit instruction.
- Missing cadgen snapshot browser: check the installed text-to-CAD setup instructions; reuse existing Chromium. Do not install FreeCAD/Blender to solve a browser issue.
- Native motion unavailable: preserve actual part/assembly files and mark the failed study; an analytical video is a partial deliverable, not evidence of Motion Analysis. Do not repeat creation of motors inside a corrupt study. Choose a fresh project for rebuilt native assembly; never overwrite original user files.
- STL export is ASCII: use installed cadgen STL export to produce a binary mesh and re-run geometry/manifold checks; the current validator explicitly rejects unknown/truncated formats rather than claiming print readiness.
- Failed stage: read `reports/stage_<stage>.json` and its actual exception. Resume only the required stage using `--stages`; do not rerun parts over existing files. Status is not a substitute for checking saved outputs.
- Skill discovery: use Codex's read-only skills/list protocol with forceReload, or open the skill selector. Installation only creates this skill directory; it does not change unrelated config. If the UI does not refresh, restart Codex as documented by OpenAI.
