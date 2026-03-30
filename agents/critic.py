"""
Adversarial Critic Agent for Virtual Biolab

Challenges drug discovery hypotheses across 5 axes:
  1. Selectivity — off-target binding risk
  2. Bioavailability — peptide stability and half-life
  3. Prior Art — existing compounds that solve the problem
  4. Mechanism — does the proposed mechanism hold up
  5. Reproducibility — can predictions be trusted

USAGE:
  This is NOT an autonomous agent. It gathers evidence from ScienceClaw tools
  and produces a structured critique report. Run interactively in Claude Code.

  from agents.critic import CriticAgent
  critic = CriticAgent.from_config("config.yaml")
  report = critic.gather_evidence("VAGSAF", "ERAP2")
  report.print_summary()
  # Then discuss the critique interactively with Claude
"""

import sys
import os
import json
import yaml
import importlib.util
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# ── Resolve parent project tools ────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARENT_PROJECT = (PROJECT_ROOT / ".." / "ancient-drug-discovery").resolve()
TOOLS_DIR = PARENT_PROJECT / "tools"

# Add parent tools to path so we can import them
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


@dataclass
class Objection:
    """A single critique objection with evidence."""
    axis: str                    # selectivity | bioavailability | prior_art | mechanism | reproducibility
    severity: str                # critical | major | minor
    claim: str                   # what the critic is asserting
    evidence: list[dict] = field(default_factory=list)  # [{source, id, summary}]
    resolved: bool = False
    resolution: str = ""

    def to_dict(self) -> dict:
        return {
            "axis": self.axis,
            "severity": self.severity,
            "claim": self.claim,
            "evidence": self.evidence,
            "resolved": self.resolved,
            "resolution": self.resolution,
        }


