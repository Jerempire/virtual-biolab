# CLAUDE.md - Virtual Biolab

## Project Overview
Multi-agent adversarial critique pipeline for peptide drug discovery. Wraps the existing
`ancient-drug-discovery` pipeline with structured gates, automated literature cross-validation,
and crowdfunding tools for wet lab synthesis.

**Parent project**: `../ancient-drug-discovery/` — all ScienceClaw tools, Boltz-2 runner,
scoring modules, and target configs live there. This project adds the critique layer.

## Architecture
- `agents/` — Structured prompt agents (Critic, Scout, Synthesizer, Protocol Writer)
- `gates/` — 9-gate pipeline with pass/fail criteria and HTML reporting
- `crowdfund/` — Campaign materials for Experiment.com, Beach Science, VitaDAO
- `tools/` — Thin wrappers that import from ancient-drug-discovery/tools/
- `outputs/` — Gate reports, critique logs (gitignored)

## How Agents Work
Agents are **not** autonomous LLM API calls. They are structured Python modules that:
1. Gather evidence via ScienceClaw tools (PubMed, ChEMBL, UniProt, BLAST)
2. Format structured prompts for interactive Claude Code sessions
3. Enforce evidence-backed critique (no hallucinated objections)

**No external LLM API costs.** Everything runs through Claude Code Max plan sessions.

## Environment
- Conda: `ancient-drug-discovery` (same env as parent project)
- Python 3.11, pyyaml, requests, jinja2

## Key Rules
- Gates 1-4 delegate to ancient-drug-discovery scripts — don't duplicate
- Critic agent must cite PubMed IDs or ChEMBL IDs for every objection
- Never run agents autonomously/scheduled — interactive sessions only
- outputs/ is gitignored
