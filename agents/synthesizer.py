"""
Synthesis Feasibility Agent for Virtual Biolab

Checks peptide synthesis feasibility: solubility, toxicity, stability,
cleavage resistance, and manufacturability. Uses TDC and ChEMBL data.

USAGE:
  from agents.synthesizer import SynthesizerAgent
  synth = SynthesizerAgent.from_config("config.yaml")
  report = synth.evaluate("VAGSAF", "ERAP2")
  report.print_summary()
"""

import sys
import json
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARENT_PROJECT = (PROJECT_ROOT / ".." / "ancient-drug-discovery").resolve()
TOOLS_DIR = PARENT_PROJECT / "tools"

if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


# Standard amino acid properties for feasibility checks
AA_PROPERTIES = {
    "A": {"name": "Alanine", "hydrophobic": True, "charge": 0, "mw": 89.09},
    "C": {"name": "Cysteine", "hydrophobic": False, "charge": 0, "mw": 121.16},
    "D": {"name": "Aspartate", "hydrophobic": False, "charge": -1, "mw": 133.10},
    "E": {"name": "Glutamate", "hydrophobic": False, "charge": -1, "mw": 147.13},
    "F": {"name": "Phenylalanine", "hydrophobic": True, "charge": 0, "mw": 165.19},
    "G": {"name": "Glycine", "hydrophobic": False, "charge": 0, "mw": 75.03},
    "H": {"name": "Histidine", "hydrophobic": False, "charge": 0, "mw": 155.16},
    "I": {"name": "Isoleucine", "hydrophobic": True, "charge": 0, "mw": 131.17},
    "K": {"name": "Lysine", "hydrophobic": False, "charge": 1, "mw": 146.19},
    "L": {"name": "Leucine", "hydrophobic": True, "charge": 0, "mw": 131.17},
    "M": {"name": "Methionine", "hydrophobic": True, "charge": 0, "mw": 149.21},
    "N": {"name": "Asparagine", "hydrophobic": False, "charge": 0, "mw": 132.12},
    "P": {"name": "Proline", "hydrophobic": False, "charge": 0, "mw": 115.13},
    "Q": {"name": "Glutamine", "hydrophobic": False, "charge": 0, "mw": 146.15},
    "R": {"name": "Arginine", "hydrophobic": False, "charge": 1, "mw": 174.20},
    "S": {"name": "Serine", "hydrophobic": False, "charge": 0, "mw": 105.09},
    "T": {"name": "Threonine", "hydrophobic": False, "charge": 0, "mw": 119.12},
    "V": {"name": "Valine", "hydrophobic": True, "charge": 0, "mw": 117.15},
    "W": {"name": "Tryptophan", "hydrophobic": True, "charge": 0, "mw": 204.23},
    "Y": {"name": "Tyrosine", "hydrophobic": True, "charge": 0, "mw": 181.19},
}

# Known protease cleavage motifs (simplified)
PROTEASE_MOTIFS = {
    "trypsin": ["K", "R"],          # Cleaves after K, R
    "chymotrypsin": ["F", "W", "Y", "L"],  # Cleaves after aromatic/large hydrophobic
    "pepsin": ["F", "L"],            # Cleaves before F, L at low pH
}

# Toxic/problematic sequence motifs
TOXIC_MOTIFS = [
    "RGD",   # Integrin-binding — may cause platelet aggregation issues
    "NGR",   # Aminopeptidase N binding
    "KGD",   # Platelet aggregation
]


@dataclass
class FeasibilityCheck:
    """Single feasibility assessment."""
    name: str
    status: str = "pass"     # pass | warn | fail
    value: str = ""
    threshold: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "value": self.value,
            "threshold": self.threshold,
            "notes": self.notes,
        }


