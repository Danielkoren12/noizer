# Noizer design skills

Project-local Codex skills live under `.agents/skills/`:
- `emil-design-eng`: component polish, motion, accessibility and performance.
- `impeccable`: frontend design, typography, layout, responsive behavior and design review.
- `design-taste-frontend`: distinctive public-facing website art direction.

Read the relevant SKILL.md before use and referenced files as needed. Use guidance that fits the task; do not apply all three mechanically. User requirements, accessibility, established branding and Hebrew/RTL needs take precedence over house-style defaults.

The user does not want to type terminal commands. Perform supported preparation through tools. Before running any external script, launcher or installer, explain what it does and obtain user approval. This includes Impeccable's launcher (which can download an engine) and Taste Skill's draw, assets, lint and inspector scripts. No automatic hooks are installed. Until approval, use available documented fallbacks and clearly report checks that did not run.

Preserve existing files and the bundled licenses and notices. Exact sources and revisions are in SKILLS-SOURCES.json. Use the existing isolated checkout; do not create a Git worktree unless requested.

The current user-approved baseline is the Git tag `v1.2.0-baseline`. Interpret requests to return to the baseline as referring to this tag. Preserve earlier version history. Never reset over uncommitted work; inspect and preserve it before restoring an approved version.
