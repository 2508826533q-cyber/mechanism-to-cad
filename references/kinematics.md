# Four-bar schema and solution

Input example (mm, seconds, degrees):

```json
{
  "mechanism_type":"four_bar",
  "units":"mm",
  "lengths":{"ground":300,"rocker":250},
  "design":{"swing_deg":40,"K":1.2,"candidate_index":0},
  "branch":1,
  "simulation":{"rpm":50,"duration_s":30,"dt_s":0.03333333333333333,"initial_deg":45,"direction":1},
  "assumptions":["candidate selection confirmed by user; other assembly choices explicitly declared"]
}
```

Alternatively specify all four `lengths` and omit `design`. If supplying both, lengths must match the requested swing/K within `design_tolerance` (default 1e-6). `part_defaults` optionally sets `width_mm,thickness_mm,rocker_width_mm,rocker_thickness_mm,hole_mm`; frame width/thickness in v1 are 30/8 mm and declared in the output. Dimensions must leave positive webs outside holes. Materials/loads are unconfirmed unless supplied; no material-strength result is generated.

Synthesis: with d=AD, c=CD, half swing h, rocker midangle m, the two endpoints are C±=(d+c cos(m±h), c sin(m±h)). From constant-speed quick return θ=π(K−1)/(K+1), the magnitude of the angle between AC− and AC+ equals θ. Their dot product is d²+2dc cos(m)cos(h)+c²cos(2h), and cross product is 2c sin(h)(d cos(m)+c cos(h)). Enumerate both cross signs in tan θ = |cross|/dot. Solve the resulting linear equation for cos(m). Reject impossible cosines, nonclosing dimensions, singular/non-full-turn designs and candidates whose recomputed swing/K fail the requested tolerance.

Let r±=|AC±|. The crank/coupler lengths are a=|r+−r−|/2, b=(r++r−)/2. This enumerates the examined crank-rocker family; it is not a general arbitrary-mechanism synthesis proof. K denotes longer/shorter time ratio, without naming which stroke is quicker.

For d300, c250, swing40°, K1.2:

| candidate | crank a mm | coupler b mm | upper-branch mean DC angle |
|---|---:|---:|---:|
|0 short coupler|83.60514904142842|151.17292022893315|150.48093989908722°|
|1 long coupler|65.63218169655732|390.6459004035889|88.20637114241343°|

Both have mirror assemblies. The user selected candidate0 for the initial acceptance on 2026-10-25. That selection is not a default for later users/projects.

Forward solve: B=(a cos q,a sin q). Let v=B−D, r=|v|, u=(c²−b²+r²)/(2r), h²=c²−u². Intersect circles centered at B and D; branch sign fixes the sign of the perpendicular component. Negative h² means closure impossible; h≈0 is a toggle where branch continuation is not guaranteed.

For complete input rotation, r ranges from |d−a| to d+a, which must lie strictly inside [|b−c|, b+c] for nonsingular closure. The solver audits at least 1441 angles per turn as well as this interval condition. The Jacobian loses rank at toggle; the scalar planar mobility formula M=3(n−1)−2J=1 is meaningful for the regular supported topology, not proof for arbitrary redundant/spatial constraints.

CSV angles are unwrapped before finite differences. Velocity and acceleration are numerical and carry discretization/endpoint error. Coarse steps with ambiguous angular jumps are rejected. Animation uses the same solver at the requested movie sampling times; no linear interpolation of independent point positions breaks link lengths.
