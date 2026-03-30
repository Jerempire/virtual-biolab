# Virtual Biolab

Multi-agent adversarial critique pipeline for peptide drug discovery, built on top of the [Ancient Drug Discovery](https://github.com/Jerempire/ancient-drug-discovery) project.

## What This Does

Adds a **9-gate adversarial pipeline** to the existing computational drug discovery workflow. The first 4 gates validate existing results (GWAS, peptide design, structure prediction, selectivity). Gates 5-9 add new capabilities:

- **Gate 5: Adversarial Critique** — AI agent challenges findings across 5 axes (selectivity, bioavailability, prior art, mechanism, reproducibility), backed by PubMed/ChEMBL evidence
- **Gate 6: Literature Cross-Validation** — Automated search for contradicting evidence
- **Gate 7: Synthesis Feasibility** — Toxicity, solubility, and manufacturability checks
- **Gate 8: Wet Lab Protocol** — Generates GenScript/Ginkgo-ready synthesis and assay protocols
- **Gate 9: Cost & Funding** — Itemized budget and crowdfunding campaign materials

## Architecture

Inspired by [Bio Protocol's virtual biotech labs](https://arxiv.org/abs/2602.19810) (ClawdLab/Beach.Science), adapted for independent researchers using Python + existing open-source tools.

```
agents/       Structured prompt agents (Critic, Scout, Synthesizer)
gates/        9-gate pipeline with pass/fail criteria
crowdfund/    Campaign materials for Experiment.com, Beach Science, VitaDAO
tools/        Imports from ancient-drug-discovery/tools/ (ScienceClaw)
outputs/      Gate reports, critique logs (gitignored)
```

## Quick Start

```bash
conda activate ancient-drug-discovery
cd Projects/medical/virtual-biolab

# Run VAGSAF through the pipeline
python gates/runner.py VAGSAF ERAP2

# Run critic agent standalone
python agents/critic.py
```

## Current Status

- **Proof-of-concept candidate:** VAGSAF (6-mer peptide)
- **Target:** ERAP2 (selective over ERAP1, IRAP)
- **Computational result:** ipTM 0.905 (ERAP2), 0.335 (ERAP1), 0.236 (IRAP)
- **Next step:** Wet lab synthesis and binding assays (~$2,200)
- **Crowdfunding:** Campaign materials ready for Experiment.com and Beach Science

## Funding

See `crowdfund/` for:
- `budget.yaml` — Itemized wet lab costs
- `campaign_draft.md` — Experiment.com campaign narrative
- `beach_hypothesis.md` — Beach Science hypothesis post
- `pitch_deck.md` — VitaDAO/Bio Protocol one-pager

## License

MIT