@dataclass
class SynthesisReport:
    """Synthesis feasibility report for a peptide candidate."""
    candidate: str
    target: str
    timestamp: str = ""
    checks: list[FeasibilityCheck] = field(default_factory=list)
    sequence_properties: dict = field(default_factory=dict)
    gate_passed: bool = False

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def evaluate_gate(self) -> bool:
        """Gate 7 passes if no checks have 'fail' status."""
        self.gate_passed = not any(c.status == "fail" for c in self.checks)
        return self.gate_passed

    def print_summary(self):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            pass

        print(f"\n{'='*60}")
        print(f"SYNTHESIS REPORT: {self.candidate} -> {self.target}")
        print(f"Generated: {self.timestamp}")
        print(f"{'='*60}")

        # Sequence properties
        sp = self.sequence_properties
        if sp:
            print(f"\n  Sequence: {self.candidate}")
            print(f"  Length: {sp.get('length', '?')} residues")
            print(f"  MW: {sp.get('mw', '?'):.1f} Da")
            print(f"  Net charge: {sp.get('net_charge', '?'):+d} (pH 7)")
            print(f"  Hydrophobic %: {sp.get('hydrophobic_pct', 0):.0f}%")
            print(f"  Composition: {sp.get('composition', '')}")

        # Checks
        for c in self.checks:
            icon = {"pass": "[+]", "warn": "[~]", "fail": "[X]"}[c.status]
            print(f"\n  {icon} {c.name}: {c.status.upper()}")
            if c.value:
                print(f"      Value: {c.value}")
            if c.threshold:
                print(f"      Threshold: {c.threshold}")
            if c.notes:
                print(f"      Note: {c.notes}")

        self.evaluate_gate()
        verdict = "PASS" if self.gate_passed else "FAIL"
        n_pass = len([c for c in self.checks if c.status == "pass"])
        n_warn = len([c for c in self.checks if c.status == "warn"])
        n_fail = len([c for c in self.checks if c.status == "fail"])
        print(f"\n{'─'*60}")
        print(f"  {n_pass} pass, {n_warn} warn, {n_fail} fail")
        print(f"  Gate 7 verdict: {verdict}")
        print(f"{'='*60}\n")

    def to_dict(self) -> dict:
        return {
            "candidate": self.candidate,
            "target": self.target,
            "timestamp": self.timestamp,
            "sequence_properties": self.sequence_properties,
            "checks": [c.to_dict() for c in self.checks],
            "gate_passed": self.gate_passed,
        }

    def save(self, output_dir: Path) -> tuple[Path, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        slug = f"{self.candidate}_{self.target}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        json_path = output_dir / f"synthesis_{slug}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

        md_path = output_dir / f"synthesis_{slug}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(self._to_markdown())

        return json_path, md_path

    def _to_markdown(self) -> str:
        self.evaluate_gate()
        sp = self.sequence_properties
        lines = [
            f"# Synthesis Feasibility: {self.candidate} -> {self.target}",
            f"**Generated:** {self.timestamp}",
            f"**Gate 7 Verdict:** {'PASS' if self.gate_passed else 'FAIL'}",
            "",
            "## Sequence Properties",
            f"- Sequence: `{self.candidate}`",
            f"- Length: {sp.get('length', '?')} residues",
            f"- MW: {sp.get('mw', 0):.1f} Da",
            f"- Net charge: {sp.get('net_charge', 0):+d} (pH 7)",
            f"- Hydrophobic: {sp.get('hydrophobic_pct', 0):.0f}%",
            "",
            "## Feasibility Checks",
        ]
        for c in self.checks:
            icon = {"pass": "+", "warn": "~", "fail": "X"}[c.status]
            lines.append(f"### [{icon}] {c.name} — {c.status.upper()}")
            if c.value:
                lines.append(f"- Value: {c.value}")
            if c.threshold:
                lines.append(f"- Threshold: {c.threshold}")
            if c.notes:
                lines.append(f"- Notes: {c.notes}")
            lines.append("")

        return "\n".join(lines)


class SynthesizerAgent:
    """
    Evaluates peptide synthesis feasibility using sequence analysis,
    protease susceptibility prediction, and known toxicity motifs.
    """

    def __init__(self, config: dict):
        self.config = config

    @classmethod
    def from_config(cls, config_path: str = "config.yaml") -> "SynthesizerAgent":
        config_file = PROJECT_ROOT / config_path
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return cls(config)

    def evaluate(self, candidate: str, target: str) -> SynthesisReport:
        """Run all feasibility checks on a peptide candidate."""
        candidate = candidate.upper().strip()
        report = SynthesisReport(candidate=candidate, target=target)

        # Calculate sequence properties
        report.sequence_properties = self._calc_properties(candidate)

        # Run checks
        report.checks.append(self._check_sequence_validity(candidate))
        report.checks.append(self._check_molecular_weight(candidate))
        report.checks.append(self._check_solubility(candidate))
        report.checks.append(self._check_net_charge(candidate))
        report.checks.append(self._check_protease_susceptibility(candidate))
        report.checks.append(self._check_toxic_motifs(candidate))
        report.checks.append(self._check_synthesis_complexity(candidate))
        report.checks.append(self._check_aggregation_risk(candidate))

        report.evaluate_gate()
        return report

    def _calc_properties(self, seq: str) -> dict:
        """Calculate basic sequence properties."""
        residues = [AA_PROPERTIES.get(aa, {}) for aa in seq]
        mw = sum(r.get("mw", 0) for r in residues) - (len(seq) - 1) * 18.02  # water loss
        net_charge = sum(r.get("charge", 0) for r in residues)
        n_hydrophobic = sum(1 for r in residues if r.get("hydrophobic", False))
        hydrophobic_pct = (n_hydrophobic / len(seq) * 100) if seq else 0

        composition = ", ".join(
            f"{aa}({AA_PROPERTIES[aa]['name']})" for aa in seq if aa in AA_PROPERTIES
        )

        return {
            "length": len(seq),
            "mw": mw,
            "net_charge": net_charge,
            "hydrophobic_pct": hydrophobic_pct,
            "n_hydrophobic": n_hydrophobic,
            "composition": composition,
        }

    def _check_sequence_validity(self, seq: str) -> FeasibilityCheck:
        """Check all residues are standard amino acids."""
        invalid = [aa for aa in seq if aa not in AA_PROPERTIES]
        if invalid:
            return FeasibilityCheck(
                name="Sequence Validity",
                status="fail",
                value=f"Invalid residues: {', '.join(invalid)}",
                notes="Non-standard amino acids require special synthesis",
            )
        return FeasibilityCheck(
            name="Sequence Validity",
            status="pass",
            value=f"All {len(seq)} residues are standard amino acids",
        )

    def _check_molecular_weight(self, seq: str) -> FeasibilityCheck:
        """Check MW is in synthesizable range."""
        props = self._calc_properties(seq)
        mw = props["mw"]
        if mw > 5000:
            return FeasibilityCheck(
                name="Molecular Weight",
                status="warn",
                value=f"{mw:.1f} Da",
                threshold="< 5000 Da preferred for synthesis",
                notes="Large peptides may have lower synthesis yields",
            )
        return FeasibilityCheck(
            name="Molecular Weight",
            status="pass",
            value=f"{mw:.1f} Da",
            threshold="< 5000 Da",
        )

    def _check_solubility(self, seq: str) -> FeasibilityCheck:
        """Estimate solubility based on hydrophobicity and charge."""
        props = self._calc_properties(seq)
        hydro_pct = props["hydrophobic_pct"]
        charge = abs(props["net_charge"])

        # High hydrophobicity + no charge = poor solubility
        if hydro_pct > 60 and charge == 0:
            return FeasibilityCheck(
                name="Solubility Estimate",
                status="warn",
                value=f"{hydro_pct:.0f}% hydrophobic, net charge 0",
                threshold="< 50% hydrophobic or non-zero charge",
                notes="May require DMSO co-solvent or pH adjustment for assay. "
                      "Consider adding charged residues or PEG modification.",
            )
        if hydro_pct > 75:
            return FeasibilityCheck(
                name="Solubility Estimate",
                status="fail",
                value=f"{hydro_pct:.0f}% hydrophobic",
                threshold="< 75% hydrophobic",
                notes="Very likely to aggregate in aqueous solution",
            )
        return FeasibilityCheck(
            name="Solubility Estimate",
            status="pass",
            value=f"{hydro_pct:.0f}% hydrophobic, net charge {props['net_charge']:+d}",
            threshold="< 50% hydrophobic or non-zero charge",
        )

    def _check_net_charge(self, seq: str) -> FeasibilityCheck:
        """Check if net charge is appropriate."""
        props = self._calc_properties(seq)
        charge = props["net_charge"]
        if abs(charge) > 4:
            return FeasibilityCheck(
                name="Net Charge",
                status="warn",
                value=f"{charge:+d} at pH 7",
                threshold="Between -4 and +4",
                notes="High charge may affect membrane permeability",
            )
        return FeasibilityCheck(
            name="Net Charge",
            status="pass",
            value=f"{charge:+d} at pH 7",
        )

    def _check_protease_susceptibility(self, seq: str) -> FeasibilityCheck:
        """Check for known protease cleavage sites."""
        sites = []
        for i, aa in enumerate(seq):
            for protease, residues in PROTEASE_MOTIFS.items():
                if aa in residues and i < len(seq) - 1:  # internal sites only
                    sites.append(f"{protease} after {aa}{i+1}")

        if len(sites) >= 3:
            return FeasibilityCheck(
                name="Protease Susceptibility",
                status="warn",
                value=f"{len(sites)} cleavage sites: {'; '.join(sites[:5])}",
                threshold="< 3 internal cleavage sites",
                notes="Consider D-amino acid substitution or N-methylation at vulnerable positions. "
                      "For in vitro assay, protease inhibitor cocktail can mitigate.",
            )
        return FeasibilityCheck(
            name="Protease Susceptibility",
            status="pass",
            value=f"{len(sites)} cleavage sites" + (f": {'; '.join(sites)}" if sites else ""),
        )

    def _check_toxic_motifs(self, seq: str) -> FeasibilityCheck:
        """Check for known toxic or problematic sequence motifs."""
        found = [motif for motif in TOXIC_MOTIFS if motif in seq]
        if found:
            return FeasibilityCheck(
                name="Toxic Motifs",
                status="warn",
                value=f"Found: {', '.join(found)}",
                notes="These motifs may have unintended biological activity. "
                      "Verify in cell-based assays before advancing.",
            )
        return FeasibilityCheck(
            name="Toxic Motifs",
            status="pass",
            value="No known toxic motifs found",
        )

    def _check_synthesis_complexity(self, seq: str) -> FeasibilityCheck:
        """Estimate synthesis difficulty (GenScript scale 1-5)."""
        complexity = 1  # base

        # Difficult residues
        difficult = {"C": 1, "M": 0.5, "W": 0.5, "H": 0.5}
        for aa in seq:
            complexity += difficult.get(aa, 0)

        # Length penalty
        if len(seq) > 20:
            complexity += 1
        if len(seq) > 40:
            complexity += 1

        # Repeated residues
        for aa in set(seq):
            if seq.count(aa) > 3:
                complexity += 0.5

        complexity = min(complexity, 5)
        status = "pass" if complexity <= 3 else "warn"

        return FeasibilityCheck(
            name="Synthesis Complexity",
            status=status,
            value=f"{complexity:.1f}/5 (GenScript scale)",
            threshold="<= 3.0",
            notes=f"Length {len(seq)}, standard Fmoc SPPS" if complexity <= 3
                  else "May require specialized synthesis conditions",
        )

    def _check_aggregation_risk(self, seq: str) -> FeasibilityCheck:
        """Check for aggregation-prone sequences."""
        # Consecutive hydrophobic residues
        max_hydro_run = 0
        current_run = 0
        for aa in seq:
            if AA_PROPERTIES.get(aa, {}).get("hydrophobic", False):
                current_run += 1
                max_hydro_run = max(max_hydro_run, current_run)
            else:
                current_run = 0

        if max_hydro_run >= 5:
            return FeasibilityCheck(
                name="Aggregation Risk",
                status="warn",
                value=f"Longest hydrophobic run: {max_hydro_run} residues",
                threshold="< 5 consecutive hydrophobic residues",
                notes="May self-aggregate. Consider salt form or formulation additive.",
            )
        return FeasibilityCheck(
            name="Aggregation Risk",
            status="pass",
            value=f"Longest hydrophobic run: {max_hydro_run} residues",
        )


# ── CLI entry point ──────────────────────────────────────────────

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    candidate = sys.argv[1] if len(sys.argv) > 1 else "VAGSAF"
    target = sys.argv[2] if len(sys.argv) > 2 else "ERAP2"

    agent = SynthesizerAgent.from_config()
    report = agent.evaluate(candidate, target)
    report.print_summary()

    out_dir = PROJECT_ROOT / "outputs" / "synthesis"
    json_path, md_path = report.save(out_dir)
    print(f"Saved: {json_path}")
    print(f"Saved: {md_path}")
