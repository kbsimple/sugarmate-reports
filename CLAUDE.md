# CGM Insights Project

## Conventions

### Git Commit Author

All commits must use:
- **Author name:** Faiser
- **Email:** keepbreakfastsimple@gmail.com

### Python Code Style

Follow the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html).

## Project Context

**Core Value:** Users upload their CGM data and leave knowing exactly what to focus on to improve their glucose control.

**Architecture:** Python analysis engine (reusable library) → CLI → Web frontend. Core library must be independently usable before any interface is built.

**Technology:** Polars + GlucoStats + FastAPI/HTMX + Typer

**Regulatory:** Wellness language only. No medical advice, insulin recommendations, or treatment suggestions.

## GSD Workflow

This project uses Get Shit Done (GSD) workflow:

- `/gsd-progress` — Check current status
- `/gsd-plan-phase 1` — Create execution plan for current phase
- `/gsd-execute-phase` — Execute all plans in current phase
- `/gsd-verify-work` — Verify work satisfies requirements
- `/gsd-next` — Advance to next phase

## Current Status

**Phase:** 1 - Core Analysis Library
**Status:** Ready for planning
**Next:** `/gsd-plan-phase 1`

See `.planning/STATE.md` for detailed context.