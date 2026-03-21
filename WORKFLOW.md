# WORKFLOW.md

## Purpose
This document describes how the team should work in this repo **based on the current actual workflow**, not just the original plan.

---

## Branching

Current practical branches:
- `main` -> stable branch
- `kardam-learner` -> Kardam learner/frontend branch when feature batching is needed

Feature work may still happen on task-specific branches if needed, but current repo history already uses:
- `main`
- `kardam-learner`

---

## Recommended Flow

1. Pull latest changes
2. Work in the appropriate branch
3. Keep commits focused
4. Build/test locally
5. Push the branch
6. Merge into `main`

---

## Commit Style

Use short conventional-style messages:
- `feat: ...`
- `fix: ...`
- `docs: ...`
- `chore: ...`
- `refactor: ...`

Examples:
- `feat: add pdf viewer with fullscreen controls`
- `chore: remove unused src module scaffolds`

---

## Frontend Working Rules

- Add metadata headers in source files
- Keep ownership clear
- Use SVG icons only
- Do not create empty scaffold folders
- Do not invent a second frontend architecture
- Reuse `src/styles/app.css` for the shared visual system unless a strong reason exists

---

## Documentation Rules

When the product structure changes:
- update the related markdown docs
- keep docs aligned with the real repo state
- prefer current truth over old planned wording

Key docs to keep aligned:
- `README.md`
- `API.md`
- `ARCHITECTURE.md`
- `DB_SCHEMA.md`
- `DESIGN.md`
- `TASKS.md`
- `PAGE_CONSISTENCY.md`

---

## Pre-Merge Checklist

Before merging:
- run `npm run build`
- review for accidental scaffold files/folders
- verify routes still work
- verify typography/spacing consistency if the change is visual

---

## Instructor/Admin Page Rule

If Yug or Yug's Codex adds instructor pages:
- follow `PAGE_CONSISTENCY.md`
- keep frontend pages in `src/pages`
- keep reusable blocks in `src/components`
- do not create frontend `src/modules/*` scaffolding again