@dataclass
class CritiqueReport:
    """Structured critique report for a candidate."""
    candidate: str
    target: str
    timestamp: str = ""
    objections: list[Objection] = field(default_factory=list)
    literature_hits: list[dict] = field(default_factory=list)
    chembl_hits: list[dict] = field(default_factory=list)
    gate_passed: bool = False

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    @property
    def critical_unresolved(self) -> list[Objection]:
        return [o for o in self.objections if o.severity == "critical" and not o.resolved]

    @property
    def all_unresolved(self) -> list[Objection]:
        return [o for o in self.objections if not o.resolved]

    def evaluate_gate(self, max_unresolved_critical: int = 0, max_unresolved_minor: int = 1) -> bool:
        """Determine if candidate passes Gate 5."""
        n_critical = len(self.critical_unresolved)
        n_minor = len([o for o in self.all_unresolved if o.severity == "minor"])
        self.gate_passed = (n_critical <= max_unresolved_critical and
                            n_minor <= max_unresolved_minor)
        return self.gate_passed

    def print_summary(self):
        """Print human-readable critique summary."""
        print(f"\n{'='*60}")
        print(f"CRITIC REPORT: {self.candidate} → {self.target}")
        print(f"Generated: {self.timestamp}")
        print(f"{'='*60}")

        for axis in ["selectivity", "bioavailability", "prior_art", "mechanism", "reproducibility"]:
            axis_objs = [o for o in self.objections if o.axis == axis]
            if not axis_objs:
                print(f"\n  [{axis.upper()}] No objections raised")
                continue
            print(f"\n  [{axis.upper()}]")
            for o in axis_objs:
                status = "RESOLVED" if o.resolved else "OPEN"
                icon = "+" if o.resolved else "!"
                print(f"    {icon} [{o.severity}] {o.claim} — {status}")
                for ev in o.evidence:
                    print(f"      └─ {ev.get('source', '?')}: {ev.get('id', '')} — {ev.get('summary', '')}")
                if o.resolved:
                    print(f"      └─ Resolution: {o.resolution}")

        print(f"\n{'─'*60}")
        n_total = len(self.objections)
        n_resolved = len([o for o in self.objections if o.resolved])
        n_critical = len(self.critical_unresolved)
        self.evaluate_gate()
        verdict = "PASS" if self.gate_passed else "FAIL"
        print(f"  Objections: {n_total} total, {n_resolved} resolved, {n_critical} critical unresolved")
        print(f"  Gate 5 verdict: {verdict}")
        print(f"{'='*60}\n")

    def to_dict(self) -> dict:
        return {
            "candidate": self.candidate,
            "target": self.target,
            "timestamp": self.timestamp,
            "objections": [o.to_dict() for o in self.objections],
            "literature_hits": self.literature_hits,
            "chembl_hits": self.chembl_hits,
            "gate_passed": self.gate_passed,
        }

    def save(self, output_dir: Path):
        """Save report as JSON and Markdown."""
        output_dir.mkdir(parents=True, exist_ok=True)
        slug = f"{self.candidate}_{self.target}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # JSON (machine-readable)
        json_path = output_dir / f"critique_{slug}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

        # Markdown (human-readable)
        md_path = output_dir / f"critique_{slug}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(self._to_markdown())

        return json_path, md_path

    def _to_markdown(self) -> str:
        lines = [
            f"# Critic Report: {self.candidate} → {self.target}",
            f"**Generated:** {self.timestamp}",
            "",
        ]
        for axis in ["selectivity", "bioavailability", "prior_art", "mechanism", "reproducibility"]:
            axis_objs = [o for o in self.objections if o.axis == axis]
            lines.append(f"## {axis.replace('_', ' ').title()}")
            if not axis_objs:
                lines.append("No objections raised.\n")
                continue
            for o in axis_objs:
                status = "Resolved" if o.resolved else "**OPEN**"
                lines.append(f"### [{o.severity.upper()}] {o.claim} — {status}")
                if o.evidence:
                    lines.append("**Evidence:**")
                    for ev in o.evidence:
                        lines.append(f"- {ev.get('source', '?')}: `{ev.get('id', '')}` — {ev.get('summary', '')}")
                if o.resolved:
                    lines.append(f"\n**Resolution:** {o.resolution}")
                lines.append("")

        self.evaluate_gate()
        verdict = "PASS" if self.gate_passed else "FAIL"
        lines.extend([
            "---",
            f"## Gate 5 Verdict: {verdict}",
            f"- Total objections: {len(self.objections)}",
            f"- Resolved: {len([o for o in self.objections if o.resolved])}",
            f"- Critical unresolved: {len(self.critical_unresolved)}",
        ])
        return "\n".join(lines)


