# Vehicle models

The rocket panel uses original procedural GLB meshes (Falcon 9, Falcon Heavy, Starship + Super Heavy). Files live in `frontend/public/models/` and are MIT-licensed visualization meshes, not engineering CAD.

- Units are meters, +Y up, launch base at Y = 0
- Named parts drive stack animation (`left_booster_*`, `right_booster_*`, `first_stage_*`, `super_heavy_*` / `booster_*` / `raptor_*`, `ship_*`, `*fairing*`)
- Poses come from the mission profile clock, not telemetry

| Vehicle | Boosters fall away at | First / Super Heavy stage |
| --- | --- | --- |
| Falcon 9 | — | `stage_sep` |
| Falcon Heavy | `booster_sep` | `stage_sep` (center core) |
| Starship | Super Heavy at `hot_stage` | Ship continues |

These are estimated schematic events. The UI labels them as such.
