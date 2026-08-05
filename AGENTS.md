# Agent notes

Facts for AI agents working in this repo.

- KiCad 10 project, design stage, no hardware yet. Root schematic `hardware/OpenAIO.kicad_sch` instantiates six FC sheets (`hardware/schematics/fc/`), 4x `hardware/schematics/esc/esc_channel.kicad_sch`, and `hardware/schematics/elrs/elrs.kicad_sch`. Board `hardware/OpenAIO.kicad_pcb` (6 copper layers) predates the 2026-06 schematic refresh.
- `esc_main.kicad_sch` and `ESC.kicad_sch` are reference circuitry, not instantiated by the root sheet.
- Clone with `git clone --recursive`; the `libs/KiCad-Library` submodule is referenced by the project lib tables for shared parts.
- Never edit `.kicad_*` files as text. Use kicad-skip or the pcbnew API, and only for metadata (text variables, symbol BOM/doc fields). Never change nets, placement, or component values.
- Checks:

```
kicad-cli sch erc --exit-code-violations hardware/OpenAIO.kicad_sch
kicad-cli pcb drc --exit-code-violations hardware/OpenAIO.kicad_pcb
```

- Design state, open items, and legacy footprint references: `hardware/docs/DESIGN.md`. Current sourcing: `docs/SOURCING-2026-06.md`; `docs/ALTERNATIVES.md` and `docs/COST_ANALYSIS.md` are 2026-03 snapshots of the pre-refresh ESC BOM.
- `hardware/datasheets/` is local reference material, gitignored, not tracked.
- Docs are deterministic: current fact only, no TODOs or plans.
- `main` is protected; push feature branches and open PRs.