class CriticAgent:
    """
    Gathers evidence and builds structured critiques of drug discovery candidates.

    The agent does NOT make autonomous decisions. It:
    1. Queries PubMed, ChEMBL, UniProt via ScienceClaw tools
    2. Structures findings as objections with evidence
    3. Produces a report for interactive discussion in Claude Code
    """

    def __init__(self, config: dict):
        self.config = config
        self.agent_config = config.get("agents", {}).get("critic", {})
        self.critique_axes = self.agent_config.get("critique_axes", [
            "selectivity", "bioavailability", "prior_art", "mechanism", "reproducibility"
        ])
        self.min_citations = self.agent_config.get("min_pubmed_citations", 1)
        self._tools_loaded = False
        self._pubmed = None
        self._chembl = None

    @classmethod
    def from_config(cls, config_path: str = "config.yaml") -> "CriticAgent":
        """Load agent from project config file."""
        config_file = PROJECT_ROOT / config_path
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return cls(config)

    def _load_tools(self):
        """Lazy-load ScienceClaw tools from parent project."""
        if self._tools_loaded:
            return

        try:
            from pubmed_search import search_pubmed, fetch_articles
            self._pubmed_search = search_pubmed
            self._pubmed_fetch = fetch_articles
        except ImportError:
            print("[WARN] pubmed_search not available — literature queries will be skipped")
            self._pubmed_search = None
            self._pubmed_fetch = None

        try:
            from chembl_search import search_molecules, _mol_props
            self._chembl_search = search_molecules
            self._chembl_props = _mol_props
        except ImportError:
            print("[WARN] chembl_search not available — compound queries will be skipped")
            self._chembl_search = None
            self._chembl_props = None

        self._tools_loaded = True

    def gather_evidence(self, candidate: str, target: str) -> CritiqueReport:
        """
        Run evidence gathering for all critique axes.

        Args:
            candidate: Peptide sequence (e.g., "VAGSAF")
            target: Target protein (e.g., "ERAP2")

        Returns:
            CritiqueReport with objections and evidence
        """
        self._load_tools()
        report = CritiqueReport(candidate=candidate, target=target)

        # ── Axis 1: Selectivity ──────────────────────────────────
        self._check_selectivity(report, candidate, target)

        # ── Axis 2: Bioavailability ──────────────────────────────
        self._check_bioavailability(report, candidate)

        # ── Axis 3: Prior Art ────────────────────────────────────
        self._check_prior_art(report, target)

        # ── Axis 4: Mechanism ────────────────────────────────────
        self._check_mechanism(report, candidate, target)

        # ── Axis 5: Reproducibility ──────────────────────────────
        self._check_reproducibility(report, candidate, target)

        report.evaluate_gate(
            max_unresolved_critical=0,
            max_unresolved_minor=self.config.get("gates", {}).get("critic_max_unresolved", 1)
        )

        return report

    def _check_selectivity(self, report: CritiqueReport, candidate: str, target: str):
        """Check for off-target binding risks."""
        queries = [
            f"{target} homolog aminopeptidase selectivity",
            f"ERAP1 ERAP2 IRAP substrate specificity differences",
            f"peptide {candidate} binding specificity aminopeptidase",
        ]
        hits = self._search_pubmed(queries)
        report.literature_hits.extend(hits)

        # Always raise selectivity as a question — it's the critical axis
        off_targets = self.config.get("primary_target", {}).get("selectivity_targets", {}).get("off_targets", [])
        report.objections.append(Objection(
            axis="selectivity",
            severity="critical",
            claim=f"Peptide {candidate} may bind {', '.join(off_targets)} due to structural homology with {target}",
            evidence=[{
                "source": "structural_biology",
                "id": "ERAP1/ERAP2/IRAP_family",
                "summary": "M1 aminopeptidase family shares >40% sequence identity in active site region"
            }] + [{"source": "pubmed", "id": h.get("pmid", ""), "summary": str(h.get("title", ""))[:120]} for h in hits[:3]],
        ))

    def _check_bioavailability(self, report: CritiqueReport, candidate: str):
        """Check peptide stability and pharmacokinetic concerns."""
        queries = [
            f"peptide drug stability protease degradation {len(candidate)}-mer",
            f"short peptide oral bioavailability strategies",
            f"peptide half-life serum stability modifications",
        ]
        hits = self._search_pubmed(queries)
        report.literature_hits.extend(hits)

        # Short peptides have known stability issues
        if len(candidate) <= 8:
            report.objections.append(Objection(
                axis="bioavailability",
                severity="major",
                claim=f"{len(candidate)}-mer peptide {candidate} likely has <30 min serum half-life without modifications",
                evidence=[{
                    "source": "literature_consensus",
                    "id": "peptide_stability_general",
                    "summary": "Unmodified peptides <10 residues typically degrade in <30 min in serum"
                }] + [{"source": "pubmed", "id": h.get("pmid", ""), "summary": str(h.get("title", ""))[:120]} for h in hits[:2]],
            ))

    def _check_prior_art(self, report: CritiqueReport, target: str):
        """Check for existing compounds targeting the same protein."""
        # ChEMBL search
        chembl_hits = self._search_chembl(target)
        report.chembl_hits.extend(chembl_hits)

        if chembl_hits:
            report.objections.append(Objection(
                axis="prior_art",
                severity="major",
                claim=f"Found {len(chembl_hits)} existing compounds targeting {target} in ChEMBL",
                evidence=[{
                    "source": "chembl",
                    "id": h.get("chembl_id", ""),
                    "summary": f"{h.get('pref_name') or 'unnamed'} — MW: {h.get('mw', '?')}, phase: {h.get('max_phase', '?')}"
                } for h in chembl_hits[:5]],
            ))

        # PubMed for known inhibitors
        queries = [
            f"{target} inhibitor selective nanomolar",
            f"{target} drug candidate clinical",
        ]
        hits = self._search_pubmed(queries)
        report.literature_hits.extend(hits)

    def _check_mechanism(self, report: CritiqueReport, candidate: str, target: str):
        """Check if the proposed binding mechanism is sound."""
        queries = [
            f"{target} active site substrate recognition",
            f"{target} allosteric regulation conformational change",
            f"{target} peptide binding mode crystallography",
        ]
        hits = self._search_pubmed(queries)
        report.literature_hits.extend(hits)

        # Flag if no structural data exists
        report.objections.append(Objection(
            axis="mechanism",
            severity="minor",
            claim=f"No experimental co-crystal structure exists for {target} with peptide substrates",
            evidence=[{
                "source": "pdb",
                "id": "no_cocrystal",
                "summary": f"AlphaFold model used (pLDDT 93.31) but no experimental {target}+peptide structure in PDB"
            }],
        ))

    def _check_reproducibility(self, report: CritiqueReport, candidate: str, target: str):
        """Check if computational predictions can be trusted."""
        queries = [
            "Boltz-2 peptide protein prediction accuracy benchmark",
            "AlphaFold peptide binding prediction reliability",
            f"computational peptide design {target} validation",
        ]
        hits = self._search_pubmed(queries)
        report.literature_hits.extend(hits)

        report.objections.append(Objection(
            axis="reproducibility",
            severity="minor",
            claim="Boltz-2 ipTM scores for short peptides may not correlate with binding affinity",
            evidence=[{
                "source": "benchmark",
                "id": "boltz2_peptide_caveat",
                "summary": "ipTM is a confidence metric for interface prediction, not a direct binding affinity predictor. "
                           "Correlation with experimental Kd is moderate for peptide-protein complexes."
            }],
        ))

    # ── Tool wrappers ────────────────────────────────────────────

    def _search_pubmed(self, queries: list[str]) -> list[dict]:
        """Search PubMed via ScienceClaw tool. Returns list of article dicts."""
        if self._pubmed_search is None:
            return []
        all_pmids = []
        for q in queries:
            try:
                pmids = self._pubmed_search(q, max_results=5)
                if isinstance(pmids, list):
                    all_pmids.extend(pmids)
            except Exception as e:
                print(f"[WARN] PubMed search failed for '{q}': {e}")

        # Deduplicate PMIDs
        unique_pmids = list(dict.fromkeys(str(p) for p in all_pmids))

        # Fetch article details
        if not unique_pmids or self._pubmed_fetch is None:
            return [{"pmid": str(p), "title": f"PMID:{p}", "summary": ""} for p in unique_pmids]

        try:
            articles = self._pubmed_fetch(unique_pmids[:20])  # cap at 20
            return [{"pmid": a.get("pmid", ""), "title": a.get("title", ""), "summary": a.get("abstract", "")[:200]} for a in articles]
        except Exception as e:
            print(f"[WARN] PubMed fetch failed: {e}")
            return [{"pmid": str(p), "title": f"PMID:{p}", "summary": ""} for p in unique_pmids]

    def _search_chembl(self, target: str) -> list[dict]:
        """Search ChEMBL via ScienceClaw tool."""
        if self._chembl_search is None:
            return []
        try:
            raw = self._chembl_search(target, max_results=10)
            if self._chembl_props:
                return [self._chembl_props(m) for m in raw]
            return raw
        except Exception as e:
            print(f"[WARN] ChEMBL search failed for '{target}': {e}")
            return []


# ── CLI entry point ──────────────────────────────────────────────

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    agent = CriticAgent.from_config()
    report = agent.gather_evidence("VAGSAF", "ERAP2")
    report.print_summary()

    # Save outputs
    out_dir = PROJECT_ROOT / "outputs" / "critiques"
    json_path, md_path = report.save(out_dir)
    print(f"Saved: {json_path}")
    print(f"Saved: {md_path}")
