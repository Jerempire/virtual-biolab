"""
Literature Scout Agent for Virtual Biolab

Searches for contradicting or supporting evidence across PubMed and ChEMBL.
Produces a structured literature report with citation counts and relevance scoring.

USAGE:
  from agents.scout import ScoutAgent
  scout = ScoutAgent.from_config("config.yaml")
  report = scout.scan("VAGSAF", "ERAP2")
  report.print_summary()
"""

import sys
import json
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARENT_PROJECT = (PROJECT_ROOT / ".." / "ancient-drug-discovery").resolve()
TOOLS_DIR = PARENT_PROJECT / "tools"

if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


@dataclass
class LiteratureHit:
    """A single literature finding."""
    pmid: str
    title: str
    abstract_snippet: str = ""
    relevance: str = "supporting"  # supporting | contradicting | neutral
    axis: str = ""                 # which critique axis it relates to
    year: str = ""

    def to_dict(self) -> dict:
        return {
            "pmid": self.pmid,
            "title": self.title,
            "abstract_snippet": self.abstract_snippet,
            "relevance": self.relevance,
            "axis": self.axis,
            "year": self.year,
        }


@dataclass
class ScoutReport:
    """Structured literature scan report."""
    candidate: str
    target: str
    timestamp: str = ""
    hits: list[LiteratureHit] = field(default_factory=list)
    chembl_compounds: list[dict] = field(default_factory=list)
    gate_passed: bool = False

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    @property
    def supporting(self) -> list[LiteratureHit]:
        return [h for h in self.hits if h.relevance == "supporting"]

    @property
    def contradicting(self) -> list[LiteratureHit]:
        return [h for h in self.hits if h.relevance == "contradicting"]

    def evaluate_gate(self, max_contradictions: int = 2, min_supporting: int = 3) -> bool:
        """Determine if candidate passes Gate 6."""
        self.gate_passed = (
            len(self.contradicting) <= max_contradictions and
            len(self.supporting) >= min_supporting
        )
        return self.gate_passed

    def print_summary(self):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            pass

        print(f"\n{'='*60}")
        print(f"SCOUT REPORT: {self.candidate} -> {self.target}")
        print(f"Generated: {self.timestamp}")
        print(f"{'='*60}")

        for relevance in ["supporting", "contradicting", "neutral"]:
            group = [h for h in self.hits if h.relevance == relevance]
            if not group:
                continue
            icon = {"supporting": "+", "contradicting": "!", "neutral": "~"}[relevance]
            print(f"\n  [{relevance.upper()}] ({len(group)} papers)")
            for h in group:
                print(f"    {icon} PMID:{h.pmid} — {h.title[:90]}")
                if h.abstract_snippet:
                    print(f"      {h.abstract_snippet[:120]}...")

        if self.chembl_compounds:
            print(f"\n  [ChEMBL COMPOUNDS] ({len(self.chembl_compounds)} found)")
            for c in self.chembl_compounds[:5]:
                print(f"    - {c.get('chembl_id', '?')}: {c.get('pref_name') or 'unnamed'} (MW: {c.get('mw', '?')})")

        self.evaluate_gate()
        verdict = "PASS" if self.gate_passed else "FAIL"
        print(f"\n{'─'*60}")
        print(f"  Supporting: {len(self.supporting)} | Contradicting: {len(self.contradicting)} | Neutral: {len([h for h in self.hits if h.relevance == 'neutral'])}")
        print(f"  Gate 6 verdict: {verdict}")
        print(f"{'='*60}\n")

    def to_dict(self) -> dict:
        return {
            "candidate": self.candidate,
            "target": self.target,
            "timestamp": self.timestamp,
            "hits": [h.to_dict() for h in self.hits],
            "chembl_compounds": self.chembl_compounds,
            "supporting_count": len(self.supporting),
            "contradicting_count": len(self.contradicting),
            "gate_passed": self.gate_passed,
        }

    def save(self, output_dir: Path) -> tuple[Path, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        slug = f"{self.candidate}_{self.target}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        json_path = output_dir / f"scout_{slug}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

        md_path = output_dir / f"scout_{slug}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(self._to_markdown())

        return json_path, md_path

    def _to_markdown(self) -> str:
        self.evaluate_gate()
        lines = [
            f"# Scout Report: {self.candidate} -> {self.target}",
            f"**Generated:** {self.timestamp}",
            f"**Gate 6 Verdict:** {'PASS' if self.gate_passed else 'FAIL'}",
            "",
        ]
        for relevance in ["supporting", "contradicting", "neutral"]:
            group = [h for h in self.hits if h.relevance == relevance]
            lines.append(f"## {relevance.title()} Evidence ({len(group)} papers)")
            if not group:
                lines.append("None found.\n")
                continue
            for h in group:
                lines.append(f"- **PMID:{h.pmid}** — {h.title}")
                if h.abstract_snippet:
                    lines.append(f"  > {h.abstract_snippet[:200]}")
            lines.append("")

        if self.chembl_compounds:
            lines.append(f"## ChEMBL Compounds ({len(self.chembl_compounds)})")
            for c in self.chembl_compounds[:10]:
                lines.append(f"- `{c.get('chembl_id', '?')}`: {c.get('pref_name') or 'unnamed'} (MW: {c.get('mw', '?')}, phase: {c.get('max_phase', '?')})")
            lines.append("")

        return "\n".join(lines)


class ScoutAgent:
    """
    Searches literature and compound databases for evidence
    supporting or contradicting a drug discovery hypothesis.
    """

    # Keywords that suggest a paper contradicts the hypothesis
    CONTRADICTION_KEYWORDS = [
        "failed", "negative result", "no significant", "no inhibition",
        "non-selective", "lack of selectivity", "poor stability",
        "rapid degradation", "toxic", "off-target", "retracted",
    ]

    # Keywords that suggest a paper supports the hypothesis
    SUPPORT_KEYWORDS = [
        "selective inhibit", "nanomolar", "potent", "specific binding",
        "validated target", "therapeutic potential", "novel inhibitor",
        "antigen presentation", "immune evasion", "MHC-I",
    ]

    def __init__(self, config: dict):
        self.config = config
        self.agent_config = config.get("agents", {}).get("scout", {})
        self._tools_loaded = False

    @classmethod
    def from_config(cls, config_path: str = "config.yaml") -> "ScoutAgent":
        config_file = PROJECT_ROOT / config_path
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return cls(config)

    def _load_tools(self):
        if self._tools_loaded:
            return
        try:
            from pubmed_search import search_pubmed, fetch_articles
            self._pubmed_search = search_pubmed
            self._pubmed_fetch = fetch_articles
        except ImportError:
            self._pubmed_search = None
            self._pubmed_fetch = None

        try:
            from chembl_search import search_molecules, _mol_props
            self._chembl_search = search_molecules
            self._chembl_props = _mol_props
        except ImportError:
            self._chembl_search = None
            self._chembl_props = None

        self._tools_loaded = True

    def scan(self, candidate: str, target: str) -> ScoutReport:
        """
        Run a comprehensive literature scan for a candidate-target pair.

        Returns ScoutReport with hits classified as supporting/contradicting/neutral.
        """
        self._load_tools()
        report = ScoutReport(candidate=candidate, target=target)

        # Build search queries from gate registry + config
        queries = self._build_queries(candidate, target)

        # Search PubMed
        all_pmids = []
        for q in queries:
            pmids = self._search_pubmed_ids(q)
            all_pmids.extend(pmids)

        # Deduplicate and fetch articles
        unique_pmids = list(dict.fromkeys(str(p) for p in all_pmids))[:30]
        articles = self._fetch_articles(unique_pmids)

        # Classify each article
        for article in articles:
            title = str(article.get("title", ""))
            abstract = str(article.get("abstract", ""))
            pmid = str(article.get("pmid", ""))
            year = str(article.get("year", ""))

            relevance = self._classify_relevance(title, abstract)

            report.hits.append(LiteratureHit(
                pmid=pmid,
                title=title,
                abstract_snippet=abstract[:200] if abstract else "",
                relevance=relevance,
                year=year,
            ))

        # Search ChEMBL for existing compounds
        if self._chembl_search:
            try:
                raw = self._chembl_search(target, max_results=10)
                report.chembl_compounds = [self._chembl_props(m) for m in raw] if self._chembl_props else raw
            except Exception as e:
                print(f"[WARN] ChEMBL search failed: {e}")

        report.evaluate_gate()
        return report

    def _build_queries(self, candidate: str, target: str) -> list[str]:
        """Build search queries for the candidate-target pair."""
        gate_queries = self.config.get("gates", {})
        # Use queries from gate_registry if available, plus standard queries
        queries = [
            f"{target} selective inhibitor peptide",
            f"{target} substrate specificity determinants",
            f"aminopeptidase peptide drug stability",
            f"{target} inhibitor clinical trial",
            f"{target} crystal structure substrate",
            f"{target} immune evasion cancer",
            f"{target} Crohn's disease therapeutic",
        ]
        # Add cross-discipline queries from config
        domains = self.agent_config.get("cross_discipline_domains", [])
        for domain in domains:
            queries.append(f"{target} {domain}")

        return queries

    def _classify_relevance(self, title: str, abstract: str) -> str:
        """Classify a paper as supporting, contradicting, or neutral."""
        text = (title + " " + abstract).lower()

        contradiction_score = sum(1 for kw in self.CONTRADICTION_KEYWORDS if kw in text)
        support_score = sum(1 for kw in self.SUPPORT_KEYWORDS if kw in text)

        if contradiction_score > support_score and contradiction_score >= 2:
            return "contradicting"
        elif support_score > contradiction_score and support_score >= 1:
            return "supporting"
        return "neutral"

    def _search_pubmed_ids(self, query: str) -> list[str]:
        if self._pubmed_search is None:
            return []
        try:
            return self._pubmed_search(query, max_results=5)
        except Exception as e:
            print(f"[WARN] PubMed search failed for '{query}': {e}")
            return []

    def _fetch_articles(self, pmids: list[str]) -> list[dict]:
        if not pmids or self._pubmed_fetch is None:
            return []
        try:
            return self._pubmed_fetch(pmids)
        except Exception as e:
            print(f"[WARN] PubMed fetch failed: {e}")
            return []


# ── CLI entry point ──────────────────────────────────────────────

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    agent = ScoutAgent.from_config()
    report = agent.scan("VAGSAF", "ERAP2")
    report.print_summary()

    out_dir = PROJECT_ROOT / "outputs" / "scout"
    json_path, md_path = report.save(out_dir)
    print(f"Saved: {json_path}")
    print(f"Saved: {md_path}")
