# Can a 700-Year-Old Plague Gene Help Us Fight Cancer?

## The Discovery

During the Black Death (1346-1353), a gene called **ERAP2** gave carriers a 40% survival advantage — the strongest documented case of natural selection in human history (Klunk et al., *Nature* 2022).

Today, that same gene is linked to **Crohn's disease** and **cancer immune evasion**. ERAP2 controls which protein fragments (antigens) get displayed on cell surfaces for immune detection. When cancer cells hijack ERAP2, they hide from the immune system — making immunotherapy less effective.

**No drugs exist that selectively target ERAP2.** The first selective nanomolar inhibitors were only discovered in 2022 (Camberlein et al., *Angewandte Chemie*).

## What We Built

Using AI-driven drug discovery, we designed a **6-amino-acid peptide (VAGSAF)** that our computational models predict will selectively bind ERAP2 while ignoring its close relatives ERAP1 and IRAP.

Our pipeline:
1. **Evolutionary genomics** — identified ERAP2 as a high-value target through ancient DNA analysis
2. **AI protein design** — generated candidate peptides using machine learning (PepMLM)
3. **Structure prediction** — validated binding with Boltz-2 (state-of-the-art protein folding AI)
4. **Selectivity screening** — confirmed the peptide ignores off-target proteins

**Key result:** VAGSAF achieves an ipTM score of 0.905 for ERAP2 (strong predicted binding), but only 0.335 for ERAP1 and 0.236 for IRAP — a **triple selectivity** profile.

## What We Need

We need **$1,400** to synthesize VAGSAF and test it in a wet lab:

| Item | Cost |
|------|------|
| Peptide synthesis (VAGSAF + scrambled control) | $330 |
| ERAP2 binding assay (dose-response) | $400 |
| ERAP1 + IRAP selectivity counter-screen | $200 |
| Lab consumables + shipping | $175 |
| Platform fees + contingency | $295 |

**Timeline:** 5-7 weeks from funding to results.

## What Success Looks Like

If VAGSAF shows selective ERAP2 inhibition in the lab:
- It validates the **first AI-designed selective ERAP2 peptide**
- It opens a path to new treatments for Crohn's disease and immunotherapy-resistant cancers
- It demonstrates that **ancient evolutionary pressures can guide modern drug discovery**

All results will be published openly — positive or negative.

## Why This Matters

ERAP2 sits at the intersection of:
- **Evolutionary biology** — shaped by the deadliest pandemic in human history
- **Cancer immunology** — controls the immune system's ability to detect tumors
- **Autoimmune disease** — directly linked to Crohn's and ankylosing spondylitis
- **AI drug discovery** — computationally designed with no existing drug to copy

This is a first-of-its-kind experiment bridging archaeogenetics and modern drug design.

## About the Researcher

Jeremy Johnson — pharmacist and independent researcher combining computational biology, evolutionary genomics, and AI to find new therapeutic targets in ancient DNA. This project uses open-source tools (Boltz-2, PepMLM, ESM-2) and publishes all methods and results publicly.

## Budget Transparency

Every dollar is itemized in our public budget. Lab work will be performed by GenScript (peptide synthesis) and a university core facility or CRO (binding assays). All raw data will be shared.

---

*This project is part of the Ancient Drug Discovery pipeline — mining 10,000 years of evolutionary immune selection to find the next generation of medicines.*
